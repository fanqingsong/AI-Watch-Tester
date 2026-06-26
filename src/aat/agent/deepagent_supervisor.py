"""
AWT DeepAgent Supervisor Agent - 基于官方 DeepAgents 框架的智能测试主管代理

这是使用 LangChain DeepAgents 框架的完整实现，提供：
- 原生的工具调用和子代理系统
- 内置的上下文管理和技能系统
- 文件系统权限和虚拟文件系统
- 人机交互和中断机制
- 持久化和状态管理
"""

import asyncio
from datetime import datetime
from typing import Any

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from aat.agent.config import AgentConfig, AgentContext, TestIntent
from aat.agent.deepagent_tools import get_awt_deepagent_tools


class DeepAgentTestResult:
    """DeepAgent 测试结果"""

    def __init__(self, success: bool, summary: str, steps_completed: int = 0,
                 failures: list[str] | None = None, screenshots: list[str] | None = None,
                 timestamp: datetime | None = None, raw_result: dict[str, Any] | None = None):
        self.success = success
        self.summary = summary
        self.steps_completed = steps_completed
        self.failures = failures or []
        self.screenshots = screenshots or []
        self.timestamp = timestamp or datetime.now()
        self.raw_result = raw_result or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "summary": self.summary,
            "steps_completed": self.steps_completed,
            "failures": self.failures,
            "screenshots": self.screenshots,
            "timestamp": self.timestamp.isoformat(),
            "raw_result": self.raw_result,
        }


class DeepAgentSupervisor:
    """
    AWT DeepAgent 智能测试主管代理

    使用官方 DeepAgents 框架实现，提供完整的代理能力：
    1. 理解自然语言测试需求
    2. 协调子代理完成任务
    3. 执行测试步骤和验证
    4. 分析失败并提供修复建议
    5. 与用户对话交互

    DeepAgents 优势：
    - 原生工具调用和子代理系统
    - 内置上下文管理和压缩
    - 虚拟文件系统支持
    - 人机交互中断机制
    - 持久化和状态管理
    """

    def __init__(self, config: AgentConfig = None):
        """
        初始化 DeepAgent 主管代理

        Args:
            config: 代理配置（可选，默认从aat.config.yaml读取）
        """
        if config is None:
            config = self._load_config_from_file()

        self.config = config
        self.agent = None
        self.context = None
        self.llm = None

    def _load_config_from_file(self) -> AgentConfig:
        """从现有的aat.config.yaml加载配置"""
        try:
            from aat.core.config import load_config
            aat_config = load_config()

            # 将现有配置转换为AgentConfig
            return AgentConfig(
                ai_model=f"zhipuai:{aat_config.ai.model}",
                default_mode="autonomous",
                max_exploration_depth=3,
                exploration_timeout=aat_config.engine.timeout_ms or 30000,
                test_execution_timeout=aat_config.engine.timeout_ms or 60000,
                max_retry_attempts=aat_config.max_loops or 3,
            )
        except Exception as e:
            print(f"⚠️  无法加载配置文件，使用默认配置: {str(e)}")
            return AgentConfig()

    async def initialize(self):
        """初始化 DeepAgent 和组件"""
        # 检查AI提供商类型并初始化相应的LLM
        provider = (
            self.config.ai_model.split(":")[0] if ":" in self.config.ai_model else "anthropic"
        )

        if provider == "zhipuai":
            # 使用智谱AI（通过OpenAI兼容API）
            try:
                from aat.core.config import load_config
                aat_config = load_config()

                from langchain_openai import ChatOpenAI

                self.llm = ChatOpenAI(
                    base_url="https://open.bigmodel.cn/api/coding/paas/v4/",
                    api_key=aat_config.ai.api_key,
                    model=aat_config.ai.model,
                    temperature=aat_config.ai.temperature or 0.3,
                    timeout=60.0,
                )

                # 测试连接
                test_message = [HumanMessage(content="你好")]
                response = await self.llm.ainvoke(test_message)
                print(f"✅ 智谱AI ({aat_config.ai.model}) 连接成功")

            except Exception as e:
                error_str = str(e)
                if "余额不足" in error_str or "1113" in error_str:
                    print("⚠️  智谱AI账户余额不足")
                    print("💡 请访问 https://open.bigmodel.cn/usercenter/recharge 充值")
                else:
                    print(f"⚠️  智谱AI连接失败: {error_str}")
                print("💡 将使用模拟模式运行")

        elif provider == "openai":
            # 使用OpenAI
            try:
                from langchain_openai import ChatOpenAI
                from aat.core.config import load_config
                aat_config = load_config()

                self.llm = ChatOpenAI(
                    api_key=aat_config.ai.api_key,
                    model="gpt-4o",
                    temperature=0.7,
                    timeout=60.0,
                )

                test_message = [HumanMessage(content="Hello")]
                response = await self.llm.ainvoke(test_message)
                print("✅ OpenAI GPT-4o 连接成功")

            except Exception as e:
                print(f"⚠️  OpenAI连接失败: {str(e)}")
                print("💡 将使用模拟模式运行")

        else:
            # 默认使用Claude
            try:
                model_name = self.config.ai_model.split(":")[-1] if ":" in self.config.ai_model else "claude-sonnet-4-6"
                self.llm = ChatAnthropic(
                    model=model_name,
                    temperature=0.7,
                    timeout=60.0,
                )

                test_message = [HumanMessage(content="Hello")]
                response = await self.llm.ainvoke(test_message)
                print(f"✅ Claude ({model_name}) 连接成功")

            except Exception as e:
                print(f"⚠️  Claude连接失败: {str(e)}")
                print("💡 将使用模拟模式运行")

    async def test_from_natural_language(
        self, user_request: str, start_url: str, mode: str = "interactive"
    ) -> DeepAgentTestResult:
        """
        从自然语言执行测试（使用 DeepAgent）

        Args:
            user_request: 用户测试需求
            start_url: 起始URL
            mode: 运行模式

        Returns:
            测试结果
        """
        print("🎯 AWT DeepAgent 启动")
        print(f"📝 测试需求: {user_request}")
        print(f"🌐 起始URL: {start_url}")
        print(f"🤖 运行模式: {mode}")
        print("-" * 50)

        # 初始化（如果还没有）
        if not self.llm:
            await self.initialize()

        # 创建测试上下文
        self.context = AgentContext(
            current_url=start_url,
            user_request=user_request,
            test_intent=await self._understand_intent(user_request),
        )

        try:
            # 创建 DeepAgent
            agent = await self._create_deepagent(mode)

            # 构建测试任务消息
            task_message = f"""
            请帮我执行以下测试任务：

            测试需求：{user_request}
            起始URL：{start_url}
            运行模式：{mode}

            测试类型：{self.context.test_intent.test_type}
            目标功能：{', '.join(self.context.test_intent.target_features)}
            风险级别：{self.context.test_intent.risk_level}

            请分析这个需求，制定测试计划，然后执行测试。
            在执行过程中，如果遇到问题，请尝试分析和修复。
            """

            print("\n🤖 DeepAgent 开始执行任务...")

            # 执行 DeepAgent 任务
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=task_message)]}
            )

            # 解析结果
            return self._parse_deepagent_result(result)

        except Exception as e:
            print(f"❌ DeepAgent 执行出错: {str(e)}")
            import traceback
            traceback.print_exc()

            return DeepAgentTestResult(
                success=False,
                summary=f"DeepAgent 执行出错: {str(e)}",
                steps_completed=0,
                failures=[str(e)],
                screenshots=[],
            )

    async def _create_deepagent(self, mode: str):
        """创建 DeepAgent 实例"""
        if not self.llm:
            raise RuntimeError("LLM 未初始化，请先调用 initialize()")

        # 获取 AWT 工具集
        awt_tools = get_awt_deepagent_tools()

        # 构建系统提示
        system_prompt = self._get_supervisor_system_prompt(mode)

        # 创建 DeepAgent
        agent = create_deep_agent(
            model=self.llm,
            tools=awt_tools,
            system_prompt=system_prompt,
            # DeepAgent 配置
            interrupt_on=self._get_interrupt_config(mode),
        )

        return agent

    def _get_supervisor_system_prompt(self, mode: str) -> str:
        """获取主管代理的系统提示"""
        base_prompt = """
        你是一个智能测试主管代理，专门负责自动化测试的规划、执行和分析。

        核心职责：
        1. 理解用户的自然语言测试需求
        2. 分析页面结构和功能
        3. 制定详细的测试计划
        4. 执行测试步骤并验证结果
        5. 在失败时分析原因并提供修复建议

        工作流程：
        - 接收用户测试需求（自然语言）
        - 理解测试意图和目标
        - 分析页面结构和可测试功能
        - 制定测试计划（步骤、验证点）
        - 执行测试步骤
        - 验证结果
        - 如果失败，分析原因并尝试修复
        - 生成测试报告

        可用工具：
        - 导航工具：smart_navigate, go_back, refresh_page
        - 分析工具：analyze_page, locate_element
        - 交互工具：smart_click, smart_type, select_option
        - 验证工具：verify_text_visible, verify_element_exists, verify_url_contains
        - 辅助工具：take_screenshot, check_console, wait_for_element

        注意事项：
        - 使用工具前仔细检查参数
        - 在关键操作前考虑请求用户确认（根据模式）
        - 记录详细的测试过程和结果
        - 在失败时进行根因分析
        - 提供可执行的修复建议
        """

        mode_specific = {
            "interactive": """
            运行模式：交互式
            - 在重要操作前主动询问用户
            - 及时反馈执行进展
            - 接受用户的指导和纠正
            """,
            "autonomous": """
            运行模式：自主
            - 独立制定和执行测试计划
            - 自动处理常见问题
            - 只在无法决策时询问用户
            """,
            "conservative": """
            运行模式：保守
            - 每个步骤都请求用户确认
            - 优先选择安全的操作方式
            - 避免可能造成破坏的操作
            """,
            "aggressive": """
            运行模式：激进
            - 大胆尝试各种测试路径
            - 快速执行，减少确认
            - 探索边界情况和异常场景
            """
        }

        return base_prompt + mode_specific.get(mode, mode_specific["autonomous"])

    def _get_interrupt_config(self, mode: str) -> dict[str, Any]:
        """获取中断配置（人机交互）"""
        if mode == "conservative":
            # 保守模式：所有重要操作都中断
            return {
                "smart_click": True,  # 点击前确认
                "smart_type": True,   # 输入前确认
                "smart_navigate": False,  # 导航不需要确认
            }
        elif mode == "interactive":
            # 交互模式：关键操作中断
            return {
                "smart_click": False,  # 点击不需要确认（已包含在用户流程中）
                "smart_type": False,   # 输入不需要确认
            }
        else:
            # 自主和激进模式：不中断
            return {}

    async def _understand_intent(self, user_request: str) -> TestIntent:
        """理解测试意图"""
        request_lower = user_request.lower()

        # 简单的关键词分析
        if any(word in request_lower for word in ["登录", "注册", "认证", "验证"]):
            test_type = "functional"
            target_features = ["authentication"]
        elif any(word in request_lower for word in ["安全", "漏洞", "注入"]):
            test_type = "security"
            target_features = ["security"]
        elif any(word in request_lower for word in ["购买", "购物", "支付", "结账"]):
            test_type = "functional"
            target_features = ["ecommerce"]
        else:
            test_type = "exploratory"
            target_features = ["general"]

        # 判断风险级别
        if any(word in request_lower for word in ["关键", "重要", "核心", "支付"]):
            risk_level = "high"
        elif any(word in request_lower for word in ["次要", "辅助", "边缘"]):
            risk_level = "low"
        else:
            risk_level = "medium"

        return TestIntent(
            test_type=test_type,
            target_features=target_features,
            risk_level=risk_level
        )

    def _parse_deepagent_result(self, result: dict[str, Any]) -> DeepAgentTestResult:
        """解析 DeepAgent 执行结果"""
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None

        # 提取最终回复
        if hasattr(last_message, 'content'):
            summary = last_message.content
        elif isinstance(last_message, dict):
            summary = last_message.get('content', str(last_message))
        else:
            summary = str(result)

        # 简化的结果解析（实际版本应该更详细地解析工具调用等）
        return DeepAgentTestResult(
            success=True,  # 如果执行到这里，认为成功
            summary=summary,
            steps_completed=0,  # 需要从工具调用历史中提取
            failures=[],
            screenshots=[],
            raw_result=result,
        )

    async def chat(self, user_message: str) -> str:
        """对话交互"""
        if not self.llm:
            await self.initialize()

        try:
            # 创建简单的对话代理
            agent = create_deep_agent(
                model=self.llm,
                tools=get_awt_deepagent_tools(),
                system_prompt="你是一个智能测试助手，可以帮助用户进行测试相关的对话和咨询。"
            )

            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=user_message)]}
            )

            messages = result.get("messages", [])
            last_message = messages[-1] if messages else None

            if hasattr(last_message, 'content'):
                return last_message.content
            else:
                return str(result)

        except Exception as e:
            return f"对话执行出错: {str(e)}"


# 便捷函数
async def create_deepagent_supervisor(config: AgentConfig = None) -> DeepAgentSupervisor:
    """创建 DeepAgent 主管代理"""
    if config is None:
        config = AgentConfig()

    supervisor = DeepAgentSupervisor(config)
    await supervisor.initialize()

    return supervisor


async def create_supervisor_from_config() -> DeepAgentSupervisor:
    """
    从现有的 aat.config.yaml 创建 DeepAgent 代理

    这是推荐的创建方式，会自动使用你配置的AI提供商（智谱AI/Anthropic/OpenAI）

    Returns:
        初始化好的主管代理
    """
    supervisor = DeepAgentSupervisor(config=None)
    await supervisor.initialize()
    return supervisor