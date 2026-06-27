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
        assert len(tools) == 7  # navigate, click, type, verify, get_text, screenshot, analyze

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
