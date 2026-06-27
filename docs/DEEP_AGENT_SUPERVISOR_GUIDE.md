# Deep Agent Supervisor 使用指南

## 概述

`DeepAgentSupervisor` 是基于 LangChain Deep Agents 框架实现的 AWT 测试代理。它提供了强大的功能和优秀的可扩展性，是 AWT 的主要测试代理实现。

## 主要优势

### 1. 虚拟文件系统访问
- 内置文件操作工具（`ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`）
- 支持多模态文件读取（图片、视频、音频、PDF）
- 声明式文件系统权限控制

### 2. 自动子代理生成
- 使用内置的 `task` 工具创建子代理处理复杂任务
- 子代理在独立上下文中运行，避免主代理上下文膨胀
- 支持并行任务执行

### 3. 上下文管理
- 自动对话历史压缩和总结
- 大型工具结果自动卸载
- 支持持久化内存（`AGENTS.md` 文件）

### 4. 人在回路（Human-in-the-Loop）
- 关键操作可配置为需要人工批准
- 支持运行时安全控制
- 可中断执行以添加指导

### 5. 增强的工具系统
- 标准化的工具定义接口
- 支持 MCP（Model Context Protocol）服务器
- 自动工具发现和调用

## 安装依赖

Deep Agents 的依赖已包含在项目的 `pyproject.toml` 中：

```toml
# DeepAgent (LangChain)
"deepagents>=0.1.0",
"langchain>=0.3.0",
"langgraph>=0.2.0",
"langchain-core>=0.3.0",
"langchain-anthropic>=0.2.0",
"langchain-openai>=0.2.0",
```

确保这些包已安装：

```bash
pip install -e .
```

## 使用方法

### 命令行使用

使用 `--supervisor deep` 选项启动 Deep Agent 模式：

```bash
# 使用 Deep Agent Supervisor
aat agent chat --supervisor deep

# 使用传统 Unified Supervisor（默认）
aat agent chat --supervisor unified

# 也可以省略 unified 参数
aat agent chat
```

### Python API 使用

#### 1. 基本初始化

```python
import asyncio
from aat.agent import create_deep_agent_supervisor

async def main():
    # 使用默认配置创建 supervisor
    supervisor = await create_deep_agent_supervisor()

    # 进行对话交互
    response = await supervisor.chat("Hello! Can you help me test a website?")
    print(response)

    # 清理资源
    await supervisor.cleanup()

asyncio.run(main())
```

#### 2. 自定义配置

```python
import asyncio
from aat.agent import create_deep_agent_supervisor, AgentConfig

async def main():
    # 创建自定义配置
    config = AgentConfig(
        ai_provider="anthropic",
        ai_model="claude-sonnet-4-6",
        # 更多配置选项...
    )

    # 使用自定义配置创建 supervisor
    supervisor = await create_deep_agent_supervisor(config=config)

    # 执行测试
    result = await supervisor.test_from_natural_language(
        user_request="测试登录功能的用户名密码验证",
        start_url="https://example.com/login",
        mode="interactive"
    )

    print(result)

    await supervisor.cleanup()

asyncio.run(main())
```

#### 3. 页面分析

```python
import asyncio
from aat.agent import create_deep_agent_supervisor

async def main():
    supervisor = await create_deep_agent_supervisor()

    # 分析页面结构
    analysis = await supervisor.analyze_page(
        url="https://example.com",
        depth=2  # 1=快速, 2=详细, 3=全面
    )

    print(f"分析结果: {analysis}")

    await supervisor.cleanup()

asyncio.run(main())
```

## 配置选项

### 文件系统权限

Deep Agent Supervisor 支持细粒度的文件系统访问控制：

```python
permissions = [
    {
        "operations": ["read", "write"],
        "paths": [".aat/agent_workspace/**"],
        "mode": "allow",
    },
    {
        "operations": ["read"],
        "paths": [".aat/**", "tests/**", "scenarios/**"],
        "mode": "allow",
    },
    {
        "operations": ["write"],
        "paths": [".env", "**/credentials.json"],
        "mode": "deny",
    },
]
```

### 人在回路配置

配置哪些工具需要人工批准：

```python
interrupt_on = {
    "write_file": True,      # 文件写入需要批准
    "execute_test_step": False,  # 测试步骤自动批准
    "navigate_to_url": False,    # 导航自动批准
}
```

### 执行模式

支持三种执行模式：

- **interactive** (默认): 平衡独立性和适当的确认
- **autonomous**: 独立执行，无需确认
- **conservative**: 在重要操作前请求确认

## 工具系统

### 内置 AWT 工具

Deep Agent Supervisor 提供以下专门为测试设计的工具：

1. **navigate_to_url**: 导航到指定 URL
2. **click_element**: 点击页面元素
3. **type_text**: 在输入框中输入文本
4. **verify_text_visible**: 验证文本是否可见
5. **take_screenshot**: 截取页面截图
6. **analyze_page_structure**: 分析页面结构
7. **execute_test_step**: 执行自然语言描述的测试步骤

### 使用内置工具

代理会自动决定何时使用哪些工具：

```
用户: 请导航到 example.com 并截图

代理: [自动调用 navigate_to_url 和 take_screenshot 工具]
已导航到 example.com 并保存截图
```

### 自定义工具

您可以添加自定义工具来扩展功能：

```python
def custom_search(query: str) -> str:
    """在数据库中搜索内容"""
    # 实现搜索逻辑
    return f"找到 {len(results)} 个结果"

# 在创建 supervisor 时传入自定义工具
supervisor = await create_deep_agent_supervisor()
# 工具会在初始化时自动注册
```

## 子代理功能

Deep Agent Supervisor 支持自动子代理生成来处理复杂任务。

### 子代理使用场景

1. **并行任务**: 同时分析多个页面
2. **深度分析**: 详细研究特定功能
3. **数据处理**: 处理大型数据集

### 子代理示例

```
用户: 分析这个网站的所有页面并生成测试计划

代理: 我将创建子代理来并行分析不同页面
      [创建多个子代理]
      子代理1: 分析首页
      子代理2: 分析登录页
      子代理3: 分析产品页面
      [汇总所有子代理的结果]
      测试计划已生成...
```

## 工作空间

Deep Agent Supervisor 使用虚拟文件系统进行上下文管理：

### 工作空间位置

默认位置: `.aat/agent_workspace/`

### 工作空间用途

- 存储对话历史和总结
- 保存测试结果和截图
- 持久化代理内存
- 管理临时文件

### 清理工作空间

```bash
# 清理工作空间
rm -rf .aat/agent_workspace/
```

## Deep Agents 核心特性

| 特性 | 功能描述 |
|------|----------|
| 文件系统访问 | 内置虚拟文件系统，支持多种文件操作 |
| 子代理生成 | 自动生成和协调子代理处理复杂任务 |
| 上下文管理 | 高级对话压缩、大型结果卸载、持久化内存 |
| 人在回路 | 支持中断和批准，运行时安全控制 |
| MCP 支持 | 原生支持 Model Context Protocol |
| 工具标准化 | LangChain 标准工具接口 |
| 可扩展性 | 高度可扩展的架构设计 |

## 最佳实践

### 1. 合理设置权限

```python
# 允许工作目录读写
permissions.append({
    "operations": ["read", "write"],
    "paths": [".aat/agent_workspace/**"],
    "mode": "allow",
})

# 拒绝敏感文件写入
permissions.append({
    "operations": ["write"],
    "paths": [".env", "**/credentials.json"],
    "mode": "deny",
})
```

### 3. 利用子代理并行处理

对于复杂任务，让 Deep Agent 自动生成子代理：

```
用户: 测试所有主要功能并生成报告

代理: [自动创建子代理]
      子代理1: 测试登录功能
      子代理2: 测试购物车
      子代理3: 测试结账流程
      [汇总结果]
      测试报告已生成
```

### 4. 使用人在回路控制

对敏感操作启用批准：

```python
interrupt_on = {
    "write_file": True,  # 文件操作需要批准
    "edit_file": True,   # 文件编辑需要批准
}
```

### 5. 定期清理工作空间

```bash
# 定期清理旧的会话数据
find .aat/agent_workspace/ -type f -mtime +7 -delete
```

## 故障排除

### 问题 1: 导入错误

**错误**: `ImportError: Deep Agents dependencies not installed`

**解决方案**:
```bash
pip install deepagents langchain-anthropic
```

### 问题 2: 权限错误

**错误**: `Permission denied: trying to write to protected file`

**解决方案**: 检查文件系统权限配置，确保目标路径在允许列表中。

### 问题 3: 子代理创建失败

**错误**: `Failed to create subagent`

**解决方案**: 确保 LangGraph 依赖已正确安装，检查 API 密钥配置。

### 问题 4: 内存不足

**错误**: `Token limit exceeded`

**解决方案**: Deep Agent 会自动压缩历史，但你可以：
- 使用更高的 token 限制模型
- 减少上下文窗口大小
- 定期清理不需要的文件

## 参考资料

- [LangChain Deep Agents 文档](https://docs.langchain.com/deepagents)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [MCP 协议](https://modelcontextprotocol.io/)
- [项目 README](../../README.md)

## 示例项目

查看 `examples/` 目录中的完整示例：

- `basic_chat.py`: 基本对话示例
- `test_execution.py`: 测试执行示例
- `page_analysis.py`: 页面分析示例
- `custom_tools.py`: 自定义工具示例

## 贡献

欢迎提交 Issue 和 Pull Request 来改进 Deep Agent Supervisor！

## 许可证

本项目采用 AGPL-3.0 许可证。参见 LICENSE 文件详情。
