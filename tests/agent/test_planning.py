"""
Tests for the agent task-planning feature.

Covers the planning data model (Todo / AgentPlan), plan extraction from Deep
Agent state responses, the planning-aware system prompt, the
``enable_planning`` config flag, and the supervisor's plan API. These are
unit tests that do not call a real LLM.
"""

import pytest

from aat.agent import (
    AgentConfig,
    AgentPlan,
    AgentSupervisor,
    Todo,
    extract_plan,
    format_plan,
)
from aat.agent.prompts import SYSTEM_PROMPT, get_system_prompt
from aat.agent.response_utils import format_plan as _format_plan

# -- data model --------------------------------------------------------------


class TestTodoModel:
    def test_default_status_is_pending(self):
        todo = Todo(content="Do something")
        assert todo.status == "pending"

    @pytest.mark.parametrize("status", ["pending", "in_progress", "completed"])
    def test_valid_statuses(self, status):
        todo = Todo(content="x", status=status)
        assert todo.status == status


class TestAgentPlan:
    def test_empty_plan(self):
        plan = AgentPlan()
        assert plan.is_empty
        assert not plan.is_complete
        assert plan.summary() == "0/0"

    def test_all_completed(self):
        plan = AgentPlan(todos=[Todo(content="a", status="completed")])
        assert not plan.is_empty
        assert plan.is_complete
        assert plan.summary() == "1/1"

    def test_partial_progress(self):
        plan = AgentPlan(
            todos=[
                Todo(content="a", status="completed"),
                Todo(content="b", status="in_progress"),
                Todo(content="c", status="pending"),
            ]
        )
        assert not plan.is_complete
        assert plan.summary() == "1/3"

    def test_empty_plan_not_complete(self):
        # No todos -> not "complete" even though vacuously all-done.
        assert not AgentPlan().is_complete


# -- extract_plan ------------------------------------------------------------


class TestExtractPlan:
    def test_no_todos_key_returns_empty(self):
        plan = extract_plan({"messages": []})
        assert plan.is_empty

    def test_empty_todos_list(self):
        plan = extract_plan({"todos": []})
        assert plan.is_empty

    def test_dict_todos(self):
        response = {
            "todos": [
                {"content": "Navigate to login", "status": "completed"},
                {"content": "Submit form", "status": "in_progress"},
                {"content": "Verify dashboard", "status": "pending"},
            ]
        }
        plan = extract_plan(response)
        assert len(plan.todos) == 3
        assert plan.todos[0].content == "Navigate to login"
        assert plan.todos[0].status == "completed"
        assert plan.todos[1].status == "in_progress"
        assert plan.summary() == "1/3"

    def test_description_fallback(self):
        # Some shapes may use 'description' instead of 'content'.
        plan = extract_plan({"todos": [{"description": "step one"}]})
        assert plan.todos[0].content == "step one"

    def test_invalid_status_defaults_to_pending(self):
        plan = extract_plan({"todos": [{"content": "x", "status": "weird"}]})
        assert plan.todos[0].status == "pending"

    def test_skips_items_without_content(self):
        plan = extract_plan({"todos": [{"content": ""}, {"content": "ok"}]})
        assert len(plan.todos) == 1
        assert plan.todos[0].content == "ok"

    def test_object_with_todos_attr(self):
        class _Resp:
            def __init__(self, todos):
                self.todos = todos

        resp = _Resp([{"content": "a", "status": "completed"}])
        plan = extract_plan(resp)
        assert plan.todos[0].content == "a"


# -- format_plan -------------------------------------------------------------


class TestFormatPlan:
    def test_empty_plan_renders_nothing(self):
        assert format_plan(AgentPlan()) == ""

    def test_renders_checklist(self):
        plan = AgentPlan(
            todos=[
                Todo(content="done step", status="completed"),
                Todo(content="active step", status="in_progress"),
                Todo(content="later step", status="pending"),
            ]
        )
        out = format_plan(plan)
        assert "1/3" in out
        assert "done step" in out
        assert "active step" in out
        assert "later step" in out
        # Status markers present
        assert "✅" in out
        assert "🔄" in out
        assert "⬜" in out

    def test_module_alias_matches_function(self):
        # The re-exported name and the direct import should be the same.
        assert format_plan is _format_plan


# -- system prompt -----------------------------------------------------------


class TestSystemPrompt:
    def test_prompt_has_testing_context(self):
        assert "testing" in SYSTEM_PROMPT.lower()

    def test_planning_enabled_includes_tool(self):
        prompt = get_system_prompt(enable_planning=True)
        assert "write_todos" in prompt
        assert "## Task planning" in prompt

    def test_planning_disabled_omits_tool(self):
        prompt = get_system_prompt(enable_planning=False)
        assert "write_todos" not in prompt
        assert "## Task planning" not in prompt

    def test_both_versions_list_browser_tools(self):
        for enabled in (True, False):
            prompt = get_system_prompt(enable_planning=enabled)
            for tool in (
                "navigate_tool",
                "get_text_tool",
                "click_tool",
                "verify_tool",
                "screenshot_tool",
                "analyze_tool",
            ):
                assert tool in prompt, f"{tool} missing when planning={enabled}"


# -- config flag -------------------------------------------------------------


class TestEnablePlanningConfig:
    def test_default_is_enabled(self):
        assert AgentConfig().enable_planning is True

    def test_can_disable(self):
        config = AgentConfig(enable_planning=False)
        assert config.enable_planning is False


# -- provider alias (claude -> anthropic) -----------------------------------


class TestProviderAlias:
    """AWT calls Anthropic 'claude' everywhere except the agent's model
    factory, which expects the deepagents 'anthropic' prefix. The factory must
    accept the legacy 'claude' name so existing project configs keep working.
    """

    def test_claude_normalizes_to_anthropic(self):
        from aat.agent.model_factory import _normalize_provider

        assert _normalize_provider("claude") == "anthropic"
        # Non-aliased providers pass through unchanged.
        assert _normalize_provider("openai") == "openai"
        assert _normalize_provider("zhipuai") == "zhipuai"

    def test_build_model_accepts_claude_provider(self):
        from aat.agent.model_factory import build_model

        config = AgentConfig(
            provider="claude",
            model="claude-sonnet-4-20250514",
            api_key="dummy-key",
        )
        model_instance, identifier = build_model(config)
        # Native provider -> no concrete instance; identifier carries the
        # normalized deepagents prefix.
        assert model_instance is None
        assert identifier == "anthropic:claude-sonnet-4-20250514"

    def test_build_model_accepts_anthropic_provider(self):
        from aat.agent.model_factory import build_model

        config = AgentConfig(provider="anthropic", model="claude-sonnet-4-6")
        _, identifier = build_model(config)
        assert identifier == "anthropic:claude-sonnet-4-6"

    def test_build_model_rejects_unknown_provider(self):
        from aat.agent.model_factory import build_model

        config = AgentConfig(provider="unknown-llm", model="m")
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            build_model(config)


# -- supervisor plan API -----------------------------------------------------


class TestSupervisorPlanApi:
    def test_get_plan_starts_empty(self):
        supervisor = AgentSupervisor()
        assert supervisor.get_plan().is_empty

    def test_render_plan_empty_before_chat(self):
        supervisor = AgentSupervisor()
        assert supervisor.render_plan() == ""

    def test_extract_plan_delegates(self):
        supervisor = AgentSupervisor()
        plan = supervisor._extract_plan({"todos": [{"content": "x", "status": "completed"}]})
        assert plan.summary() == "1/1"

    def test_system_prompt_respects_config(self):
        # Planning on (default)
        on = AgentSupervisor(AgentConfig(enable_planning=True))
        assert "write_todos" in on._get_system_prompt()

        # Planning off
        off = AgentSupervisor(AgentConfig(enable_planning=False))
        assert "write_todos" not in off._get_system_prompt()

    def test_apply_planning_profile_is_noop_when_enabled(self):
        # Should not raise and should not register anything.
        supervisor = AgentSupervisor(AgentConfig(enable_planning=True))
        supervisor._apply_planning_profile()  # no-op

    def test_apply_planning_profile_registers_when_disabled(self):
        from deepagents.profiles.harness.harness_profiles import _HARNESS_PROFILES

        supervisor = AgentSupervisor(AgentConfig(enable_planning=False))
        supervisor._apply_planning_profile()
        # At least the configured provider should have a profile now.
        assert "anthropic" in _HARNESS_PROFILES
        profile = _HARNESS_PROFILES["anthropic"]
        assert "write_todos" in profile.excluded_tools


# -- ChatResult --------------------------------------------------------------


class TestChatResult:
    def test_str_returns_text(self):
        from aat.agent import ChatResult

        result = ChatResult(text="hello", plan=AgentPlan())
        assert str(result) == "hello"
        assert result.plan.is_empty

    def test_str_defaults(self):
        from aat.agent import ChatResult

        result = ChatResult(text="ok")
        assert result.plan.is_empty


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
