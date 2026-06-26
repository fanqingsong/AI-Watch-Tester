"""
AWT Agent Module - Simplified

Intelligent testing agents without over-engineering.
Clean, simple, practical.
"""

__version__ = "3.0.0"

# Main exports
from aat.agent.config import AgentConfig, AgentContext, AgentMode, TestIntent
from aat.agent.supervisor import AgentSupervisor, create_supervisor

__all__ = [
    # Configuration
    "AgentConfig",
    "AgentContext",
    "TestIntent",
    "AgentMode",
    # Main Supervisor
    "AgentSupervisor",
    "create_supervisor",
]
