"""
AWT Agent Supervisor - Simplified

Main supervisor class without over-engineering.
Coordinates AI and browser automation for intelligent testing.

The heavy lifting is delegated to focused modules:
- ``browser_tools``: WebEngine interaction + LangChain tool definitions
- ``model_factory``: LLM model construction per provider
- ``prompts``: system prompt and filesystem permissions
- ``response_utils``: extracting text from agent responses
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aat.agent.browser_tools import BrowserToolbox, build_tools
from aat.agent.config import AgentConfig, AgentContext
from aat.agent.model_factory import build_model
from aat.agent.prompts import get_permissions, get_system_prompt
from aat.agent.response_utils import (
    AgentPlan,
    extract_plan,
    extract_response,
    format_plan,
)
from aat.core.config_models import EngineConfig


@dataclass
class ChatResult:
    """Structured outcome of an agent turn.

    Attributes:
        text: The assistant's textual reply (same value ``chat()`` returns).
        plan: The current task plan extracted from agent state. Empty when
            the agent did not use ``write_todos`` for this turn.
    """

    text: str
    plan: AgentPlan = field(default_factory=AgentPlan)

    def __str__(self) -> str:
        return self.text


class AgentSupervisor:
    """
    Main agent supervisor.

    Coordinates AI and browser automation for intelligent testing.
    """

    def __init__(self, config: AgentConfig | None = None, engine=None) -> None:
        """
        Initialize the supervisor.

        Args:
            config: Agent configuration (uses defaults if None)
            engine: Optional existing engine instance
        """
        self.config = config or AgentConfig()
        self._engine = engine  # 保存引擎引用供工具使用
        self._deep_agent = None
        self._is_initialized = False
        self.context: AgentContext | None = None
        self._work_dir: Path | None = None
        self._toolbox: BrowserToolbox | None = None
        # Task-planning state: the most recent plan extracted from the agent
        # state. Persists across turns so callers can read it after chat().
        self._plan: AgentPlan = AgentPlan()

    async def initialize(self) -> None:
        """Initialize the supervisor and its components."""
        if self._is_initialized:
            return

        try:
            # Import Deep Agents
            from deepagents import create_deep_agent

            # Create work directory
            self._work_dir = Path.cwd() / ".aat" / "agent_workspace"
            self._work_dir.mkdir(parents=True, exist_ok=True)

            # 🔧 创建或使用现有浏览器引擎
            if not self._engine:
                from aat.engine.web import WebEngine

                engine_config = EngineConfig(
                    type="web",
                    browser=self.config.browser_type,
                    headless=self.config.headless,
                    viewport_width=1280,
                    viewport_height=720,
                    timeout_ms=self.config.browser_timeout,
                )

                self._engine = WebEngine(config=engine_config)
                print(f"🌐 创建了新的浏览器引擎 (headless={self.config.headless})")

            print(
                f"🌐 浏览器配置: {self.config.browser_type}, "
                f"headless={self.config.headless}"
            )

            # Disable the built-in `write_todos` planning tool when the caller
            # opts out. The harness keeps TodoListMiddleware wired (it is part
            # of the protected scaffolding), so we hide the tool from the model
            # via a harness profile rather than removing the middleware.
            self._apply_planning_profile()

            # Build model based on provider using AWT adapters
            model_instance, model_identifier = build_model(self.config)

            # Create the Deep Agent with AWT tools
            create_kwargs = dict(
                tools=self._create_tools(),
                system_prompt=self._get_system_prompt(),
                permissions=self._get_permissions(),
            )
            if model_instance:
                self._deep_agent = create_deep_agent(
                    model=model_instance, **create_kwargs
                )
            else:
                self._deep_agent = create_deep_agent(
                    model=model_identifier, **create_kwargs
                )

            self._is_initialized = True
            planning_state = (
                "planning on" if self.config.enable_planning else "planning off"
            )
            print(f"✅ Agent initialized with {model_identifier} ({planning_state})")

        except ImportError as e:
            raise ImportError(
                "Deep Agents not installed. Run: pip install deepagents langchain-anthropic"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to initialize: {e}") from e

    # -- tool / prompt / response delegates ------------------------------

    def _create_tools(self) -> list[Any]:
        """Create AWT browser tools wired to the real WebEngine.

        Lazily constructs the BrowserToolbox on first call so this method
        is safe to invoke before ``initialize()`` (used in tests).
        """
        if self._toolbox is None:
            self._toolbox = BrowserToolbox(
                self._engine, work_dir_provider=lambda: self._work_dir
            )
        return build_tools(self._toolbox)

    def _get_permissions(self) -> list[Any]:
        """Get filesystem permissions."""
        return get_permissions()

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent.

        Omits the ``write_todos`` guidance when planning is disabled so the
        prompt and the visible tool set stay consistent.
        """
        return get_system_prompt(enable_planning=self.config.enable_planning)

    def _apply_planning_profile(self) -> None:
        """Hide the ``write_todos`` tool from the model when planning is off.

        ``TodoListMiddleware`` is part of the harness's protected scaffolding
        and cannot be removed, so we register a harness profile that excludes
        the tool name instead. This only runs when planning is disabled.

        Note: harness profiles are process-global in deepagents, so this
        affects any other agent created in the same process. AWT runs one
        supervisor per CLI session, so that is acceptable here.
        """
        if self.config.enable_planning:
            return
        from deepagents import HarnessProfile, register_harness_profile

        from aat.agent.model_factory import _normalize_provider

        profile = HarnessProfile(excluded_tools=frozenset({"write_todos"}))
        # Register under the normalized provider (deepagents key) plus the
        # common fallbacks. zhipuai uses a ChatOpenAI instance whose provider
        # resolves to "openai", so cover that path too.
        providers = {
            _normalize_provider(self.config.provider),
            self.config.provider,
            "openai",
            "anthropic",
        }
        for provider in providers:
            if provider:
                register_harness_profile(provider, profile)

    def _extract_response(self, response: Any) -> str:
        """Extract text content from a Deep Agent response."""
        return extract_response(response)

    def _extract_plan(self, response: Any) -> AgentPlan:
        """Extract the task plan from a Deep Agent response."""
        return extract_plan(response)

    def _ensure_initialized(self) -> None:
        """Ensure the supervisor is initialized."""
        if not self._is_initialized:
            raise RuntimeError(
                "AgentSupervisor must be initialized before use. "
                "Call await initialize()"
            )

    # -- public API -------------------------------------------------------

    async def chat(self, message: str, history: list[dict] | None = None) -> str:
        """Send a user message to the agent and return its textual response.

        Also updates the supervisor's task plan (see :meth:`get_plan`),
        which is extracted from the agent state after each turn.

        Args:
            message: The user's message text.
            history: Optional prior conversation messages as a list of
                ``{"role": "user"|"assistant", "content": str}`` dicts.
                When provided, the full history is sent to give the agent
                conversational context.

        Returns:
            The agent's response text.

        Raises:
            RuntimeError: If the supervisor has not been initialized.
        """
        result = await self.chat_with_plan(message, history=history)
        return result.text

    async def chat_with_plan(
        self, message: str, history: list[dict] | None = None
    ) -> ChatResult:
        """Like :meth:`chat` but also return the task plan for this turn.

        Useful when the caller wants to render the plan (e.g. a checklist
        of test steps) alongside the textual reply.

        Returns:
            A :class:`ChatResult` holding both the reply text and the plan.
        """
        self._ensure_initialized()
        assert self._deep_agent is not None  # noqa: S101 - narrowed by init

        messages: list[dict] = list(history) if history else []
        messages.append({"role": "user", "content": message})

        agent_response = await self._deep_agent.ainvoke({"messages": messages})
        text = self._extract_response(agent_response)
        # Refresh the cached plan from agent state. For multi-step tasks the
        # agent will have called `write_todos`; for trivial turns this stays
        # empty so callers that read get_plan() simply see "no plan".
        self._plan = self._extract_plan(agent_response)
        return ChatResult(text=text, plan=self._plan)

    def get_plan(self) -> AgentPlan:
        """Return the most recent task plan, or an empty plan if none exists.

        The plan is updated after every :meth:`chat` / :meth:`chat_with_plan`
        call. It reflects the agent state at the end of the last turn.
        """
        return self._plan

    def render_plan(self) -> str:
        """Render the current plan as a human-readable checklist.

        Returns an empty string when there is no plan to show.
        """
        return format_plan(self._plan)

    async def cleanup(self) -> None:
        """Clean up resources."""
        # Stop the browser engine if we own it and it has been started.
        if self._engine is not None:
            try:
                # Prefer the public page property; fall back to the private
                # attribute only as a safety net for partial init states.
                started = False
                try:
                    _ = self._engine.page  # raises if not started
                    started = True
                except Exception:
                    started = getattr(self._engine, "_page", None) is not None
                if started:
                    await self._engine.stop()
            except Exception as e:  # noqa: BLE001 - best-effort cleanup
                print(f"⚠️  Engine stop failed: {e}")

        # Deep agents may expose an async cleanup(); call it if present.
        if self._deep_agent is not None:
            cleanup_fn = getattr(self._deep_agent, "cleanup", None)
            if callable(cleanup_fn):
                try:
                    result = cleanup_fn()
                    if hasattr(result, "__await__"):
                        await result
                except Exception as e:  # noqa: BLE001 - best-effort cleanup
                    print(f"⚠️  Deep agent cleanup failed: {e}")

        self._is_initialized = False
        print("✅ Agent cleaned up")


# Convenience factory function
async def create_supervisor(config: AgentConfig | None = None, engine=None) -> AgentSupervisor:
    """
    Create and initialize an agent supervisor.

    Args:
        config: Optional configuration
        engine: Optional engine instance

    Returns:
        Initialized AgentSupervisor instance
    """
    supervisor = AgentSupervisor(config, engine)
    await supervisor.initialize()
    return supervisor
