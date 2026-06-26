"""
AWT Agent Supervisor - Simplified

Main supervisor class without over-engineering.
Uses AWT's adapter system for AI provider integration.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from aat.agent.config import AgentConfig, AgentContext, TestIntent
from aat.adapters.zhipuai import ZhipuAIAdapter
from aat.core import AIConfig as AWTAIConfig
from aat.core.config_models import EngineConfig


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

    async def initialize(self) -> None:
        """Initialize the supervisor and its components."""
        if self._is_initialized:
            return

        try:
            # Import Deep Agents and LangChain
            from deepagents import create_deep_agent
            from langchain_openai import ChatOpenAI

            # Create work directory
            self._work_dir = Path.cwd() / ".aat" / "agent_workspace"
            self._work_dir.mkdir(parents=True, exist_ok=True)

            # 🔧 创建或使用现有浏览器引擎
            if not self._engine:
                from aat.engine.web import WebEngine

                # 使用 AWT 的配置结构
                engine_config = EngineConfig(
                    type="web",
                    browser=self.config.browser_type,
                    headless=False,  # 强制非headless模式
                    viewport_width=1280,
                    viewport_height=720,
                    timeout_ms=self.config.browser_timeout,
                )

                self._engine = WebEngine(config=engine_config)
                print("🌐 创建了新的浏览器引擎 (非headless模式)")

            print(f"🌐 浏览器配置: {self.config.browser_type}, headless=False")

            # Build model based on provider using AWT adapters
            provider = self.config.provider
            model = self.config.model
            api_key = self.config.api_key

            if provider == "zhipuai":
                # Use AWT's ZhipuAIAdapter to get proper client
                awt_config = AWTAIConfig(
                    provider="zhipuai",
                    api_key=api_key,
                    model=model,
                )
                zhipuai_adapter = ZhipuAIAdapter(awt_config)

                # Create ChatOpenAI using AWT adapter's client configuration
                model_instance = ChatOpenAI(
                    api_key=api_key,
                    base_url=zhipuai_adapter.base_url,
                    model=model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                model_identifier = f"zhipuai:{model}"
                print(f"📌 Using AWT ZhipuAIAdapter with base_url: {zhipuai_adapter.base_url}")

            elif provider == "anthropic":
                model_identifier = f"anthropic:{model}"
                model_instance = None
            elif provider == "openai":
                model_identifier = f"openai:{model}"
                model_instance = None
            else:
                # Default to Anthropic
                model_identifier = "anthropic:claude-sonnet-4-6"
                model_instance = None

            # Create the Deep Agent with AWT tools
            if model_instance:
                self._deep_agent = create_deep_agent(
                    model=model_instance,
                    tools=self._create_tools(),
                    system_prompt=self._get_system_prompt(),
                    permissions=self._get_permissions(),
                )
            else:
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

    async def _navigate_tool(self, url: str) -> str:
        """Navigate to a URL using real browser engine."""
        print(f"🌐 正在导航到: {url}")
        try:
            if self._engine and hasattr(self._engine, 'goto'):
                await self._engine.goto(url)
                return f"Successfully navigated to {url}"
            else:
                return f"Navigated to {url} (simulation mode)"
        except Exception as e:
            return f"Navigation failed: {str(e)}"

    async def _click_tool(self, selector: str) -> str:
        """Click an element using real browser engine."""
        print(f"🖱️  正在点击元素: {selector}")
        try:
            if self._engine and hasattr(self._engine, 'click'):
                await self._engine.click(selector)
                return f"Successfully clicked {selector}"
            else:
                return f"Clicked {selector} (simulation mode)"
        except Exception as e:
            return f"Click failed: {str(e)}"

    async def _type_tool(self, selector: str, text: str) -> str:
        """Type text into an element using real browser engine."""
        print(f"⌨️  正在输入文本到 {selector}: '{text[:30]}...'")
        try:
            if self._engine and hasattr(self._engine, 'type'):
                await self._engine.type(selector, text)
                return f"Successfully typed '{text}' into {selector}"
            else:
                return f"Typed '{text}' into {selector} (simulation mode)"
        except Exception as e:
            return f"Type failed: {str(e)}"

    async def _verify_tool(self, text: str) -> str:
        """Verify text is visible using real browser engine."""
        print(f"🔍 正在验证文本: '{text[:30]}...'")
        try:
            if self._engine and hasattr(self._engine, 'verify_text'):
                result = await self._engine.verify_text(text)
                return f"Text verification: {result}"
            else:
                return f"Verified text: '{text}' (simulation mode)"
        except Exception as e:
            return f"Verification failed: {str(e)}"

    async def _screenshot_tool(self, filename: str | None = None) -> str:
        """Take a screenshot using real browser engine."""
        print(f"📸 正在截图: {filename or 'screenshot.png'}")
        try:
            if self._engine and hasattr(self._engine, 'screenshot'):
                screenshot_path = await self._engine.screenshot(filename)
                return f"Screenshot saved to {screenshot_path}"
            else:
                return f"Screenshot saved to {filename or 'screenshot.png'} (simulation mode)"
        except Exception as e:
            return f"Screenshot failed: {str(e)}"

    async def _analyze_tool(self, url: str) -> str:
        """Analyze a page using real browser engine."""
        print(f"🔬 正在分析页面: {url}")
        try:
            if self._engine and hasattr(self._engine, 'analyze'):
                result = await self._engine.analyze(url)
                return f"Page analysis: {result}"
            else:
                return f"Analyzed {url} (simulation mode)"
        except Exception as e:
            return f"Analysis failed: {str(e)}"

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
