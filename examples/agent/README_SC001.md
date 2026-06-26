# SC-001 用户登录场景 DeepAgent 测试指南

## 概述

本指南展示了如何使用 AWT DeepAgent 框架执行 SC-001 (成功用户登录) 测试场景，该场景原本定义为 YAML 配置文件 `SC-001_successful_user_login.yaml`。

## 测试脚本说明

### 1. **test_sc_001_login.py** - 完整交互式测试

这是一个功能完整的测试脚本，提供多种运行模式和详细的分析对比。

#### 功能特点

- ✅ **多种运行模式**: 自主、交互、保守模式
- ✅ **详细对比分析**: YAML vs DeepAgent 方式对比
- ✅ **完整测试流程**: 从创建到结果分析
- ✅ **用户交互**: 可选择测试模式和选项
- ✅ **详细报告**: 生成完整的测试报告和对比

#### 使用方法

```bash
# 运行交互式测试
python examples/agent/test_sc_001_login.py
```

#### 运行模式选择

1. **自主模式 (推荐)**: AI 自动执行测试，无需人工确认
2. **交互模式**: 关键操作前请求用户确认
3. **保守模式**: 每个步骤都请求用户确认
4. **运行所有模式**: 依次运行所有模式进行对比

#### 输出示例

```
🚀 AWT DeepAgent 测试 - SC-001: 成功用户登录
============================================================
对应场景文件: SC-001_successful_user_login.yaml
============================================================
✅ DeepAgent 主管代理创建成功

📝 测试请求:
------------------------------------------------------------
测试 SC-001: 成功用户登录
请按以下步骤执行测试...
...
```

### 2. **test_sc_001_auto.py** - 自动化测试脚本

这是一个简化的自动化测试脚本，适合用于 CI/CD 或批量测试。

#### 功能特点

- ✅ **完全自动化**: 无需用户交互
- ✅ **快速执行**: 直接运行测试
- ✅ **适合集成**: 可集成到 CI/CD 流程
- ✅ **退出码**: 提供标准的退出码用于脚本判断

#### 使用方法

```bash
# 运行自动化测试
python examples/agent/test_sc_001_auto.py

# 在 CI/CD 中使用
python examples/agent/test_sc_001_auto.py && echo "测试通过" || echo "测试失败"
```

#### 退出码含义

- `0`: 测试成功
- `1`: 测试失败
- `2`: 执行出错

## 测试场景对比

### YAML 方式 (传统)

```yaml
steps:
  - step: 1
    action: navigate
    value: http://localhost:5173/
    description: Open login page
    
  - step: 2
    action: find_and_type
    target:
      text: Email/Account
      selector: '[ref=e11]'
    value: admin@example.com
    description: Enter valid email
    
  - step: 3
    action: find_and_type
    target:
      text: Password
      selector: '[ref=e14]'
    value: changethis
    description: Enter valid password
    
  - step: 4
    action: find_and_click
    target:
      text: Submit
      selector: '[ref=e21]'
    description: Click submit button
    
  - step: 5
    action: wait
    value: '2000'
    description: Wait for navigation

expected_result:
  - type: text_visible
    value: User
```

### DeepAgent 方式 (新)

```python
test_request = """
测试 SC-001: 成功用户登录

请按以下步骤执行测试：
1. 导航到登录页面 http://localhost:5173/
2. 在邮箱输入框输入: admin@example.com
3. 在密码输入框输入: changethis
4. 点击提交按钮 (Submit)
5. 等待 2 秒让页面导航
6. 验证页面显示 "User" 文本，确认登录成功

测试目标：
- 验证用户认证流程正常工作
- 确认登录后正确重定向到仪表板
"""

result = await supervisor.test_from_natural_language(
    user_request=test_request,
    start_url="http://localhost:5173/",
    mode="autonomous"
)
```

## 核心优势对比

| 维度 | YAML 方式 | DeepAgent 方式 |
|------|-----------|----------------|
| **配置方式** | YAML 文件 | 自然语言描述 |
| **可读性** | 需要理解 YAML 语法 | 直观的中文描述 |
| **灵活性** | 需要修改 YAML 结构 | 直接修改描述文本 |
| **智能性** | 机械执行步骤 | 理解意图，智能执行 |
| **错误处理** | 需要预定义错误处理 | 自动分析和修复 |
| **适应性** | 固定步骤 | 根据实际情况调整 |
| **维护性** | 需要手动更新 | 自然语言容易理解 |
| **学习曲线** | 需要学习 YAML 格式 | 无需特殊培训 |

## DeepAgent 的核心优势

### 1. 🎯 自然语言
用日常语言描述测试意图，无需学习专门的配置语法

### 2. 🤖 智能理解
AI 自动理解测试目标和策略，选择最佳执行方式

### 3. 🔧 自动工具选择
根据具体测试需求自动选择最合适的工具和方法

### 4. 🛠️ 智能错误处理
自动分析失败原因，尝试修复，提供详细建议

### 5. 📊 详细报告
生成人类可读的详细测试报告，便于理解和分析

### 6. 🔄 持续学习
从历史测试中学习，不断改进测试策略

## 运行环境要求

### 前置条件

1. **Python 环境**: Python 3.11+
2. **依赖安装**: 
   ```bash
   pip install -e .
   ```
3. **测试服务器**: 确保测试目标服务器可访问
   - 本地测试: `http://localhost:5173/`
   - 或修改脚本中的 URL

### AI 配置

确保 `aat.config.yaml` 中配置了有效的 AI 提供商:

```yaml
ai:
  provider: "zhipuai"  # 或 "anthropic", "openai"
  model: "glm-4-flash"
  api_key: "your-api-key"
```

## 使用场景

### 1. 开发测试

```bash
# 开发过程中快速验证
python examples/agent/test_sc_001_auto.py
```

### 2. CI/CD 集成

```bash
# 在 CI 流水线中
- name: Run SC-001 Test
  run: python examples/agent/test_sc_001_auto.py
```

### 3. 回归测试

```bash
# 定期执行回归测试
python examples/agent/test_sc_001_login.py
# 选择模式 1 (自主模式)
```

### 4. 探索性测试

```bash
# 尝试不同的测试策略
python examples/agent/test_sc_001_login.py
# 选择模式 4 (运行所有模式)
```

## 故障排除

### 常见问题

**Q: 测试连接失败？**
```bash
# 检查测试服务器是否可访问
curl http://localhost:5173/

# 或修改脚本中的 URL
```

**Q: AI 调用失败？**
```bash
# 检查 AI 配置
cat aat.config.yaml

# 验证 API 密钥
python -c "from aat.core.config import load_config; print(load_config().ai.api_key[:10] + '...')"
```

**Q: 工具调用失败？**
```bash
# 验证工具加载
python -c "from aat.agent import get_awt_deepagent_tools; print(len(get_awt_deepagent_tools()))"
# 应该输出: 15
```

## 进阶使用

### 自定义测试场景

修改 `test_request` 变量来创建自定义测试:

```python
test_request = """
测试自定义场景：
[你的测试需求描述]
"""

result = await supervisor.test_from_natural_language(
    user_request=test_request,
    start_url="http://your-target-url/",
    mode="autonomous"
)
```

### 批量测试

创建批量测试脚本:

```python
scenarios = [
    ("SC-001", "测试用户登录功能"),
    ("SC-002", "测试用户注册功能"),
    ("SC-003", "测试密码重置功能"),
]

for scenario_id, description in scenarios:
    print(f"运行 {scenario_id}: {description}")
    result = await supervisor.test_from_natural_language(
        user_request=description,
        start_url="http://localhost:5173/",
        mode="autonomous"
    )
    print(f"结果: {'✅ 成功' if result.success else '❌ 失败'}")
```

## 总结

通过 DeepAgent 框架，我们可以用自然语言替代传统的 YAML 配置方式，使测试更加直观、灵活和智能。两个测试脚本展示了从简单自动化到完整交互式的不同使用场景，满足不同的测试需求。

**推荐使用方式:**
- 日常开发: `test_sc_001_auto.py` (快速验证)
- 完整测试: `test_sc_001_login.py` (详细分析)
- CI/CD: `test_sc_001_auto.py` (自动化集成)

🎉 开始享受更智能的测试方式吧！