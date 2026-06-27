"""
AWT Agent Module - Simplified

Intelligent testing agents without over-engineering.
Clean, simple, practical.
"""

__version__ = "3.1.0"

# Main exports
from aat.agent.config import AgentConfig, AgentContext, AgentMode, TestIntent
from aat.agent.response_utils import (
    AgentPlan,
    Todo,
    clean_response,
    extract_plan,
    extract_response,
    format_plan,
)
from aat.agent.supervisor import AgentSupervisor, ChatResult, create_supervisor

__all__ = [
    # Configuration
    "AgentConfig",
    "AgentContext",
    "TestIntent",
    "AgentMode",
    # Main Supervisor
    "AgentSupervisor",
    "ChatResult",
    "create_supervisor",
    # Task planning
    "AgentPlan",
    "Todo",
    "extract_plan",
    "format_plan",
    # Response helpers
    "clean_response",
    "extract_response",
]
