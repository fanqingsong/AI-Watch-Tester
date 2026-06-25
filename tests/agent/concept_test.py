"""
AWT Smart Agent 概念验证测试

这个文件包含基础的概念验证测试，用于验证：
1. 代理系统基础架构
2. 工具系统功能
3. 配置系统工作
4. 子代理配置
"""

import pytest

from aat.agent.config import AgentConfig, AgentMode, TestIntent
from aat.agent.supervisor import AWTSupervisorAgent
from aat.agent.tools import get_awt_tools, get_interaction_tools, get_navigation_tools


class TestAgentConfig:
    """测试配置系统"""

    def test_default_config(self):
        """测试默认配置"""
        config = AgentConfig()
        assert config.ai_model == "anthropic:claude-sonnet-4-6"
        assert config.default_mode == AgentMode.INTERACTIVE
        assert config.max_exploration_depth == 3

    def test_custom_config(self):
        """测试自定义配置"""
        config = AgentConfig(
            ai_model="openai:gpt-4", default_mode=AgentMode.AUTONOMOUS, max_exploration_depth=5
        )
        assert config.ai_model == "openai:gpt-4"
        assert config.default_mode == AgentMode.AUTONOMOUS
        assert config.max_exploration_depth == 5

    def test_test_intent(self):
        """测试测试意图"""
        intent = TestIntent(
            test_type="functional", target_features=["login", "authentication"], risk_level="high"
        )
        assert intent.test_type == "functional"
        assert len(intent.target_features) == 2
        assert intent.risk_level == "high"


class TestToolSystem:
    """测试工具系统"""

    def test_get_awt_tools(self):
        """测试获取所有工具"""
        tools = get_awt_tools()
        assert len(tools) >= 12
        tool_names = [tool.name for tool in tools]
        assert "smart_navigate" in tool_names
        assert "smart_click" in tool_names
        assert "smart_type" in tool_names

    def test_get_navigation_tools(self):
        """测试导航工具"""
        tools = get_navigation_tools()
        assert len(tools) == 4
        tool_names = [tool.name for tool in tools]
        assert "smart_navigate" in tool_names
        assert "go_back" in tool_names

    def test_get_interaction_tools(self):
        """测试交互工具"""
        tools = get_interaction_tools()
        assert len(tools) == 3
        tool_names = [tool.name for tool in tools]
        assert "smart_click" in tool_names
        assert "smart_type" in tool_names


class TestSupervisorAgent:
    """测试主管代理"""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """测试代理初始化"""
        config = AgentConfig()
        supervisor = AWTSupervisorAgent(config)

        # 测试代理未初始化时的状态
        assert supervisor.agent is None
        assert supervisor.config == config

    @pytest.mark.asyncio
    async def test_intent_understanding(self):
        """测试意图理解（简化版本）"""
        config = AgentConfig()
        supervisor = AWTSupervisorAgent(config)

        # 测试登录相关的意图理解
        intent = await supervisor._understand_intent("测试用户登录功能")
        assert intent.test_type == "functional"
        assert "authentication" in intent.target_features

        # 测试安全相关的意图理解
        intent = await supervisor._understand_intent("测试安全性漏洞")
        assert intent.test_type == "security"
        assert "security" in intent.target_features


class TestToolExecution:
    """测试工具执行（模拟）"""

    @pytest.mark.asyncio
    async def test_smart_navigate_tool(self):
        """测试导航工具"""
        from aat.agent.tools import smart_navigate

        result = await smart_navigate("http://localhost:3000")
        assert result["success"] == True
        assert "url" in result

    @pytest.mark.asyncio
    async def test_smart_click_tool(self):
        """测试点击工具"""
        from aat.agent.tools import smart_click

        result = await smart_click("登录按钮")
        assert result["success"] == True
        assert "action" in result

    @pytest.mark.asyncio
    async def test_smart_type_tool(self):
        """测试输入工具"""
        from aat.agent.tools import smart_type

        result = await smart_type("邮箱输入框", "test@example.com")
        assert result["success"] == True
        assert result["text"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_verify_text_visible_tool(self):
        """测试文本验证工具"""
        from aat.agent.tools import verify_text_visible

        result = await verify_text_visible("欢迎")
        assert result["success"] == True
        assert "assertion" in result


class TestSubagentConfigs:
    """测试子代理配置"""

    def test_explorer_agent_config(self):
        """测试探索代理配置"""
        from aat.agent.subagents import get_explorer_agent_config

        config = get_explorer_agent_config()
        assert config["name"] == "explorer"
        assert "system_prompt" in config
        assert "tools" in config
        assert len(config["tools"]) >= 4

    def test_tester_agent_config(self):
        """测试执行代理配置"""
        from aat.agent.subagents import get_tester_agent_config

        config = get_tester_agent_config()
        assert config["name"] == "tester"
        assert "system_prompt" in config
        assert "tools" in config
        assert len(config["tools"]) >= 10

    def test_analyzer_agent_config(self):
        """测试分析代理配置"""
        from aat.agent.subagents import get_analyzer_agent_config

        config = get_analyzer_agent_config()
        assert config["name"] == "analyzer"
        assert "system_prompt" in config
        assert "tools" in config


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_basic_agent_workflow(self):
        """测试基础代理工作流"""
        # 创建配置
        config = AgentConfig()
        supervisor = AWTSupervisorAgent(config)

        # 测试意图理解
        intent = await supervisor._understand_intent("测试注册功能")
        assert intent is not None

        # 测试结果解析
        mock_result = {"messages": [{"type": "ai", "content": "测试完成"}]}
        parsed = supervisor._parse_result(mock_result)
        assert parsed["success"] == True


def test_project_structure():
    """测试项目结构完整性"""
    from pathlib import Path

    # 检查关键文件是否存在
    agent_dir = Path("src/aat/agent")
    assert agent_dir.exists()

    required_files = [
        "src/aat/agent/__init__.py",
        "src/aat/agent/supervisor.py",
        "src/aat/agent/config.py",
        "src/aat/agent/tools/__init__.py",
        "src/aat/agent/subagents/__init__.py",
        "docs/agent/README.md",
        "docs/agent/DEEPAGENTS_IMPLEMENTATION.md",
        "examples/agent/quickstart.py",
    ]

    for file_path in required_files:
        assert Path(file_path).exists(), f"Missing file: {file_path}"


# 运行测试
if __name__ == "__main__":
    print("🧪 运行 AWT Smart Agent 概念验证测试\n")

    # 运行基础测试
    print("📋 测试配置系统...")
    test_config = TestAgentConfig()
    test_config.test_default_config()
    test_config.test_custom_config()
    test_config.test_test_intent()
    print("✅ 配置系统测试通过\n")

    print("📋 测试工具系统...")
    test_tools = TestToolSystem()
    test_tools.test_get_awt_tools()
    test_tools.test_get_navigation_tools()
    test_tools.test_get_interaction_tools()
    print("✅ 工具系统测试通过\n")

    print("📋 测试项目结构...")
    test_project_structure()
    print("✅ 项目结构测试通过\n")

    print("🎉 所有基础测试通过！")
    print("\n💡 运行完整测试:")
    print("   pytest tests/agent/concept_test.py -v")
    print("\n📖 查看快速开始:")
    print("   python examples/agent/quickstart.py")
