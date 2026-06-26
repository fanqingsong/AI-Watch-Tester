"""
Agent Supervisor Tests - Simplified

Tests for the simplified AgentSupervisor.
"""

import pytest

from aat.agent import AgentSupervisor, AgentConfig, create_supervisor


class TestAgentSupervisor:
    """Test suite for AgentSupervisor."""

    @pytest.mark.asyncio
    async def test_supervisor_initialization(self):
        """Test that supervisor can be initialized."""
        supervisor = AgentSupervisor()

        assert supervisor.config is not None
        assert supervisor._deep_agent is None  # Not initialized yet
        assert supervisor.context is None

    @pytest.mark.asyncio
    async def test_supervisor_factory(self):
        """Test the factory function for creating supervisor."""
        supervisor = await create_supervisor()

        assert supervisor is not None
        assert supervisor._is_initialized is True
        assert supervisor._deep_agent is not None
        assert supervisor._work_dir is not None

        await supervisor.cleanup()

    @pytest.mark.asyncio
    async def test_supervisor_with_custom_config(self):
        """Test supervisor creation with custom configuration."""
        custom_config = AgentConfig(
            provider="anthropic",
            model="claude-sonnet-4-6",
        )

        supervisor = AgentSupervisor(config=custom_config)

        assert supervisor.config.provider == "anthropic"
        assert supervisor.config.model == "claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_tools_creation(self):
        """Test that tools are created correctly."""
        supervisor = await create_supervisor()

        tools = supervisor._create_tools()

        assert isinstance(tools, list)
        assert len(tools) == 6  # navigate, click, type, verify, screenshot, analyze

        await supervisor.cleanup()

    @pytest.mark.asyncio
    async def test_permissions(self):
        """Test filesystem permissions configuration."""
        supervisor = await create_supervisor()

        permissions = supervisor._get_permissions()

        assert isinstance(permissions, list)
        assert len(permissions) > 0

        await supervisor.cleanup()

    @pytest.mark.asyncio
    async def test_system_prompt(self):
        """Test system prompt generation."""
        supervisor = await create_supervisor()

        prompt = supervisor._get_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "testing" in prompt.lower()

        await supervisor.cleanup()

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_chat_basic(self):
        """Test basic chat functionality (requires API keys)."""
        supervisor = await create_supervisor()

        response = await supervisor.chat("Hello!")

        assert isinstance(response, str)
        assert len(response) > 0

        await supervisor.cleanup()

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_test_from_natural_language_basic(self):
        """Test test execution from natural language (requires API keys)."""
        supervisor = await create_supervisor()

        result = await supervisor.test_from_natural_language(
            user_request="Navigate to example.com and check if it loads",
            start_url="https://example.com",
            mode="interactive",
        )

        assert isinstance(result, dict)
        assert "success" in result

        await supervisor.cleanup()

    def test_extract_response_dict(self):
        """Test response content extraction from dict."""
        supervisor = AgentSupervisor()

        # Test with messages format
        response = {
            "messages": [
                {"content": "First message"},
                {"content": "Second message"},
            ]
        }
        content = supervisor._extract_response(response)
        assert content == "Second message"

        # Test with direct content
        response = {"content": "Direct content"}
        content = supervisor._extract_response(response)
        assert content == "Direct content"

    def test_extract_response_string(self):
        """Test response content extraction from string."""
        supervisor = AgentSupervisor()

        content = supervisor._extract_response("Plain string")
        assert content == "Plain string"

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test supervisor cleanup."""
        supervisor = await create_supervisor()

        assert supervisor._is_initialized is True

        await supervisor.cleanup()

        assert supervisor._is_initialized is False

    @pytest.mark.asyncio
    async def test_ensure_initialized_error(self):
        """Test that using supervisor before initialization raises error."""
        supervisor = AgentSupervisor()

        with pytest.raises(RuntimeError, match="must be initialized"):
            await supervisor.chat("Hello")

    @pytest.mark.asyncio
    async def test_analyze_page(self):
        """Test page analysis functionality."""
        supervisor = await create_supervisor()

        result = await supervisor.analyze_page("https://example.com", depth=1)

        assert isinstance(result, dict)
        assert "success" in result
        assert "example.com" in result["url"]
        assert result["depth"] == 1

        await supervisor.cleanup()
