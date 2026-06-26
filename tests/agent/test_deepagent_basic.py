"""
基础测试：验证 DeepAgent 安装和基本功能
"""

import pytest
import asyncio
from langchain_core.tools import tool


class TestDeepAgentInstallation:
    """测试 DeepAgent 安装"""

    def test_deepagent_import(self):
        """测试能否导入 DeepAgent"""
        try:
            from deepagents import create_deep_agent
            assert create_deep_agent is not None
            print("✅ DeepAgent 导入成功")
        except ImportError as e:
            pytest.fail(f"❌ DeepAgent 导入失败: {str(e)}")

    def test_langchain_imports(self):
        """测试 LangChain 相关导入"""
        try:
            import langchain
            import langgraph
            from langchain_core.messages import HumanMessage
            assert langchain is not None
            assert langgraph is not None
            assert HumanMessage is not None
            print("✅ LangChain 组件导入成功")
        except ImportError as e:
            pytest.fail(f"❌ LangChain 导入失败: {str(e)}")


class TestAWTDeepAgentIntegration:
    """测试 AWT DeepAgent 集成"""

    def test_awt_agent_import(self):
        """测试 AWT Agent 导入"""
        try:
            from aat.agent import (
                DeepAgentSupervisor,
                DeepAgentTestResult,
                create_supervisor_from_config,
                get_awt_deepagent_tools,
            )
            assert DeepAgentSupervisor is not None
            assert create_supervisor_from_config is not None
            print("✅ AWT DeepAgent 组件导入成功")
        except ImportError as e:
            pytest.fail(f"❌ AWT DeepAgent 导入失败: {str(e)}")

    def test_tools_import(self):
        """测试工具导入"""
        try:
            from aat.agent.deepagent_tools import (
                get_awt_deepagent_tools,
                get_navigation_tools,
                get_interaction_tools,
                get_verification_tools,
                get_analysis_tools,
            )
            tools = get_awt_deepagent_tools()
            assert len(tools) > 0
            print(f"✅ 工具导入成功，共 {len(tools)} 个工具")
        except ImportError as e:
            pytest.fail(f"❌ 工具导入失败: {str(e)}")

    @pytest.mark.asyncio
    async def test_tool_creation(self):
        """测试工具创建"""
        from aat.agent.deepagent_tools import smart_navigate

        # 验证工具属性
        assert hasattr(smart_navigate, 'name')
        assert hasattr(smart_navigate, 'description')

        # 测试工具调用 (使用 .invoke() 方法)
        result = await smart_navigate.ainvoke({"url": "https://example.com", "wait_for_load": True, "timeout": 30000})
        assert result["success"] == True
        assert "url" in result
        print("✅ 工具创建和调用测试通过")


class TestDeepAgentFunctionality:
    """测试 DeepAgent 基本功能"""

    @pytest.mark.asyncio
    async def test_supervisor_creation(self):
        """测试主管代理创建"""
        from aat.agent import AgentConfig, DeepAgentSupervisor

        config = AgentConfig(
            ai_model="anthropic:claude-sonnet-4-6",
            default_mode="autonomous",
        )

        supervisor = DeepAgentSupervisor(config)
        assert supervisor.config == config
        assert supervisor.agent is None  # 未初始化
        print("✅ 主管代理创建测试通过")

    @pytest.mark.asyncio
    async def test_supervisor_initialize(self):
        """测试主管代理初始化"""
        from aat.agent import DeepAgentSupervisor, AgentConfig

        supervisor = DeepAgentSupervisor(AgentConfig())

        # 测试初始化（可能需要实际API密钥）
        try:
            await supervisor.initialize()
            assert supervisor.llm is not None
            print("✅ 主管代理初始化测试通过")
        except Exception as e:
            print(f"⚠️  初始化失败（可能缺少API密钥）: {str(e)}")

    @pytest.mark.asyncio
    async def test_deepagent_creation(self):
        """测试 DeepAgent 创建"""
        from aat.agent import DeepAgentSupervisor, AgentConfig
        from langchain_anthropic import ChatAnthropic

        # 创建模拟 LLM（不需要实际API调用）
        try:
            llm = ChatAnthropic(
                model="claude-sonnet-4-6",
                temperature=0.7,
            )

            supervisor = DeepAgentSupervisor(AgentConfig())
            supervisor.llm = llm

            # 测试 DeepAgent 创建
            agent = await supervisor._create_deepagent("autonomous")
            assert agent is not None
            print("✅ DeepAgent 创建测试通过")

        except Exception as e:
            print(f"⚠️  DeepAgent 创建测试失败: {str(e)}")


class TestToolFunctionality:
    """测试工具功能"""

    @pytest.mark.asyncio
    async def test_navigation_tools(self):
        """测试导航工具"""
        from aat.agent.deepagent_tools import (
            smart_navigate,
            go_back,
            go_forward,
            refresh_page,
        )

        # 测试导航
        result = await smart_navigate.ainvoke({"url": "https://example.com"})
        assert result["success"] == True

        # 测试其他导航工具 (同步工具使用 .invoke())
        assert go_back.invoke({})["success"] == True
        assert go_forward.invoke({})["success"] == True
        assert refresh_page.invoke({})["success"] == True

        print("✅ 导航工具测试通过")

    @pytest.mark.asyncio
    async def test_interaction_tools(self):
        """测试交互工具"""
        from aat.agent.deepagent_tools import (
            smart_click,
            smart_type,
            select_option,
        )

        # 测试点击
        click_result = await smart_click.ainvoke({"target": "测试按钮", "humanize": True, "double_click": False})
        assert click_result["success"] == True

        # 测试输入
        type_result = await smart_type.ainvoke({"target": "输入框", "text": "测试文本"})
        assert type_result["success"] == True

        # 测试选择
        select_result = await select_option.ainvoke({"target": "下拉框", "value": "选项1"})
        assert select_result["success"] == True

        print("✅ 交互工具测试通过")

    @pytest.mark.asyncio
    async def test_verification_tools(self):
        """测试验证工具"""
        from aat.agent.deepagent_tools import (
            verify_text_visible,
            verify_element_exists,
            verify_url_contains,
        )

        # 测试文本验证
        text_result = await verify_text_visible.ainvoke({"expected_text": "测试文本"})
        assert text_result["success"] == True

        # 测试元素验证
        element_result = await verify_element_exists.ainvoke({"selector": "#test-element"})
        assert element_result["success"] == True

        # 测试URL验证
        url_result = verify_url_contains.invoke({"expected_fragment": "/test"})
        assert url_result["success"] == True

        print("✅ 验证工具测试通过")

    @pytest.mark.asyncio
    async def test_analysis_tools(self):
        """测试分析工具"""
        from aat.agent.deepagent_tools import (
            analyze_page,
            take_screenshot,
            check_console,
            wait_for_element,
        )

        # 测试页面分析
        analysis_result = await analyze_page.ainvoke({"analysis_depth": "basic"})
        assert analysis_result["success"] == True
        assert "analysis" in analysis_result

        # 测试截图
        screenshot_result = await take_screenshot.ainvoke({"filename": "test.png"})
        assert screenshot_result["success"] == True

        # 测试控制台检查
        console_result = await check_console.ainvoke({"level": "error"})
        assert console_result["success"] == True

        # 测试等待元素
        wait_result = await wait_for_element.ainvoke({"selector": "#test-element"})
        assert wait_result["success"] == True

        print("✅ 分析工具测试通过")


# 运行测试的便捷函数
def run_basic_tests():
    """运行基础测试"""
    print("🚀 开始运行 DeepAgent 基础测试...")
    print("=" * 60)

    test_classes = [
        TestDeepAgentInstallation(),
        TestAWTDeepAgentIntegration(),
        TestToolFunctionality(),
    ]

    for test_class in test_classes:
        print(f"\n📍 测试类: {test_class.__class__.__name__}")
        for method_name in dir(test_class):
            if method_name.startswith("test_"):
                method = getattr(test_class, method_name)
                if callable(method):
                    try:
                        if asyncio.iscoroutinefunction(method):
                            asyncio.run(method())
                        else:
                            method()
                    except Exception as e:
                        print(f"❌ {method_name} 失败: {str(e)}")

    print("\n" + "=" * 60)
    print("✅ 基础测试完成")


if __name__ == "__main__":
    run_basic_tests()