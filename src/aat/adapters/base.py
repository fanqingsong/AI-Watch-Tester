"""AIAdapter ABC — AI tool integration interface.

ClaudeAdapter, GPTAdapter etc. implement this.
Handles failure analysis, code fix generation, scenario generation, and document analysis.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aat.core.models import AnalysisResult, FixResult, Scenario, TestResult


class AIAdapter(ABC):
    """AI tool integration abstract interface."""

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
