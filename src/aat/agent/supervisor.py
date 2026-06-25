"""
AWT Supervisor Agent - 智能测试主管代理

这是 AWT Smart Agent 系统的核心协调器，负责：
- 接收用户的自然语言测试需求
- 协调子代理（Explorer、Tester、Analyzer）的工作
- 汇总测试结果并提供反馈
- 在需要时请求用户指导
"""

import asyncio
from typing import Optional, Dict, Any, List
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

from aat.agent.config import AgentConfig, TestIntent, AgentContext
from aat.agent.tools import get_awt_tools
from aat.agent.subagents import get_subagent_configs


class AWTSupervisorAgent:
    """
    AWT 智能测试主管代理

    这个代理是整个测试流程的协调者，它：
    1. 理解用户的自然语言测试需求
    2. 委托任务给专门的子代理
    3. 协调子代理之间的工作流程
    4. 汇总结果并反馈给用户
    """

    def __init__(self, config: AgentConfig):
        """
        初始化主管代理

        Args:
            config: 代理配置
        """
        self.config = config
        self.agent = None
        self.context = None

    async def initialize(self):
        """初始化代理和工具"""
        # 获取 AWT 工具集
        awt_tools = get_awt_tools()

        # 获取子代理配置
        subagent_configs = get_subagent_configs()

        # TODO: 集成 DeepAgents 的中间件系统
        # 目前使用简化的版本，后续会替换为完整的 DeepAgents 集成

        # 创建代理
        self.agent = create_agent(
            model=self.config.ai_model,
            tools=awt_tools,
            system_prompt=self._get_supervisor_prompt()
        )

    def _get_supervisor_prompt(self) -> str:
        """获取主管代理的系统提示"""
        return """
        你是一个智能测试主管。你的职责是：

        1. 理解用户的自然语言测试需求
        2. 将需求分解为具体的测试任务
        3. 协调子代理完成任务：
           - Explorer Agent: 探索页面结构和功能
           - Tester Agent: 执行测试步骤和验证
           - Analyzer Agent: 分析失败并提供修复建议
        4. 汇总测试结果并向用户反馈
        5. 在需要时请求用户指导

        工作流程：
        - 接收用户测试需求（自然语言）
        - 理解测试意图和目标
        - 委托 Explorer Agent 探索页面
        - 委托 Tester Agent 执行测试
        - 如果有失败，委托 Analyzer Agent 分析
        - 汇总结果并向用户报告

        注意事项：
        - 保持与用户的沟通，及时反馈进展
        - 在不确定时主动询问用户
        - 记录探索和测试过程供后续学习
        - 在执行关键操作前请求用户确认（根据模式）
        """

    async def test_from_natural_language(
        self,
        user_request: str,
        start_url: str,
        mode: str = "interactive"
    ) -> Dict[str, Any]:
        """
        从自然语言描述执行测试

        Args:
            user_request: 用户的自然语言测试需求
            start_url: 测试起始 URL
            mode: 运行模式 (interactive|autonomous|conservative|aggressive)

        Returns:
            测试结果字典
        """
        # 初始化代理（如果还没有初始化）
        if not self.agent:
            await self.initialize()

        # 创建测试上下文
        self.context = AgentContext(
            current_url=start_url,
            user_request=user_request,
            test_intent=await self._understand_intent(user_request)
        )

        print(f"🎯 AWT Smart Agent 启动")
        print(f"📝 测试需求: {user_request}")
        print(f"🌐 起始URL: {start_url}")
        print(f"🤖 运行模式: {mode}")
        print("-" * 50)

        # 构建初始消息
        initial_message = f"""
        用户的测试需求：{user_request}
        起始URL：{start_url}
        运行模式：{mode}

        请分析这个需求，然后协调子代理完成测试任务。
        """

        try:
            # 执行代理任务
            result = await self.agent.ainvoke({
                "messages": [HumanMessage(content=initial_message)]
            })

            # 解析结果
            return self._parse_result(result)

        except Exception as e:
            print(f"❌ 代理执行出错: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "partial_results": []
            }

    async def _understand_intent(self, user_request: str) -> TestIntent:
        """
        理解用户的测试意图

        Args:
            user_request: 用户的自然语言需求

        Returns:
            解析出的测试意图
        """
        # 简化版本：使用关键词匹配
        # 完整版本应该使用 LLM 来解析

        request_lower = user_request.lower()

        # 判断测试类型
        if any(word in request_lower for word in ["登录", "注册", "认证", "验证"]):
            test_type = "functional"
            target_features = ["authentication"]
        elif any(word in request_lower for word in ["安全", "漏洞", "注入", "攻击"]):
            test_type = "security"
            target_features = ["security"]
        else:
            test_type = "exploratory"
            target_features = ["general"]

        # 判断风险级别
        if any(word in request_lower for word in ["关键", "重要", "核心"]):
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

    def _parse_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析代理执行结果

        Args:
            result: 原始代理结果

        Returns:
            格式化的测试结果
        """
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None

        if isinstance(last_message, AIMessage):
            content = last_message.content
        else:
            content = str(result)

        return {
            "success": True,
            "summary": content,
            "context": self.context.model_dump() if self.context else None,
            "raw_result": result
        }

    async def chat(self, user_message: str) -> str:
        """
        与代理进行对话交互

        Args:
            user_message: 用户消息

        Returns:
            代理的回复
        """
        if not self.agent:
            await self.initialize()

        result = await self.agent.ainvoke({
            "messages": [HumanMessage(content=user_message)]
        })

        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None

        if isinstance(last_message, AIMessage):
            return last_message.content
        else:
            return str(result)


# 便捷函数
async def create_supervisor(config: AgentConfig = None) -> AWTSupervisorAgent:
    """
    创建并初始化主管代理

    Args:
        config: 代理配置，如果为 None 则使用默认配置

    Returns:
        初始化好的主管代理
    """
    if config is None:
        config = AgentConfig()

    supervisor = AWTSupervisorAgent(config)
    await supervisor.initialize()

    return supervisor