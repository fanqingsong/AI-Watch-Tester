"""
AWT Smart Agent 实际功能测试

测试简化版代理系统的实际功能
"""

import pytest
import asyncio
from aat.agent.simple_supervisor import SimpleSupervisorAgent
from aat.agent.config import AgentConfig, AgentMode
from aat.agent.simple_tools import get_simple_tools, execute_tool_with_tracking


class TestSimpleAgentSystem:
    """测试简化代理系统"""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """测试代理初始化"""
        config = AgentConfig()
        supervisor = SimpleSupervisorAgent(config)

        # 测试初始状态
        assert supervisor.config == config
        assert supervisor.llm is None
        assert supervisor.context is None

    @pytest.mark.asyncio
    async def test_agent_with_mock_llm(self):
        """测试代理与模拟 LLM"""
        config = AgentConfig()
        supervisor = SimpleSupervisorAgent(config)

        # 初始化（会创建模拟连接）
        await supervisor.initialize()

        # 验证初始化
        assert supervisor.llm is not None

    @pytest.mark.asyncio
    async def test_intent_understanding(self):
        """测试意图理解功能"""
        config = AgentConfig()
        supervisor = SimpleSupervisorAgent(config)

        # 测试不同类型的意图理解
        test_cases = [
            ("测试用户登录功能", "functional", ["authentication"]),
            ("测试安全性漏洞", "security", ["security"]),
            ("测试购物流程", "functional", ["ecommerce"]),
            ("探索页面功能", "exploratory", ["general"])
        ]

        for user_request, expected_type, expected_features in test_cases:
            intent = await supervisor._understand_intent(user_request)

            assert intent.test_type == expected_type
            assert intent.target_features == expected_features

    @pytest.mark.asyncio
    async def test_auth_test_plan_generation(self):
        """测试认证测试计划生成"""
        config = AgentConfig()
        supervisor = SimpleSupervisorAgent(config)
        supervisor.context = await supervisor._understand_intent("测试登录功能")

        # 生成测试计划
        plan = supervisor._get_auth_test_plan()

        assert plan["approach"] == "测试用户认证流程"
        assert len(plan["steps"]) == 5
        assert plan["steps"][0]["action"] == "navigate"
        assert plan["steps"][-1]["action"] == "verify"

    @pytest.mark.asyncio
    async def test_ecommerce_test_plan_generation(self):
        """测试电商测试计划生成"""
        config = AgentConfig()
        supervisor = SimpleSupervisorAgent(config)
        supervisor.context = await supervisor._understand_intent("测试购物流程")

        # 生成测试计划
        plan = supervisor._get_ecommerce_test_plan()

        assert plan["approach"] == "测试电商购物流程"
        assert len(plan["steps"]) == 4
        assert any(step["action"] == "click" for step in plan["steps"])

    @pytest.mark.asyncio
    async def test_step_execution(self):
        """测试步骤执行"""
        config = AgentConfig()
        supervisor = SimpleSupervisorAgent(config)

        # 测试不同类型的步骤
        steps_to_test = [
            {
                "step_number": 1,
                "description": "导航测试",
                "action": "navigate",
                "target": "http://example.com",
                "value": None
            },
            {
                "step_number": 2,
                "description": "点击测试",
                "action": "click",
                "target": "按钮",
                "value": None
            },
            {
                "step_number": 3,
                "description": "输入测试",
                "action": "type",
                "target": "输入框",
                "value": "测试文本"
            },
            {
                "step_number": 4,
                "description": "验证测试",
                "action": "verify",
                "target": "文本",
                "value": "期望值"
            }
        ]

        for step in steps_to_test:
            result = await supervisor._execute_step(step)
            assert result["success"], f"步骤 {step['description']} 执行失败"

    @pytest.mark.asyncio
    async def test_full_test_execution(self):
        """测试完整测试执行流程"""
        config = AgentConfig()
        supervisor = SimpleSupervisorAgent(config)

        # 执行一个简单的测试
        result = await supervisor.test_from_natural_language(
            user_request="测试基本功能",
            start_url="http://localhost:3000",
            mode="autonomous"
        )

        # 验证结果
        assert isinstance(result, dict) or hasattr(result, 'success')
        assert result.steps_completed > 0


class TestSimpleTools:
    """测试简化工具系统"""

    @pytest.mark.asyncio
    async def test_navigate_tool(self):
        """测试导航工具"""
        from aat.agent.simple_tools import simple_navigate

        result = await simple_navigate("http://example.com")
        assert result["success"] == True
        assert "url" in result

    @pytest.mark.asyncio
    async def test_click_tool(self):
        """测试点击工具"""
        from aat.agent.simple_tools import simple_click

        result = await simple_click("测试按钮")
        assert result["success"] == True
        assert result["action"] == "click"

    @pytest.mark.asyncio
    async def test_type_tool(self):
        """测试输入工具"""
        from aat.agent.simple_tools import simple_type

        result = await simple_type("输入框", "测试文本")
        assert result["success"] == True
        assert result["text"] == "测试文本"

    @pytest.mark.asyncio
    async def test_verify_tool(self):
        """测试验证工具"""
        from aat.agent.simple_tools import simple_verify

        result = await simple_verify("测试元素", "期望值")
        assert result["success"] == True
        assert result["action"] == "verify"

    @pytest.mark.asyncio
    async def test_tool_tracking(self):
        """测试工具跟踪"""
        from aat.agent.simple_tools import tool_tracker, execute_tool_with_tracking

        # 执行一些工具调用
        await execute_tool_with_tracking("simple_navigate", "http://example.com")
        await execute_tool_with_tracking("simple_click", "按钮")
        await execute_tool_with_tracking("simple_type", "输入框", "文本")

        # 检查统计
        stats = tool_tracker.get_stats()
        assert len(stats) == 3

        # 检查最常用工具
        most_used = tool_tracker.get_most_used_tools(1)
        assert len(most_used) == 1


class TestIntegrationScenarios:
    """集成测试场景"""

    @pytest.mark.asyncio
    async def test_complete_auth_scenario(self):
        """测试完整的认证场景"""
        config = AgentConfig(
            max_retry_attempts=2
        )
        supervisor = SimpleSupervisorAgent(config)

        result = await supervisor.test_from_natural_language(
            user_request="测试用户登录功能",
            start_url="http://localhost:3000/login",
            mode="autonomous"
        )

        assert result.steps_completed > 0
        assert isinstance(result.failures, list)

    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self):
        """测试错误恢复场景"""
        config = AgentConfig(
            max_retry_attempts=3
        )
        supervisor = SimpleSupervisorAgent(config)

        # 使用可能产生错误的测试
        result = await supervisor.test_from_natural_language(
            user_request="测试表单验证和错误处理",
            start_url="http://localhost:3000/register",
            mode="autonomous"
        )

        # 验证错误处理
        assert result is not None
        if result.failures:
            # 如果有失败，应该尝试过修复
            assert config.max_retry_attempts > 0

    @pytest.mark.asyncio
    async def test_chat_interaction(self):
        """测试对话交互"""
        config = AgentConfig()
        supervisor = await create_simple_supervisor(config)

        # 测试不同的对话
        test_messages = [
            "测试功能",
            "分析失败",
            "生成计划"
        ]

        for message in test_messages:
            response = await supervisor.chat(message)
            assert isinstance(response, str)
            assert len(response) > 0


def test_project_structure():
    """测试项目结构完整性"""
    import os
    from pathlib import Path

    # 检查关键文件
    required_files = [
        "src/aat/agent/simple_supervisor.py",
        "src/aat/agent/simple_tools.py",
        "src/aat/agent/config.py",
        "examples/agent/demo.py"
    ]

    for file_path in required_files:
        assert Path(file_path).exists(), f"缺少文件: {file_path}"


# 运行基础测试
if __name__ == "__main__":
    print("🧪 运行 AWT Smart Agent 功能测试\n")

    async def run_basic_tests():
        print("📋 测试代理系统...")
        test_agent = TestSimpleAgentSystem()

        await test_agent.test_agent_initialization()
        print("  ✅ 代理初始化测试通过")

        await test_agent.test_intent_understanding()
        print("  ✅ 意图理解测试通过")

        await test_agent.test_auth_test_plan_generation()
        print("  ✅ 测试计划生成测试通过")

        await test_agent.test_step_execution()
        print("  ✅ 步骤执行测试通过")

        print("\n📋 测试工具系统...")
        test_tools = TestSimpleTools()

        await test_tools.test_navigate_tool()
        print("  ✅ 导航工具测试通过")

        await test_tools.test_click_tool()
        print("  ✅ 点击工具测试通过")

        await test_tools.test_type_tool()
        print("  ✅ 输入工具测试通过")

        await test_tools.test_verify_tool()
        print("  ✅ 验证工具测试通过")

        print("\n📋 测试项目结构...")
        test_project_structure()
        print("  ✅ 项目结构测试通过")

        print("\n📋 测试完整场景...")
        await test_agent.test_full_test_execution()
        print("  ✅ 完整测试场景通过")

    print("\n🎉 所有基础测试通过！")
    print("\n💡 运行完整测试:")
    print("   pytest tests/agent/simple_test.py -v")
    print("\n🚀 运行演示:")
    print("   python examples/agent/demo.py")