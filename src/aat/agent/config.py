"""
AWT Agent 配置系统
"""

from enum import Enum

from pydantic import BaseModel, Field


class AgentMode(str, Enum):
    """代理运行模式"""

    INTERACTIVE = "interactive"  # 交互式模式，需要用户确认
    AUTONOMOUS = "autonomous"  # 自主模式，代理独立决策
    CONSERVATIVE = "conservative"  # 保守模式，多询问用户
    AGGRESSIVE = "aggressive"  # 激进模式，大胆尝试


class StrategyLevel(str, Enum):
    """策略级别"""

    SAFE = "safe"  # 安全优先
    BALANCED = "balanced"  # 平衡策略
    FAST = "fast"  # 快速测试


class AgentConfig(BaseModel):
    """代理配置"""

    # AI 模型配置
    ai_model: str = Field(default="anthropic:claude-sonnet-4-6", description="主要使用的 AI 模型")
    backup_model: str | None = Field(default=None, description="备用 AI 模型")

    # 代理行为配置
    default_mode: AgentMode = Field(default=AgentMode.INTERACTIVE, description="默认运行模式")
    strategy_level: StrategyLevel = Field(default=StrategyLevel.BALANCED, description="策略级别")

    # 探索配置
    max_exploration_depth: int = Field(default=3, description="最大探索深度（页面跳转层级）")
    exploration_timeout: int = Field(default=30000, description="单页面探索超时时间（毫秒）")

    # 测试配置
    test_execution_timeout: int = Field(default=60000, description="测试执行超时时间（毫秒）")
    max_retry_attempts: int = Field(default=3, description="最大重试次数")

    # 记忆和学习配置
    enable_exploration_memory: bool = Field(default=True, description="是否启用探索记忆")
    enable_user_learning: bool = Field(default=True, description="是否启用用户偏好学习")

    # 上下文管理配置
    max_context_tokens: int = Field(default=100000, description="最大上下文 token 数")
    enable_context_compression: bool = Field(default=True, description="是否启用上下文压缩")

    # 沙盒配置
    enable_sandbox: bool = Field(default=True, description="是否启用沙盒隔离")
    sandbox_timeout: int = Field(default=120000, description="沙盒执行超时时间（毫秒）")

    # 用户交互配置
    enable_human_feedback: bool = Field(default=True, description="是否启用人机交互反馈")
    feedback_frequency: str = Field(
        default="on_failure", description="反馈频率：always | on_failure | on_milestone"
    )

    class Config:
        """Pydantic 配置"""

        use_enum_values = True
        extra = "allow"


class TestIntent(BaseModel):
    """测试意图"""

    test_type: str = Field(
        description="测试类型：functional | regression | exploratory | security"
    )
    target_features: list[str] = Field(default_factory=list, description="目标功能列表")
    success_criteria: list[str] = Field(default_factory=list, description="成功标准")
    risk_level: str = Field(default="medium", description="风险级别：low | medium | high")
    priority_areas: list[str] = Field(default_factory=list, description="优先测试的区域")
    constraints: list[str] = Field(default_factory=list, description="约束条件")

    class Config:
        """Pydantic 配置"""

        extra = "allow"


class AgentContext(BaseModel):
    """代理上下文"""

    current_url: str
    user_request: str
    test_intent: TestIntent
    exploration_history: list[dict] = Field(default_factory=list)
    test_results: list[dict] = Field(default_factory=list)
    user_feedback: list[dict] = Field(default_factory=list)

    class Config:
        """Pydantic 配置"""

        extra = "allow"
