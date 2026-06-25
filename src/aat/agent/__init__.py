"""
AWT Smart Agent - 基于 DeepAgents 的智能测试代理系统

这个模块将 AWT 从传统的 YAML 测试框架升级为智能测试代理系统。
"""

__version__ = "0.1.0"

# 导出简化版本（立即可用）
from aat.agent.simple_supervisor import SimpleSupervisorAgent, create_simple_supervisor
from aat.agent.config import AgentConfig

# 未来版本：完整 DeepAgents 集成
# from aat.agent.supervisor import AWTSupervisorAgent

__all__ = [
    "SimpleSupervisorAgent",
    "create_simple_supervisor",
    "AgentConfig",
]