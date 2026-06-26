# AWT DeepAgent Migration Guide

## 概述

本文档描述了 AWT (AI Watch Tester) 项目如何迁移到官方的 LangChain DeepAgents 框架。这次迁移为项目带来了更强大的代理能力和更好的集成性。

## 迁移状态

✅ **已完成** - 项目已成功迁移到官方 DeepAgents 框架

## 主要变化

### 1. 核心架构变化

#### 之前（自定义实现）
```python
from aat.agent import SimpleSupervisorAgent, create_simple_supervisor

# 使用自定义的代理实现
supervisor = await create_simple_supervisor()
result = await supervisor.test_from_natural_language(
    user_request="测试登录功能",
    start_url="https://example.com/login",
    mode="interactive"
)
```

#### 现在（DeepAgent 框架）
```python
from aat.agent import DeepAgentSupervisor, create_supervisor_from_config

# 使用官方 DeepAgents 框架
supervisor = await create_supervisor_from_config()
result = await supervisor.test_from_natural_language(
    user_request="测试登录功能",
    start_url="https://example.com/login",
    mode="interactive"
)
```

### 2. 依赖包变化

#### 新增依赖
- `deepagents>=0.1.0` - 官方 DeepAgents SDK
- `langchain>=0.3.0` - LangChain 核心库
- `langgraph>=0.2.0` - LangGraph 运行时
- `langchain-core>=0.3.0` - LangChain 核心组件
- `langchain-anthropic>=0.2.0` - Anthropic 集成
- `langchain-openai>=0.2.0` - OpenAI 集成

#### 安装命令
```bash
# 在虚拟环境中安装新的依赖
pip install deepagents langchain langgraph langchain-core langchain-anthropic langchain-openai

# 或者重新安装整个项目
pip install -e .
```

### 3. API 变化

#### 新的 API

**DeepAgentSupervisor 类**
- 基于官方 `create_deep_agent()` 实现
- 支持原生工具调用和子代理系统
- 内置上下文管理和压缩
- 支持人机交互中断机制

**DeepAgentTestResult 类**
- 标准化的测试结果结构
- 包含详细的执行信息和原始结果
- 支持多种结果格式输出

**工具系统**
- 所有工具遵循 DeepAgents 工具规范
- 标准化的参数签名和文档
- 丰富的错误处理和状态反馈

#### 向后兼容

旧的 `SimpleSupervisorAgent` 仍然可用，确保向后兼容性：

```python
# 旧的API仍然可用
from aat.agent import SimpleSupervisorAgent, create_simple_supervisor

supervisor = await create_simple_supervisor()
result = await supervisor.test_from_natural_language(...)
```

## DeepAgents 框架优势

### 1. 原生工具调用系统
- **自动工具发现**: DeepAgents 自动识别和注册工具
- **智能工具选择**: 基于上下文自动选择合适的工具
- **并行工具执行**: 支持多个工具并行调用
- **错误处理**: 内置的工具错误处理和重试机制

### 2. 子代理系统
- **任务委托**: 主代理可以创建专门的子代理处理特定任务
- **隔离上下文**: 每个子代理拥有独立的上下文窗口
- **并行执行**: 多个子代理可以并行工作
- **结果聚合**: 自动聚合子代理的执行结果

### 3. 上下文管理
- **自动压缩**: 超长对话历史自动压缩总结
- **提示缓存**: 静态提示内容自动缓存，降低成本
- **渐进式加载**: 按需加载详细内容，节省上下文
- **长期记忆**: 跨会话的持久化记忆能力

### 4. 人机交互
- **中断机制**: 关键操作前可以暂停请求人工确认
- **多级交互**: 支持不同级别的交互模式
- **反馈学习**: 从用户反馈中学习优化策略
- **安全控制**: 细粒度的操作权限控制

### 5. 文件系统支持
- **虚拟文件系统**: 内置的虚拟文件系统支持
- **权限控制**: 声明式的文件访问权限控制
- **多后端支持**: 支持内存、磁盘、数据库等多种后端
- **沙盒执行**: 可选的沙盒环境执行

## 迁移指南

### 对于现有用户

#### 最小变化迁移
如果你已经在使用 AWT Smart Agent，迁移到 DeepAgent 版本只需要很少的代码更改：

```python
# 之前的代码
from aat.agent import create_simple_supervisor

supervisor = await create_simple_supervisor()
result = await supervisor.test_from_natural_language(...)

# 迁移后的代码（只需更改导入）
from aat.agent import create_supervisor_from_config

supervisor = await create_supervisor_from_config()
result = await supervisor.test_from_natural_language(...)
```

#### 利用新功能
要充分利用 DeepAgents 的新功能，可以：

```python
from aat.agent import DeepAgentSupervisor, AgentConfig

# 创建自定义配置
config = AgentConfig(
    ai_model="anthropic:claude-sonnet-4-6",
    default_mode="autonomous",
    max_exploration_depth=5,
    enable_context_compression=True,
)

supervisor = DeepAgentSupervisor(config)
await supervisor.initialize()

# 使用更强大的功能
result = await supervisor.test_from_natural_language(...)
```

### 对于开发者

#### 创建自定义工具

遵循 DeepAgents 工具规范创建自定义工具：

```python
from langchain_core.tools import tool

@tool
async def my_custom_tool(param1: str, param2: int = 10) -> dict[str, Any]:
    """
    工具描述（DeepAgents 会自动解析）
    
    Args:
        param1: 参数1描述
        param2: 参数2描述（默认值）
        
    Returns:
        返回值描述
    """
    # 工具实现
    return {"success": True, "result": "..."}
```

#### 创建子代理配置

```python
from aat.agent.subagents import get_subagent_configs

# 添加自定义子代理配置
def get_my_custom_agent_config() -> dict[str, Any]:
    return {
        "name": "my_custom_agent",
        "description": "我的自定义代理",
        "system_prompt": "你是...",
        "tools": ["tool1", "tool2"],
        "model": "anthropic:claude-sonnet-4-6",
    }
```

## 配置和部署

### 环境配置

DeepAgent 使用与 AWT 相同的配置文件，无需额外配置：

```yaml
# aat.config.yaml
ai:
  provider: "zhipuai"  # 或 "anthropic", "openai"
  model: "glm-4-flash"
  api_key: "your-api-key"
  temperature: 0.3

engine:
  timeout_ms: 30000

max_loops: 3
```

### 模式选择

DeepAgent 支持多种运行模式：

- **interactive**: 交互式模式，重要操作前确认
- **autonomous**: 自主模式，自动处理常见问题
- **conservative**: 保守模式，所有操作都确认
- **aggressive**: 激进模式，大胆探索边界情况

```python
result = await supervisor.test_from_natural_language(
    user_request="测试登录功能",
    start_url="https://example.com/login",
    mode="autonomous"  # 选择合适的模式
)
```

## 性能和成本优化

### 提示缓存
DeepAgent 自动对静态提示内容进行缓存，减少重复处理成本：

```python
# 自动缓存系统提示、内存内容和技能内容
# 对于 Anthropic 和 Bedrock 模型自动启用
```

### 上下文压缩
长对话历史自动压缩总结，保持在 token 限制内：

```python
config = AgentConfig(
    enable_context_compression=True,  # 启用上下文压缩
    max_context_tokens=100000,        # 最大上下文 token 数
)
```

### 并行执行
支持工具和子代理的并行执行，提高效率：

```python
# DeepAgent 自动识别可并行的操作
# 无需手动配置，自动优化执行顺序
```

## 测试和验证

### 运行测试

```bash
# 运行 DeepAgent 相关测试
python -m pytest tests/agent/ -v

# 运行示例程序
python examples/agent/deepagent_example.py
```

### 验证安装

```python
# 验证 DeepAgent 安装
from deepagents import create_deep_agent
print("DeepAgent 安装成功！")

# 验证 AWT 集成
from aat.agent import create_supervisor_from_config
supervisor = await create_supervisor_from_config()
print("AWT DeepAgent 集成成功！")
```

## 故障排除

### 常见问题

#### 1. 导入错误
**问题**: `ImportError: cannot import name 'create_deep_agent'`
**解决**: 确保安装了正确的依赖：
```bash
pip install deepagents>=0.1.0
```

#### 2. AI 提供商连接失败
**问题**: AI 模型连接失败
**解决**: 检查 API 密钥配置和网络连接：
```python
from aat.core.config import load_config
config = load_config()
print(f"AI Provider: {config.ai.provider}")
print(f"API Key: {config.ai.api_key[:10]}...")  # 只显示前10个字符
```

#### 3. 工具调用失败
**问题**: DeepAgent 无法调用工具
**解决**: 确保工具遵循正确的格式：
```python
from langchain_core.tools import tool

@tool
async def my_tool(param: str) -> dict[str, Any]:
    """工具描述"""
    return {"success": True, "result": "..."}
```

## 未来计划

### 即将推出的功能

1. **完整 WebEngine 集成**: 将实际的浏览器操作集成到工具中
2. **高级子代理系统**: 实现专门的测试、分析、安全子代理
3. **学习和记忆**: 基于历史测试结果的智能学习系统
4. **可视化和报告**: 丰富的测试结果可视化和报告生成
5. **MCP 服务器集成**: 支持模型上下文协议服务器

### 贡献指南

欢迎贡献代码和想法！请参阅项目的 `CONTRIBUTING.md` 文件。

## 相关资源

- [LangChain DeepAgents 官方文档](https://docs.langchain.com/deepagents)
- [AWT 项目文档](README.md)
- [示例代码](examples/agent/)
- [测试用例](tests/agent/)

## 支持

如有问题或建议，请：
- 提交 GitHub Issue
- 加入项目讨论区
- 查阅文档和示例

---

**迁移完成日期**: 2026-06-26
**版本**: 1.0.0
**状态**: ✅ 生产就绪