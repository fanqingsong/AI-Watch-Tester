"""
Basic functionality test for simplified agent module.

This test verifies that the simplified module maintains essential functionality.
"""

import pytest
from aat.agent import AgentSupervisor, AgentConfig, AgentMode


def test_config_creation():
    """Test basic configuration creation."""
    # Default config
    config = AgentConfig()
    assert config.provider == "anthropic"
    assert config.model == "claude-sonnet-4-6"
    assert config.mode == AgentMode.INTERACTIVE

    # Custom config
    custom = AgentConfig(
        provider="openai",
        model="gpt-4",
        mode=AgentMode.AUTONOMOUS,
    )
    assert custom.provider == "openai"
    assert custom.model == "gpt-4"
    assert custom.mode == AgentMode.AUTONOMOUS


def test_supervisor_instantiation():
    """Test supervisor can be created."""
    supervisor = AgentSupervisor()
    assert supervisor.config is not None
    assert supervisor._deep_agent is None
    assert supervisor._is_initialized is False


def test_supervisor_with_config():
    """Test supervisor with custom config."""
    config = AgentConfig(provider="openai", model="gpt-4")
    supervisor = AgentSupervisor(config=config)
    assert supervisor.config.provider == "openai"


def test_error_before_initialization():
    """Test that using supervisor before initialization raises error."""
    supervisor = AgentSupervisor()

    with pytest.raises(RuntimeError, match="must be initialized"):
        _ = supervisor._ensure_initialized()


def test_tools_list():
    """Test tools are created."""
    from langchain_core.tools import BaseTool

    supervisor = AgentSupervisor()
    tools = supervisor._create_tools()

    assert len(tools) == 7  # navigate, click, type, verify, get_text, screenshot, analyze
    assert all(isinstance(tool, BaseTool) for tool in tools)


def test_permissions_list():
    """Test permissions are created."""
    supervisor = AgentSupervisor()
    # We can't test full permissions without Deep Agents installed
    # but we can verify the method exists and is callable
    assert callable(supervisor._get_permissions)


def test_system_prompt():
    """Test system prompt generation."""
    supervisor = AgentSupervisor()
    prompt = supervisor._get_system_prompt()

    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "AWT" in prompt or "testing" in prompt.lower()


def test_extract_response_dict():
    """Test response extraction from dict."""
    supervisor = AgentSupervisor()

    # Messages format
    response = {"messages": [{"content": "test"}]}
    assert supervisor._extract_response(response) == "test"

    # Direct content
    response = {"content": "direct"}
    assert supervisor._extract_response(response) == "direct"


def test_extract_response_string():
    """Test response extraction from string."""
    supervisor = AgentSupervisor()
    assert supervisor._extract_response("plain text") == "plain text"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
