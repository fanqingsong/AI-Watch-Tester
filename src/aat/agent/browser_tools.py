"""Browser-engine interaction and LangChain tool definitions for the agent."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_WORK_DIR = Path.cwd() / ".aat" / "agent_workspace"


class BrowserToolbox:
    """Wraps a WebEngine and exposes high-level browser operations.

    Each operation returns a human-readable result string so it can be fed
    directly back to the LLM agent as a tool response.
    """

    def __init__(
        self,
        engine: Any,
        work_dir_provider: Callable[[], Path | None] = lambda: None,
    ) -> None:
        self.engine = engine
        self._get_work_dir = work_dir_provider

    # -- engine lifecycle -------------------------------------------------

    async def ensure_started(self) -> None:
        """Start the browser engine if it is not running yet."""
        if self.engine is None:
            return
        if self.engine._page is None:
            await self.engine.start()

    def _started(self) -> bool:
        """True if the engine exists and has a live page."""
        return self.engine is not None and self.engine._page is not None

    def _work_dir(self) -> Path:
        return self._get_work_dir() or DEFAULT_WORK_DIR

    # -- operations -------------------------------------------------------

    async def navigate(self, url: str) -> str:
        """Navigate to a URL using the real browser engine."""
        print(f"🌐 正在导航到: {url}")
        try:
            engine = self.engine
            if engine is None:
                return "Navigation failed: browser engine not available"
            await self.ensure_started()
            await engine.navigate(url)
            return f"Successfully navigated to {url}"
        except Exception as e:
            return f"Navigation failed: {e}"

    async def click(self, selector: str) -> str:
        """Click an element using the real browser engine."""
        print(f"🖱️  正在点击元素: {selector}")
        try:
            if not self._started():
                return "Click failed: browser not started. Use navigate_tool first."
            engine = self.engine
            locator = engine.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=engine._config.timeout_ms)
            await locator.click()
            return f"Successfully clicked {selector}"
        except Exception as e:
            return f"Click failed: {e}"

    async def type_text(self, selector: str, text: str) -> str:
        """Type text into an element using the real browser engine."""
        preview = text[:30] + ("..." if len(text) > 30 else "")
        print(f"⌨️  正在输入文本到 {selector}: '{preview}'")
        try:
            if not self._started():
                return "Type failed: browser not started. Use navigate_tool first."
            engine = self.engine
            locator = engine.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=engine._config.timeout_ms)
            await locator.fill(text)
            return f"Successfully typed '{text}' into {selector}"
        except Exception as e:
            return f"Type failed: {e}"

    async def verify(self, text: str) -> str:
        """Verify text is visible using the real browser engine."""
        preview = text[:30] + ("..." if len(text) > 30 else "")
        print(f"🔍 正在验证文本: '{preview}'")
        try:
            if not self._started():
                return "Verification failed: browser not started. Use navigate_tool first."
            page_text = await self.engine.page.inner_text("body")
            if text in page_text:
                return f"Verified: text '{text}' is visible on page"
            return f"Verification failed: text '{text}' not found on page"
        except Exception as e:
            return f"Verification failed: {e}"

    async def get_text(
        self, selector: str | None = None, max_chars: int = 8000
    ) -> str:
        """Read visible text from the current page.

        Args:
            selector: Optional CSS selector. When given, returns the text of
                the first matching element; otherwise returns the full body.
            max_chars: Truncate the returned text to this many characters to
                keep the tool response within the LLM context budget.
        """
        print("📄 正在读取页面文本")
        try:
            if not self._started():
                return "Get text failed: browser not started. Use navigate_tool first."
            if selector:
                locator = self.engine.page.locator(selector).first
                if await locator.count() == 0:
                    return f"Get text failed: no element matches '{selector}'"
                content = await locator.inner_text()
            else:
                content = await self.engine.page.inner_text("body")
            if len(content) > max_chars:
                content = (
                    content[:max_chars]
                    + f"\n... [truncated, {len(content) - max_chars} more chars]"
                )
            return content
        except Exception as e:
            return f"Get text failed: {e}"

    async def screenshot(self, filename: str | None = None) -> str:
        """Take a screenshot using the real browser engine."""
        print(f"📸 正在截图: {filename or 'screenshot.png'}")
        try:
            if not self._started():
                return "Screenshot failed: browser not started. Use navigate_tool first."
            work_dir = self._work_dir()
            work_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_name = filename or f"screenshot_{ts}.png"
            screenshot_path = work_dir / screenshot_name
            screenshot_bytes = await self.engine.screenshot()
            screenshot_path.write_bytes(screenshot_bytes)
            return f"Screenshot saved to {screenshot_path}"
        except Exception as e:
            return f"Screenshot failed: {e}"

    async def analyze(self, url: str) -> str:
        """Analyze a page using the real browser engine."""
        print(f"🔬 正在分析页面: {url}")
        try:
            nav_result = await self.navigate(url)
            if "failed" in nav_result.lower():
                return nav_result
            if not self._started():
                return "Analysis failed: browser not started"
            title = await self.engine.page.title()
            counts = await self.engine.page.evaluate(
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
            return f"Analysis failed: {e}"


def build_tools(toolbox: BrowserToolbox) -> list[Any]:
    """Create AWT browser tools wired to a BrowserToolbox."""
    from langchain_core.tools import tool

    @tool
    async def navigate_tool(url: str) -> str:
        """Navigate the browser to a URL. Call this first when testing a website."""
        await toolbox.ensure_started()
        return await toolbox.navigate(url)

    @tool
    async def click_tool(selector: str) -> str:
        """Click a page element using a CSS selector (e.g. '#search-icon')."""
        await toolbox.ensure_started()
        return await toolbox.click(selector)

    @tool
    async def type_tool(selector: str, text: str) -> str:
        """Type text into an input field identified by CSS selector."""
        await toolbox.ensure_started()
        return await toolbox.type_text(selector, text)

    @tool
    async def verify_tool(text: str) -> str:
        """Verify that expected text appears on the current page."""
        await toolbox.ensure_started()
        return await toolbox.verify(text)

    @tool
    async def get_text_tool(
        selector: str | None = None, max_chars: int = 8000
    ) -> str:
        """Read the visible text content of the current page.

        Use this to extract page content for analysis, scraping, or reporting
        to the user. Pass a CSS ``selector`` to read a specific element, or
        omit it to read the whole page body. Output is truncated to
        ``max_chars`` (default 8000).
        """
        await toolbox.ensure_started()
        return await toolbox.get_text(selector, max_chars)

    @tool
    async def screenshot_tool(filename: str | None = None) -> str:
        """Capture a screenshot of the current browser page."""
        await toolbox.ensure_started()
        return await toolbox.screenshot(filename)

    @tool
    async def analyze_tool(url: str) -> str:
        """Navigate to a URL and summarize page structure (forms, buttons, links)."""
        await toolbox.ensure_started()
        return await toolbox.analyze(url)

    return [
        navigate_tool,
        click_tool,
        type_tool,
        verify_tool,
        get_text_tool,
        screenshot_tool,
        analyze_tool,
    ]
