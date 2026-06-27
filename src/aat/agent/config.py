"""
AWT Agent Configuration - Simplified

Single, simple configuration class without over-engineering.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AgentMode(str, Enum):  # noqa: UP042
    """Agent execution mode"""

    INTERACTIVE = "interactive"
    AUTONOMOUS = "autonomous"
    CONSERVATIVE = "conservative"


class AgentConfig(BaseModel):
    """
    Simple agent configuration.

    All fields have sensible defaults - just pass what you need.
    """

    # AI settings
    provider: str = Field(default="anthropic", description="AI provider: anthropic|openai|google")
    model: str = Field(default="claude-sonnet-4-6", description="Model identifier")
    api_key: str | None = Field(default=None, description="API key (optional)")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096, ge=1)
    timeout: int = Field(default=60000, description="Request timeout in ms")

    # Browser settings
    browser_type: str = Field(default="chromium", description="Browser: chromium|firefox|webkit")
    headless: bool = Field(default=True, description="Run browser headless")
    browser_timeout: int = Field(default=30000, description="Browser timeout in ms")

    # Execution settings
    mode: AgentMode = Field(default=AgentMode.INTERACTIVE, description="Execution mode")
    execution_timeout: int = Field(default=60000, description="Test execution timeout in ms")
    max_retries: int = Field(default=3, ge=0, le=10, description="Max retry attempts")

    # Features
    screenshot_on_failure: bool = Field(default=True)
    save_console_logs: bool = Field(default=True)
    enable_sandbox: bool = Field(default=True)
    enable_planning: bool = Field(
        default=True,
        description=(
            "Enable structured task planning via the `write_todos` tool. "
            "When True (default) the agent is encouraged to plan multi-step "
            "tests and the plan is exposed via AgentSupervisor.get_plan()."
        ),
    )

    model_config = ConfigDict(extra="allow")


# Runtime context (not configuration)
class TestIntent(BaseModel):
    """Test intent specification"""

    type: str = "functional"
    features: list[str] = Field(default_factory=list)
    risk_level: str = "medium"

    model_config = ConfigDict(extra="allow")


class AgentContext(BaseModel):
    """Agent execution context"""

    current_url: str
    user_request: str
    test_intent: TestIntent
    history: list[dict] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")
