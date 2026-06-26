"""
AWT Smart Agent - 基于官方 LangChain DeepAgents 的智能测试代理系统

这个模块将 AWT 从传统的 YAML 测试框架升级为智能测试代理系统。
现在完全基于官方的 DeepAgents 框架实现。
"""

__version__ = "1.0.0"

# 导出 DeepAgent 版本（推荐）
from aat.agent.config import AgentConfig
from aat.agent.deepagent_supervisor import (
    DeepAgentSupervisor,
    DeepAgentTestResult,
    create_deepagent_supervisor,
    create_supervisor_from_config,
)

# 导出简化版本（向后兼容，可选）
from aat.agent.simple_supervisor import (
    SimpleSupervisorAgent,
    create_simple_supervisor,
)

# 导出 DeepAgent 工具
from aat.agent.deepagent_tools import (
    get_awt_deepagent_tools,
    get_navigation_tools,
    get_interaction_tools,
    get_verification_tools,
    get_analysis_tools,
    get_tools_by_category,
)

__all__ = [
    # 主要：DeepAgent 版本（推荐使用）
    "DeepAgentSupervisor",
    "DeepAgentTestResult",
    "create_deepagent_supervisor",
    "create_supervisor_from_config",
    "AgentConfig",
    # 工具系统
    "get_awt_deepagent_tools",
    "get_navigation_tools",
    "get_interaction_tools",
    "get_verification_tools",
    "get_analysis_tools",
    "get_tools_by_category",
    # 向后兼容：简化版本（可选）
    "SimpleSupervisorAgent",
    "create_simple_supervisor",
]
