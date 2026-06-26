"""
════════════════════════════════════════════════════════════════════════════════
                       🤖 AI Adapter Base Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Abstract interface for AI tool integration. Defines the contract that all AI
providers (Claude, OpenAI, Gemini, DeepSeek, Ollama, Zhipu) must implement
for failure analysis, code generation, and scenario creation.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.adapters.claude import ClaudeAdapter
from aat.core import AIConfig

config = AIConfig(
    provider="claude",
    api_key="sk-...",
    model="claude-sonnet-4-20250514"
)

adapter = ClaudeAdapter(config)

# Analyze test failure
analysis = await adapter.analyze_failure(test_result)

# Generate code fix
fix = await adapter.generate_fix(analysis, source_files)

# Generate test scenarios
scenarios = await adapter.generate_scenarios(url="https://example.com", spec="test login")
```

⚙️  AI CAPABILITIES
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  Method                 │  Purpose                  │  Use Case                │
├────────────────────────────────────────────────────────────────────────────┤
│  analyze_failure()      │  Diagnose test failures   │  AI debugging loop       │
│  generate_fix()          │  Generate code patches     │  Auto-fix with approval   │
│  generate_scenarios()    │  Create test scenarios    │  Scan → Generate        │
│  analyze_document()      │  Extract requirements     │  Spec → Test cases       │
│  verify_step()           │  Visual step verification  │  AI-powered validation   │
└────────────────────────────────────────────────────────────────────────────┘

🔌 SUPPORTED PROVIDERS
───────────────────────────────────────────────────────────────────────────────
• Claude (Anthropic) — claude-sonnet-4-20250514, claude-haiku-4-5-20251001
• OpenAI — gpt-4o, gpt-4o-mini, gpt-4
• Gemini — gemini-2.0-flash, gemini-2.5-flash
• DeepSeek — deepseek-chat
• Ollama — Local models (free)
• Zhipu — GLM-4

💡 DESIGN PATTERN
───────────────────────────────────────────────────────────────────────────────
Adapter pattern with provider-specific implementations sharing common interface:
```
          AIAdapter (ABC)
                 │
    ┌────────────┼────────────┬────────────┬────────────┐
    │            │            │            │            │
ClaudeAdapter  OpenAIAdapter  GeminiAdapter  OllamaAdapter  DeepSeekAdapter
```

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• Abstract Base Class (ABC) — enforces interface compliance
• Provider-agnostic API — swap AI providers without changing application code
• JSON response parsing — handles markdown fences and format variations
• Vision support — image analysis for screenshot-based failure diagnosis

🔧 ARCHITECTURAL NOTES
───────────────────────────────────────────────────────────────────────────────
• All AI operations are async for non-blocking execution
• JSON response format is standardized across all providers
• Vision capabilities vary by provider (Claude/OpenAI support images)
• Structured Outputs (json_schema) supported only by OpenAI adapter
• Fallback parsing handles YAML, JSON, and markdown-wrapped responses

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aat.core import AnalysisResult, FixResult, Scenario, TestResult


class AIAdapter(ABC):
    """AI tool integration abstract interface."""

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Strip markdown fence markers (```) from AI response text.

        Many LLMs wrap JSON responses in ```json ... ``` or ``` ... ```.
        This helper removes those fences while preserving the content.

        Args:
            text: Raw response text from the AI model.

        Returns:
            Cleaned text with markdown fences removed.
        """
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove all fence lines (lines starting with ```)
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            cleaned = "\n".join(lines)
        return cleaned

    @abstractmethod
    async def analyze_failure(
        self,
        test_result: TestResult,
        screenshots: list[bytes] | None = None,
    ) -> AnalysisResult:
        """Analyze test failure cause.

        Args:
            test_result: Failed test result.
            screenshots: Failure-point screenshots (for Vision API).

        Returns:
            AnalysisResult with cause, suggestion, severity.
        """
        ...

    @abstractmethod
    async def generate_fix(
        self,
        analysis: AnalysisResult,
        source_files: dict[str, str],
    ) -> FixResult:
        """Generate code fix based on analysis.

        Args:
            analysis: Failure analysis result.
            source_files: {file_path: file_content} dict.

        Returns:
            FixResult with description, changed files, confidence.
        """
        ...

    @abstractmethod
    async def generate_scenarios(
        self,
        document_text: str,
        images: list[bytes] | None = None,
        *,
        system_prompt: str | None = None,
    ) -> list[Scenario]:
        """Generate test scenarios from document analysis.

        Args:
            document_text: Spec/design guide text.
            images: Images from the document.
            system_prompt: Optional override for the default system prompt.

        Returns:
            List of generated Scenario objects.
        """
        ...

    async def verify_step(
        self,
        screenshot: bytes,
        step_num: int,
        action: str,
        description: str,
    ) -> tuple[bool, str]:
        """Verify if a step succeeded by visually analyzing its screenshot.

        Args:
            screenshot: PNG bytes of the screen state after the step.
            step_num: Step number for context.
            action: Action type (e.g. "find_and_click").
            description: Step description from the scenario.

        Returns:
            (passed, reason) — bool pass/fail, and a one-line reason.

        Note:
            Default raises NotImplementedError.
            Adapters that support Vision (Claude, OpenAI) should override this.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support verify_step")

    @abstractmethod
    async def analyze_document(
        self,
        document_text: str,
        images: list[bytes] | None = None,
    ) -> dict[str, Any]:
        """Analyze spec document to extract screens/elements/flows.

        Returns:
            dict: {"screens": [...], "elements": [...], "flows": [...]}
        """
        ...
