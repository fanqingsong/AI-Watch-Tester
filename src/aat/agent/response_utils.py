"""Helpers for extracting and cleaning text from Deep Agent / LangChain responses."""

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

TodoStatus = Literal["pending", "in_progress", "completed"]


class Todo(BaseModel):
    """A single task-planning item tracked by the agent via ``write_todos``."""

    content: str
    status: TodoStatus = "pending"

    model_config = ConfigDict(extra="allow")


class AgentPlan(BaseModel):
    """Structured task plan extracted from a Deep Agent response.

    Mirrors the ``todos`` state field maintained by the harness's
    ``TodoListMiddleware``. Empty when the agent did not plan.
    """

    todos: list[Todo] = []

    model_config = ConfigDict(extra="allow")

    @property
    def is_empty(self) -> bool:
        """True when no todos were produced (the agent did not plan)."""
        return not self.todos

    @property
    def is_complete(self) -> bool:
        """True when every todo is marked ``completed``."""
        return bool(self.todos) and all(t.status == "completed" for t in self.todos)

    def summary(self) -> str:
        """Render a compact human-readable progress summary (e.g. ``2/5``)."""
        if not self.todos:
            return "0/0"
        done = sum(1 for t in self.todos if t.status == "completed")
        return f"{done}/{len(self.todos)}"


def extract_response(response: Any) -> str:
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


def extract_plan(response: Any) -> AgentPlan:
    """Extract the todo plan from a Deep Agent response.

    The harness stores the current plan under the ``todos`` key of the
    agent state (a list of ``{"content": str, "status": str}`` dicts).
    Returns an empty :class:`AgentPlan` when no plan exists.
    """
    todos_raw: Any = None
    if isinstance(response, dict):
        todos_raw = response.get("todos")
    elif hasattr(response, "todos"):
        todos_raw = getattr(response, "todos", None)

    if not todos_raw:
        return AgentPlan()

    todos: list[Todo] = []
    if isinstance(todos_raw, list):
        for item in todos_raw:
            content: str | None = None
            raw_status: Any = "pending"
            if isinstance(item, dict):
                content = item.get("content") or item.get("description")
                raw_status = item.get("status", "pending")
            elif hasattr(item, "content"):
                content = getattr(item, "content", None)
                raw_status = getattr(item, "status", "pending")
            else:
                content = str(item) if item else None

            if not content:
                continue
            if raw_status not in ("pending", "in_progress", "completed"):
                raw_status = "pending"
            todos.append(Todo(content=content, status=raw_status))  # type: ignore[arg-type]
    return AgentPlan(todos=todos)


# Pre-compiled patterns for ``clean_response`` — avoids recompiling per call.
_FENCE_RE = re.compile(r"```(?:json|yaml|markdown|python|bash|sh)?\s*")
_FENCE_CLOSE_RE = re.compile(r"```")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def clean_response(response: str) -> str:
    """Clean an agent response for display.

    Strips markdown code fences, collapses excessive blank lines, and trims
    per-line whitespace. Returns the input unchanged if it is empty.
    """
    if not response:
        return response

    # 去除 markdown 代码块标记 (```json / ```yaml / ``` 等)
    response = _FENCE_RE.sub("", response)
    response = _FENCE_CLOSE_RE.sub("", response)

    # 去除过多的换行
    response = _BLANK_LINES_RE.sub("\n\n", response)

    # 去除行首行尾的空格
    lines = [line.strip() for line in response.split("\n")]
    response = "\n".join(lines)

    return response.strip()


def format_plan(plan: AgentPlan) -> str:
    """Render an :class:`AgentPlan` as a multi-line checklist string.

    Returns an empty string when the plan is empty so callers can treat the
    result as "nothing to display".
    """
    if plan.is_empty:
        return ""
    lines = [f"📋 Plan ({plan.summary()}):"]
    for todo in plan.todos:
        mark = {"completed": "✅", "in_progress": "🔄", "pending": "⬜"}[todo.status]
        lines.append(f"  {mark} {todo.content}")
    return "\n".join(lines)
