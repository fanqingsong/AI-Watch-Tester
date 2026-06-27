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

    async def _ensure_engine_started(self) -> None:
        """Start the browser engine if it is not running yet."""
        if self._engine is None:
            return
        if self._engine._page is None:
            await self._engine.start()

    def _create_tools(self) -> list[Any]:
        """Create AWT browser tools wired to the real WebEngine."""
        from langchain_core.tools import tool

        supervisor = self

        @tool
        async def navigate_tool(url: str) -> str:
            """Navigate the browser to a URL. Call this first when testing a website."""
            await supervisor._ensure_engine_started()
            return await supervisor._navigate_with_engine(supervisor._engine, url)

        @tool
        async def click_tool(selector: str) -> str:
            """Click a page element using a CSS selector (e.g. '#search-icon', 'button[type=submit]')."""
            await supervisor._ensure_engine_started()
            return await supervisor._click_with_engine(supervisor._engine, selector)

        @tool
        async def type_tool(selector: str, text: str) -> str:
            """Type text into an input field identified by CSS selector."""
            await supervisor._ensure_engine_started()
            return await supervisor._type_with_engine(supervisor._engine, selector, text)

        @tool
        async def verify_tool(text: str) -> str:
            """Verify that expected text appears on the current page."""
            await supervisor._ensure_engine_started()
            return await supervisor._verify_with_engine(supervisor._engine, text)

        @tool
        async def screenshot_tool(filename: str | None = None) -> str:
            """Capture a screenshot of the current browser page."""
            await supervisor._ensure_engine_started()
            return await supervisor._screenshot_with_engine(supervisor._engine, filename)

        @tool
        async def analyze_tool(url: str) -> str:
            """Navigate to a URL and summarize page structure (forms, buttons, links)."""
            await supervisor._ensure_engine_started()
            return await supervisor._analyze_with_engine(supervisor._engine, url)

        return [
            navigate_tool,
            click_tool,
            type_tool,
            verify_tool,
            screenshot_tool,
            analyze_tool,
        ]

    async def _navigate_with_engine(self, engine, url: str) -> str:
        """
        Navigate to a URL using real browser engine.

        Args:
            engine: Browser engine instance
            url: URL to navigate to

        Returns:
            Navigation result message
        """
        print(f"🌐 正在导航到: {url}")
        try:
            if engine is None:
                return "Navigation failed: browser engine not available"
            if engine._page is None:
                await engine.start()
            await engine.navigate(url)
            return f"Successfully navigated to {url}"
        except Exception as e:
            return f"Navigation failed: {str(e)}"

    async def _click_with_engine(self, engine, selector: str) -> str:
        """
        Click an element using real browser engine.

        Args:
            engine: Browser engine instance
            selector: CSS selector for the element

        Returns:
            Click result message
        """
        print(f"🖱️  正在点击元素: {selector}")
        try:
            if engine is None or engine._page is None:
                return "Click failed: browser not started. Use navigate_tool first."
            locator = engine.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=engine._config.timeout_ms)
            await locator.click()
            return f"Successfully clicked {selector}"
        except Exception as e:
            return f"Click failed: {str(e)}"

    async def _type_with_engine(self, engine, selector: str, text: str) -> str:
        """
        Type text into an element using real browser engine.

        Args:
            engine: Browser engine instance
            selector: CSS selector for the element
            text: Text to type

        Returns:
            Type result message
        """
        preview = text[:30] + ("..." if len(text) > 30 else "")
        print(f"⌨️  正在输入文本到 {selector}: '{preview}'")
        try:
            if engine is None or engine._page is None:
                return "Type failed: browser not started. Use navigate_tool first."
            locator = engine.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=engine._config.timeout_ms)
            await locator.fill(text)
            return f"Successfully typed '{text}' into {selector}"
        except Exception as e:
            return f"Type failed: {str(e)}"

    async def _verify_with_engine(self, engine, text: str) -> str:
        """
        Verify text is visible using real browser engine.

        Args:
            engine: Browser engine instance
            text: Text to verify

        Returns:
            Verification result message
        """
        preview = text[:30] + ("..." if len(text) > 30 else "")
        print(f"🔍 正在验证文本: '{preview}'")
        try:
            if engine is None or engine._page is None:
                return "Verification failed: browser not started. Use navigate_tool first."
            page_text = await engine.page.inner_text("body")
            if text in page_text:
                return f"Verified: text '{text}' is visible on page"
            return f"Verification failed: text '{text}' not found on page"
        except Exception as e:
            return f"Verification failed: {str(e)}"

    async def _screenshot_with_engine(self, engine, filename: str | None = None) -> str:
        """
        Take a screenshot using real browser engine.

        Args:
            engine: Browser engine instance
            filename: Optional filename for the screenshot

        Returns:
            Screenshot result message
        """
        print(f"📸 正在截图: {filename or 'screenshot.png'}")
        try:
            if engine is None or engine._page is None:
                return "Screenshot failed: browser not started. Use navigate_tool first."
            work_dir = self._work_dir or Path.cwd() / ".aat" / "agent_workspace"
            work_dir.mkdir(parents=True, exist_ok=True)
            screenshot_name = filename or f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            screenshot_path = work_dir / screenshot_name
            screenshot_bytes = await engine.screenshot()
            screenshot_path.write_bytes(screenshot_bytes)
            return f"Screenshot saved to {screenshot_path}"
        except Exception as e:
            return f"Screenshot failed: {str(e)}"

    async def _analyze_with_engine(self, engine, url: str) -> str:
        """
        Analyze a page using real browser engine.

        Args:
            engine: Browser engine instance
            url: URL of the page to analyze

        Returns:
            Analysis result message
        """
        print(f"🔬 正在分析页面: {url}")
        try:
            nav_result = await self._navigate_with_engine(engine, url)
            if "failed" in nav_result.lower():
                return nav_result
            if engine is None or engine._page is None:
                return "Analysis failed: browser not started"
            title = await engine.page.title()
            counts = await engine.page.evaluate(
                """() => ({
                    inputs: document.querySelectorAll('input, textarea, select').length,
                    buttons: document.querySelectorAll('button, [role="button"]').length,
                    links: document.querySelectorAll('a').length,
                })"""
            )
            return (
                f"Page analysis for {url}: title='{title}', "
                f"inputs={counts['inputs']}, buttons={counts['buttons']}, links={counts['links']}"
            )
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

When the user asks to test a website or feature, proactively use browser tools.
Do not say you cannot access the internet — you have a real browser.

Capabilities:
- Navigate web pages and interact with elements
- Analyze page structure and discover functionality
- Execute test plans and verify outcomes
- Take screenshots at key steps
- Report test results clearly

Available tools (call them directly, do not describe what you would do):
- navigate_tool: Open a URL in the browser
- click_tool: Click an element by CSS selector
- type_tool: Fill an input field by CSS selector
- verify_tool: Check expected text on the page
- screenshot_tool: Capture the current page
- analyze_tool: Open a URL and summarize interactive elements

Workflow:
1. Infer the target site from the user request (e.g. Bing search -> https://www.bing.com)
2. Navigate, interact, and verify — use tools immediately
3. Only ask clarifying questions when the target site or expected outcome is ambiguous
4. Report pass/fail with the steps you executed

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
        """Extract text content from a Deep Agent response.

        Handles LangChain message objects (AIMessage, etc.) which have
        a .content attribute, as well as plain dicts.
        """
        # 找到最后一条 AI 消息的内容
        if isinstance(response, dict):
            if "messages" in response:
                messages = response["messages"]
                # 从后往前找最后一条有文本内容的 AI 消息
                for msg in reversed(messages):
                    # LangChain 消息对象（AIMessage 等）
                    if hasattr(msg, "content") and getattr(msg, "content", "").strip():
                        # 跳过只有 tool_calls 没有文本内容的消息
                        return msg.content
                    # 普通 dict 消息
                    elif isinstance(msg, dict) and msg.get("content", "").strip():
                        return msg["content"]
                # 没有文本内容，返回整个响应的字符串
                return str(response)
            elif "content" in response:
                return response["content"]
            return str(response)
        elif hasattr(response, "content"):
            return response.content
        else:
            return str(response)

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._engine and self._engine._page is not None:
            await self._engine.stop()
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
