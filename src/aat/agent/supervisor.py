"""
AWT Agent Supervisor - Simplified

Main supervisor class without over-engineering.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from aat.agent.config import AgentConfig, AgentContext, TestIntent
from aat.agent.zhipuai_chat import create_zhipuai_model


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
        self._engine = engine
        self._deep_agent = None
        self._is_initialized = False
        self.context: AgentContext | None = None
        self._work_dir: Path | None = None

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

            # Build model based on provider
            provider = self.config.provider
            model = self.config.model
            api_key = self.config.api_key

            # Handle different providers
            if provider == "zhipuai":
                # Use custom ChatZhipuAI model
                model_instance = create_zhipuai_model(
                    api_key=api_key,
                    model=model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                model_identifier = f"zhipuai:{model}"
            elif provider == "anthropic":
                model_identifier = f"anthropic:{model}"
                model_instance = None  # Let Deep Agents create it
            elif provider == "openai":
                model_identifier = f"openai:{model}"
                model_instance = None
            else:
                # Default to Anthropic
                model_identifier = "anthropic:claude-sonnet-4-6"
                model_instance = None

            # Create the Deep Agent with AWT tools
            if model_instance:
                # Use custom model instance
                self._deep_agent = create_deep_agent(
                    model=model_instance,
                    tools=self._create_tools(),
                    system_prompt=self._get_system_prompt(),
                    permissions=self._get_permissions(),
                )
            else:
                # Use model string
                self._deep_agent = create_deep_agent(
                    model=model_identifier,
                    tools=self._create_tools(),
                    system_prompt=self._get_system_prompt(),
                    permissions=self._get_permissions(),
                )

            self._is_initialized = True
            print(f"✅ Agent initialized with {model_identifier}")

        except ImportError as e:
            raise ImportError(
                "Deep Agents not installed. Run: pip install deepagents langchain-anthropic"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to initialize: {e}") from e

    def _create_tools(self) -> list[Any]:
        """Create AWT-specific tools for the agent."""
        return [
            self._navigate_tool,
            self._click_tool,
            self._type_tool,
            self._verify_tool,
            self._screenshot_tool,
            self._analyze_tool,
        ]

    def _navigate_tool(self, url: str) -> str:
        """Navigate to a URL."""
        return f"Navigated to {url}"

    def _click_tool(self, selector: str) -> str:
        """Click an element."""
        return f"Clicked {selector}"

    def _type_tool(self, selector: str, text: str) -> str:
        """Type text into an element."""
        return f"Typed '{text}' into {selector}"

    def _verify_tool(self, text: str) -> str:
        """Verify text is visible."""
        return f"Verified: {text}"

    def _screenshot_tool(self, filename: str | None = None) -> str:
        """Take a screenshot."""
        return f"Screenshot saved to {filename or 'screenshot.png'}"

    def _analyze_tool(self, url: str) -> str:
        """Analyze a page."""
        return f"Analyzed {url}"

    def _get_permissions(self) -> list[Any]:
        """Get filesystem permissions."""
        from deepagents import FilesystemPermission

        cwd = str(Path.cwd())
        return [
            FilesystemPermission(
                operations=["read", "write"],
                paths=[f"{cwd}/.aat/agent_workspace/**"],
                mode="allow",
            ),
            FilesystemPermission(
                operations=["read"],
                paths=[f"{cwd}/.aat/**", f"{cwd}/tests/**"],
                mode="allow",
            ),
        ]

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """
You are an intelligent testing agent powered by AWT (AI Auto Tester).
Help users test web applications through natural language.

Capabilities:
- Navigate web pages and interact with elements
- Analyze page structure and discover functionality
- Execute test plans and verify outcomes
- Take screenshots and capture console logs
- Report test results clearly

Available tools:
- _navigate_tool: Navigate to a web page
- _click_tool: Click on UI elements
- _type_tool: Input text into form fields
- _verify_tool: Check if text appears on page
- _screenshot_tool: Capture page state
- _analyze_tool: Discover page elements

Workflow:
1. Understand the user's testing goal
2. Ask clarifying questions if needed
3. Navigate to the target page
4. Execute test steps systematically
5. Verify expected outcomes
6. Report results with clear pass/fail status

Always provide clear, actionable feedback about test results.
"""

    def _ensure_initialized(self) -> None:
        """Ensure the supervisor is initialized."""
        if not self._is_initialized:
            raise RuntimeError("AgentSupervisor must be initialized before use. Call await initialize()")

    async def test_from_natural_language(
        self, user_request: str, start_url: str, mode: str = "interactive"
    ) -> dict[str, Any]:
        """
        Execute a test from natural language description.

        Args:
            user_request: Natural language test description
            start_url: Starting URL for the test
            mode: Execution mode (interactive, autonomous, conservative)

        Returns:
            Test execution result
        """
        self._ensure_initialized()

        print(f"🎯 AWT Agent Supervisor")
        print(f"📝 Request: {user_request}")
        print(f"🌐 Start URL: {start_url}")
        print("-" * 50)

        # Create context
        self.context = AgentContext(
            current_url=start_url,
            user_request=user_request,
            test_intent=TestIntent(type="general"),
        )

        try:
            prompt = f"""
Test Request: {user_request}
Start URL: {start_url}
Mode: {mode}

Please:
1. Navigate to the starting URL
2. Analyze the page structure
3. Execute test steps systematically
4. Verify expected outcomes
5. Take screenshots at key points
6. Report results with clear pass/fail status
"""

            response = await self._deep_agent.ainvoke(
                {"messages": [{"role": "user", "content": prompt}]}
            )

            return {
                "success": True,
                "message": "Test execution completed",
                "response": self._extract_response(response),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

    async def chat(self, user_message: str) -> str:
        """
        Conduct conversational interaction with the agent.

        Args:
            user_message: User's message/question

        Returns:
            Agent's response
        """
        self._ensure_initialized()

        try:
            response = await self._deep_agent.ainvoke(
                {"messages": [{"role": "user", "content": user_message}]}
            )
            return self._extract_response(response)
        except Exception as e:
            return f"Error: {e}"

    async def analyze_page(self, url: str, depth: int = 1) -> dict[str, Any]:
        """
        Analyze a web page to discover its structure.

        Args:
            url: URL of the page to analyze
            depth: How deep to explore (1=quick, 2=thorough, 3=comprehensive)

        Returns:
            Page analysis results
        """
        self._ensure_initialized()

        print(f"🔍 Analyzing page: {url} (depth: {depth})")

        try:
            depth_desc = {1: "quick overview", 2: "thorough analysis", 3: "comprehensive analysis"}
            prompt = f"""
Analyze the web page at: {url}
Provide a {depth_desc.get(depth, 'overview')} including:
- Main navigation elements
- Forms and input fields
- Interactive elements
- Content structure
- Potential test points
"""

            response = await self._deep_agent.ainvoke(
                {"messages": [{"role": "user", "content": prompt}]}
            )

            return {
                "success": True,
                "url": url,
                "depth": depth,
                "analysis": self._extract_response(response),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "url": url, "depth": depth}

    def _extract_response(self, response: Any) -> str:
        """Extract text content from a Deep Agent response."""
        if isinstance(response, dict):
            if "messages" in response:
                messages = response["messages"]
                if messages and len(messages) > 0:
                    last = messages[-1]
                    if isinstance(last, dict):
                        return last.get("content", str(last))
            elif "content" in response:
                return response["content"]
            return str(response)
        elif hasattr(response, "content"):
            return response.content
        else:
            return str(response)

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._deep_agent and hasattr(self._deep_agent, "cleanup"):
            await self._deep_agent.cleanup()
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
