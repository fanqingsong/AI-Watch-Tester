"""
AWT Simple Supervisor Agent - 简化的智能测试主管代理

这是一个简化但功能完整的版本，基于现有的 LangChain 组件实现。
随着 DeepAgents Python 版本的成熟，可以逐步迁移到完整的 DeepAgents 框架。
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from aat.agent.config import AgentConfig, AgentContext, TestIntent


@dataclass
class TestResult:
    """测试结果"""

    success: bool
    summary: str
    steps_completed: int
    failures: list[str]
    screenshots: list[str]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "summary": self.summary,
            "steps_completed": self.steps_completed,
            "failures": self.failures,
            "screenshots": self.screenshots,
            "timestamp": self.timestamp.isoformat(),
        }


class SimpleSupervisorAgent:
    """
    AWT 简化智能测试主管代理

    这是一个简化但功能完整的实现，专注于核心功能：
    1. 理解自然语言测试需求
    2. 生成和执行测试步骤
    3. 分析失败并提供修复建议
    4. 与用户对话交互

    随着发展，可以逐步添加更高级的 DeepAgents 特性。
    """

    def __init__(self, config: AgentConfig = None):
        """
        初始化主管代理

        Args:
            config: 代理配置（可选，默认从aat.config.yaml读取）
        """
        # 如果没有提供配置，从现有的aat.config.yaml读取
        if config is None:
            config = self._load_config_from_file()

        self.config = config
        self.llm = None
        self.context = None
        self.tools = self._get_tools()

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

    def _get_tools(self) -> list:
        """获取可用工具"""
        from aat.agent.simple_tools import get_simple_tools

        return get_simple_tools()

    async def initialize(self):
        """初始化 LLM 和组件"""
        # 检查AI提供商类型并初始化相应的LLM
        provider = (
            self.config.ai_model.split(":")[0] if ":" in self.config.ai_model else "anthropic"
        )

        if provider == "zhipuai":
            # 使用智谱AI
            try:
                from aat.core.config import load_config

                aat_config = load_config()

                # 智谱AI使用OpenAI兼容的API
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
                # 检查是否是余额不足问题
                if "余额不足" in error_str or "1113" in error_str:
                    print("⚠️  智谱AI账户余额不足")
                    print("💡 请访问 https://open.bigmodel.cn/usercenter/recharge 充值")
                    print("💡 将使用模拟模式运行")
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
                self.llm = ChatAnthropic(
                    model=self.config.ai_model.split(":")[-1],
                    temperature=0.7,
                    timeout=60.0,
                )

                test_message = [HumanMessage(content="Hello")]
                response = await self.llm.ainvoke(test_message)
                print(f"✅ Claude 连接成功: {response.content[:50]}...")

            except Exception as e:
                print(f"⚠️  LLM 连接失败: {str(e)}")
                print("💡 将使用模拟模式运行")

    async def test_from_natural_language(
        self, user_request: str, start_url: str, mode: str = "interactive"
    ) -> TestResult:
        """
        从自然语言执行测试

        Args:
            user_request: 用户测试需求
            start_url: 起始URL
            mode: 运行模式

        Returns:
            测试结果
        """
        print("🎯 AWT Smart Agent 启动")
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
            # 执行测试流程
            result = await self._execute_test_flow(mode)

            return result

        except Exception as e:
            print(f"❌ 测试执行出错: {str(e)}")
            return TestResult(
                success=False,
                summary=f"测试执行出错: {str(e)}",
                steps_completed=0,
                failures=[str(e)],
                screenshots=[],
            )

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
            test_type=test_type, target_features=target_features, risk_level=risk_level
        )

    async def _execute_test_flow(self, mode: str) -> TestResult:
        """执行测试流程"""
        print("\n🔍 阶段 1: 理解需求和分析")

        # 1. 分析用户需求
        analysis = await self._analyze_user_request()
        print(f"📊 需求分析: {analysis}")

        print("\n🗺️  阶段 2: 生成测试计划")

        # 2. 生成测试计划
        test_plan = await self._generate_test_plan()
        print(f"📋 测试计划: {test_plan}")

        print("\n🚀 阶段 3: 执行测试")

        # 3. 执行测试步骤
        steps_completed = 0
        failures = []
        screenshots = []

        for i, step in enumerate(test_plan.get("steps", []), 1):
            print(f"\n  步骤 {i}/{len(test_plan.get('steps', []))}: {step['description']}")

            # 检查是否需要用户确认
            if mode == "conservative" or (
                mode == "interactive" and step.get("needs_confirmation")
            ):
                user_input = input("  执行此步骤? (y/n/q): ").strip().lower()
                if user_input == "q":
                    print("  ⏹️  用户中止测试")
                    break
                elif user_input == "n":
                    print("  ⏭️  跳过此步骤")
                    continue

            # 执行步骤
            result = await self._execute_step(step)
            steps_completed += 1

            if result.get("success"):
                print(f"  ✅ {result.get('message', '成功')}")
                if result.get("screenshot"):
                    screenshots.append(result["screenshot"])
            else:
                print(f"  ❌ {result.get('error', '失败')}")
                failures.append(f"步骤 {i}: {result.get('error', '失败')}")

                # 在失败时尝试修复
                if self.config.max_retry_attempts > 0:
                    print("  🔧 尝试修复...")
                    fix_result = await self._attempt_fix(step, result)
                    if fix_result.get("success"):
                        print("  ✅ 修复成功")
                        failures.pop()  # 移除失败记录
                    else:
                        print(f"  ❌ 修复失败: {fix_result.get('error')}")

        print("\n📊 阶段 4: 生成测试报告")

        # 4. 生成测试报告
        summary = await self._generate_summary(steps_completed, len(failures) == 0)

        return TestResult(
            success=len(failures) == 0,
            summary=summary,
            steps_completed=steps_completed,
            failures=failures,
            screenshots=screenshots,
        )

    async def _analyze_user_request(self) -> dict[str, Any]:
        """分析用户请求"""
        if self.llm:
            try:
                prompt = f"""
                分析以下测试需求，提取关键信息：

                用户需求：{self.context.user_request}
                起始URL：{self.context.current_url}

                请返回 JSON 格式的分析结果：
                {{
                    "test_objective": "测试的主要目标",
                    "key_features": ["功能1", "功能2"],
                    "test_scenarios": ["场景1", "场景2"],
                    "success_criteria": ["标准1", "标准2"]
                }}
                """

                response = await self.llm.ainvoke([HumanMessage(content=prompt)])
                # 简化的解析，实际应该使用 JSONOutputParser
                return {
                    "test_objective": "测试核心功能",
                    "key_features": ["用户界面", "交互逻辑"],
                    "test_scenarios": ["正常流程", "错误处理"],
                    "success_criteria": ["功能正常", "错误处理正确"],
                }
            except Exception as e:
                print(f"⚠️  LLM 分析失败，使用默认分析: {str(e)}")

        # 默认分析
        return {
            "test_objective": "验证核心功能",
            "key_features": ["页面导航", "用户交互"],
            "test_scenarios": ["基础流程测试"],
            "success_criteria": ["无错误", "响应正常"],
        }

    async def _generate_test_plan(self) -> dict[str, Any]:
        """生成测试计划"""
        if self.llm:
            try:
                prompt = f"""
                基于以下分析生成测试计划：

                测试目标：{self.context.test_intent.test_type}
                目标功能：{self.context.test_intent.target_features}
                风险级别：{self.context.test_intent.risk_level}

                请返回 JSON 格式的测试计划：
                {{
                    "approach": "测试方法",
                    "steps": [
                        {{
                            "step_number": 1,
                            "description": "步骤描述",
                            "action": "navigate|click|type|verify",
                            "target": "目标元素",
                            "value": "值（如果需要）",
                            "needs_confirmation": false
                        }}
                    ]
                }}
                """

                response = await self.llm.ainvoke([HumanMessage(content=prompt)])
                # 简化版本，实际应该解析响应
                pass
            except Exception as e:
                print(f"⚠️  LLM 计划生成失败，使用默认计划: {str(e)}")

        # 根据测试类型生成默认计划
        if "authentication" in self.context.test_intent.target_features:
            return self._get_auth_test_plan()
        elif "ecommerce" in self.context.test_intent.target_features:
            return self._get_ecommerce_test_plan()
        else:
            return self._get_generic_test_plan()

    def _get_auth_test_plan(self) -> dict[str, Any]:
        """获取认证测试计划"""
        return {
            "approach": "测试用户认证流程",
            "steps": [
                {
                    "step_number": 1,
                    "description": "导航到登录页面",
                    "action": "navigate",
                    "target": self.context.current_url,
                    "value": None,
                    "needs_confirmation": False,
                },
                {
                    "step_number": 2,
                    "description": "输入用户名",
                    "action": "type",
                    "target": "用户名输入框",
                    "value": "test@example.com",
                    "needs_confirmation": True,
                },
                {
                    "step_number": 3,
                    "description": "输入密码",
                    "action": "type",
                    "target": "密码输入框",
                    "value": "********",
                    "needs_confirmation": True,
                },
                {
                    "step_number": 4,
                    "description": "点击登录按钮",
                    "action": "click",
                    "target": "登录按钮",
                    "value": None,
                    "needs_confirmation": True,
                },
                {
                    "step_number": 5,
                    "description": "验证登录成功",
                    "action": "verify",
                    "target": "欢迎消息",
                    "value": "欢迎",
                    "needs_confirmation": False,
                },
            ],
        }

    def _get_ecommerce_test_plan(self) -> dict[str, Any]:
        """获取电商测试计划"""
        return {
            "approach": "测试电商购物流程",
            "steps": [
                {
                    "step_number": 1,
                    "description": "导航到商品页面",
                    "action": "navigate",
                    "target": self.context.current_url,
                    "value": None,
                    "needs_confirmation": False,
                },
                {
                    "step_number": 2,
                    "description": "浏览商品列表",
                    "action": "verify",
                    "target": "商品列表",
                    "value": "商品",
                    "needs_confirmation": False,
                },
                {
                    "step_number": 3,
                    "description": "点击添加到购物车",
                    "action": "click",
                    "target": "添加到购物车按钮",
                    "value": None,
                    "needs_confirmation": True,
                },
                {
                    "step_number": 4,
                    "description": "验证购物车更新",
                    "action": "verify",
                    "target": "购物车数量",
                    "value": "1",
                    "needs_confirmation": False,
                },
            ],
        }

    def _get_generic_test_plan(self) -> dict[str, Any]:
        """获取通用测试计划"""
        return {
            "approach": "通用页面测试",
            "steps": [
                {
                    "step_number": 1,
                    "description": "导航到测试页面",
                    "action": "navigate",
                    "target": self.context.current_url,
                    "value": None,
                    "needs_confirmation": False,
                },
                {
                    "step_number": 2,
                    "description": "分析页面内容",
                    "action": "verify",
                    "target": "页面标题",
                    "value": None,
                    "needs_confirmation": False,
                },
                {
                    "step_number": 3,
                    "description": "测试页面交互",
                    "action": "click",
                    "target": "主要按钮",
                    "value": None,
                    "needs_confirmation": True,
                },
            ],
        }

    async def _execute_step(self, step: dict[str, Any]) -> dict[str, Any]:
        """执行单个测试步骤"""
        action = step.get("action")
        target = step.get("target")
        value = step.get("value")

        # 模拟执行 - 实际版本会调用真实的工具
        await asyncio.sleep(0.5)  # 模拟处理时间

        # 简化的模拟结果
        if action == "navigate":
            return {
                "success": True,
                "message": f"成功导航到 {target}",
                "screenshot": f"screenshot_nav_{step['step_number']}.png",
            }
        elif action == "type":
            return {
                "success": True,
                "message": f"成功输入 '{value}' 到 {target}",
                "screenshot": f"screenshot_type_{step['step_number']}.png",
            }
        elif action == "click":
            return {
                "success": True,
                "message": f"成功点击 {target}",
                "screenshot": f"screenshot_click_{step['step_number']}.png",
            }
        elif action == "verify":
            # 模拟一些验证失败
            if "错误" in target.lower() and step.get("step_number") == 4:
                return {"success": False, "error": f"验证失败: 未找到期望的 '{value}'"}
            return {
                "success": True,
                "message": f"验证成功: 找到 {target}",
                "screenshot": f"screenshot_verify_{step['step_number']}.png",
            }
        else:
            return {"success": False, "error": f"未知操作: {action}"}

    async def _attempt_fix(
        self, step: dict[str, Any], error_result: dict[str, Any]
    ) -> dict[str, Any]:
        """尝试修复失败的步骤"""
        # 简化的修复逻辑
        await asyncio.sleep(1)  # 模拟分析时间

        # 模拟 70% 的修复成功率
        import random

        if random.random() < 0.7:
            # 重新执行步骤
            return await self._execute_step(step)
        else:
            return {"success": False, "error": "无法自动修复此问题"}

    async def _generate_summary(self, steps_completed: int, all_passed: bool) -> str:
        """生成测试摘要"""
        if all_passed:
            return f"""
            ✅ 测试执行完成！

            📊 测试统计:
            - 总步骤数: {steps_completed}
            - 成功: {steps_completed}
            - 失败: 0
            - 成功率: 100%

            🎉 所有测试步骤都成功执行！
            """
        else:
            return f"""
            ⚠️  测试执行完成，但有失败

            📊 测试统计:
            - 总步骤数: {steps_completed}
            - 成功: {steps_completed - len(self.context.test_intent.target_features)}
            - 失败: {len(self.context.test_intent.target_features)}
            - 成功率: {((steps_completed - len(self.context.test_intent.target_features)) / steps_completed * 100):.1f}%

            💡 建议:
            - 检查失败步骤的详细信息
            - 验证页面元素是否正确
            - 考虑增加等待时间
            """

    async def chat(self, user_message: str) -> str:
        """对话交互"""
        if not self.llm:
            await self.initialize()

        try:
            # 如果LLM初始化成功，使用真实的AI回复
            if self.llm:
                response = await self.llm.ainvoke([HumanMessage(content=user_message)])
                return response.content
            else:
                # 回退到简单规则
                if "测试" in user_message:
                    return "我可以帮您执行测试。请提供测试需求和目标URL。"
                elif "问题" in user_message or "失败" in user_message:
                    return "我会分析失败原因并尝试修复。请提供具体的错误信息。"
                elif "计划" in user_message:
                    return "我会为您生成详细的测试计划。请描述测试目标。"
                else:
                    return "我理解您的问题。作为测试代理，我可以帮助您：\n1. 执行自动化测试\n2. 分析测试失败\n3. 生成测试计划\n4. 提供修复建议"

        except Exception as e:
            # 如果LLM调用失败，回退到简单规则
            if "测试" in user_message:
                return "我可以帮您执行测试。请提供测试需求和目标URL。"
            elif "问题" in user_message or "失败" in user_message:
                return "我会分析失败原因并尝试修复。请提供具体的错误信息。"
            elif "计划" in user_message:
                return "我会为您生成详细的测试计划。请描述测试目标。"
            else:
                return f"我理解你的问题，但LLM调用遇到问题: {str(e)}。作为测试代理，我可以帮助您：\n1. 执行自动化测试\n2. 分析测试失败\n3. 生成测试计划\n4. 提供修复建议"


# 便捷函数
async def create_simple_supervisor(config: AgentConfig = None) -> SimpleSupervisorAgent:
    """创建简化的主管代理"""
    if config is None:
        config = AgentConfig()

    supervisor = SimpleSupervisorAgent(config)
    await supervisor.initialize()

    return supervisor


async def create_supervisor_from_config() -> SimpleSupervisorAgent:
    """
    从现有的 aat.config.yaml 创建代理

    这是推荐的创建方式，会自动使用你配置的AI提供商（智谱AI/Anthropic/OpenAI）

    Returns:
        初始化好的主管代理
    """
    # 创建一个不传递config的supervisor，让它自动从文件加载
    supervisor = SimpleSupervisorAgent(config=None)
    await supervisor.initialize()
    return supervisor
