# 浏览器显示模式测试指南

## 🌐 概述

本指南专门针对使用浏览器显示模式执行 SC-001 测试的场景。

## 🎯 测试配置

- **测试服务器**: http://127.0.0.1:8899/
- **测试场景**: SC-001 成功用户登录
- **浏览器模式**: 显示模式 (headless=false)
- **测试凭据**: admin@example.com / changethis

## 🚀 快速开始

### 1. 确保测试服务器运行

```bash
# 验证测试服务器可访问
curl http://127.0.0.1:8899/

# 或在浏览器中打开
# http://127.0.0.1:8899/
```

### 2. 运行浏览器显示测试

```bash
# 完整浏览器测试（推荐）
python examples/agent/test_sc001_browser.py

# 选择模式 1 (完整浏览器测试)
```

### 3. 观察测试过程

浏览器窗口将会自动打开并执行以下步骤：

1. **导航**: 打开 http://127.0.0.1:8899/
2. **输入**: 在邮箱框输入 admin@example.com
3. **输入**: 在密码框输入 changethis
4. **点击**: 点击登录按钮
5. **等待**: 等待页面响应
6. **验证**: 检查 "User" 文本显示

## 📋 测试模式对比

### 1. 完整浏览器测试 (推荐)

```bash
python examples/agent/test_sc001_browser.py
# 选择 1
```

**特点:**
- ✅ 详细的测试步骤
- ✅ 完整的结果分析
- ✅ 错误处理和建议
- ✅ 适合调试和观察

### 2. 快速浏览器测试

```bash
python examples/agent/test_sc001_browser.py
# 选择 2
```

**特点:**
- ⚡ 快速执行
- 📊 基本结果显示
- 🎯 适合快速验证

### 3. 模式对比说明

```bash
python examples/agent/test_sc001_browser.py
# 选择 3
```

**特点:**
- 📚 模式说明
- 💡 使用建议
- 🎯 场景推荐

## 🔧 浏览器模式选项

### Autonomous 模式

```python
result = await supervisor.test_from_natural_language(
    user_request=test_request,
    start_url="http://127.0.0.1:8899/",
    mode="autonomous"  # 自主执行
)
```

**特点:**
- 🤖 自动执行所有步骤
- ⚡ 最快完成测试
- 🎯 适合回归测试

### Interactive 模式 (推荐)

```python
result = await supervisor.test_from_natural_language(
    user_request=test_request,
    start_url="http://127.0.0.1:8899/",
    mode="interactive"  # 关键步骤确认
)
```

**特点:**
- 💬 关键操作前确认
- 👀 方便观察测试过程
- 🔧 适合调试验证

### Conservative 模式

```python
result = await supervisor.test_from_natural_language(
    user_request=test_request,
    start_url="http://127.0.0.1:8899/",
    mode="conservative"  # 每步确认
)
```

**特点:**
- 🛡️ 每步都确认
- 🔒 最安全的测试方式
- 🏢 适合生产环境

## 📊 测试步骤详细说明

### 步骤 1: 创建代理

```python
supervisor = await create_supervisor_from_config()
```

### 步骤 2: 定义测试请求

```python
test_request = """
我需要在真实的浏览器中执行用户登录测试，请启用浏览器显示模式。

测试步骤：
1. 打开浏览器，导航到: http://127.0.0.1:8899/
2. 在页面中找到邮箱输入框，输入: admin@example.com
3. 找到密码输入框，输入: changethis
4. 找到并点击登录按钮（Submit 按钮）
5. 等待页面响应（约 2-3 秒）
6. 验证登录成功，检查页面上是否显示 "User" 文本

重要要求：
- 必须启用浏览器显示模式（headless=false）
- 让我能够看到浏览器操作过程
- 在关键步骤前暂停一下，方便观察
"""
```

### 步骤 3: 执行测试

```python
result = await supervisor.test_from_natural_language(
    user_request=test_request,
    start_url="http://127.0.0.1:8899/",
    mode="interactive"
)
```

### 步骤 4: 查看结果

```python
print(f"测试状态: {'✅ 成功' if result.success else '❌ 失败'}")
print(f"测试摘要: {result.summary}")
```

## 🛠️ 故障排除

### 常见问题

**Q: 浏览器没有打开？**

```bash
# 检查浏览器驱动
# Playwright 应该自动安装浏览器
python -m playwright install chromium

# 手动安装浏览器
python -m playwright install
```

**Q: 测试服务器连接失败？**

```bash
# 验证服务器运行
curl http://127.0.0.1:8899/

# 或在浏览器中访问
# http://127.0.0.1:8899/
```

**Q: 测试步骤执行太快看不清？**

```python
# 使用 interactive 模式
mode="interactive"  # 关键步骤会暂停
```

**Q: 元素定位失败？**

```bash
# 检查页面是否正确加载
# 验证选择器是否正确
# 尝试增加等待时间
```

## 💡 使用技巧

### 技巧 1: 调试时使用截图

```python
test_request = """
执行测试并在每个关键步骤后截图：
1. 导航到登录页并截图
2. 输入凭据并截图
3. 点击登录并截图
4. 验证结果并截图
"""
```

### 技巧 2: 分步观察

```python
# 一步一步测试，方便观察
test_request = """
请分步执行测试，每步执行前：
1. 说明即将执行的操作
2. 等待 1-2 秒让我观察
3. 执行操作
4. 报告操作结果
"""
```

### 技巧 3: 错误分析

```python
test_request = """
如果遇到错误：
1. 截取当前页面状态
2. 分析页面元素
3. 检查控制台错误
4. 提供详细的错误分析
"""
```

## 📈 性能优化

### 加快测试速度

```python
# 减少等待时间
test_request = """
优化执行速度：
- 减少不必要的等待
- 快速执行操作
- 只在关键步骤截图
"""
```

### 提高测试稳定性

```python
# 增加稳定性
test_request = """
提高稳定性：
- 增加元素定位的等待时间
- 在操作前验证元素存在
- 使用重试机制处理失败
"""
```

## 🎓 学习路径

### 1. 观察测试执行

```bash
# 第一次运行，仔细观察
python examples/agent/test_sc001_browser.py
```

### 2. 理解测试流程

```bash
# 查看测试步骤的详细说明
python examples/agent/test_sc001_browser.py
# 选择 3 (模式对比说明)
```

### 3. 自定义测试

修改 `test_request` 变量来自定义测试场景。

### 4. 集成到工作流

将测试集成到开发或 CI/CD 流程中。

## 🔄 与 YAML 对应关系

| YAML 步骤 | 浏览器模式执行 |
|-----------|---------------|
| `navigate: http://127.0.0.1:8899/` | 浏览器打开页面 |
| `find_and_type: admin@example.com` | 可视化输入过程 |
| `find_and_type: changethis` | 可视化输入过程 |
| `find_and_click: Submit` | 可视化点击过程 |
| `wait: 2000` | 实际等待过程 |
| `text_visible: User` | 实际页面验证 |

## 📞 获取帮助

如果遇到问题：

1. 检查服务器连接
2. 验证浏览器安装
3. 查看 AI 配置
4. 参考其他示例文件

## 🎉 开始使用

```bash
# 立即运行浏览器显示测试
python examples/agent/test_sc001_browser.py

# 选择模式 1 开始观察测试过程
```

🌐 享受可视化的 AI 测试体验！