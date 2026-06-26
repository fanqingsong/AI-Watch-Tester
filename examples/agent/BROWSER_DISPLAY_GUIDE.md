# 浏览器显示模式使用指南

## 🌐 概述

所有 AWT DeepAgent 测试脚本现在都支持浏览器显示模式，让你可以实时观察测试执行过程。

## 🚀 快速开始

### 方法 1: 使用统一启动器（推荐）

```bash
# 启动浏览器显示模式测试
python examples/agent/browser_launcher.py

# 指定测试类型和服务器
python examples/agent/browser_launcher.py --test auto --url http://127.0.0.1:8899/

# 查看所有可用测试
python examples/agent/browser_launcher.py --list
```

### 方法 2: 直接修改测试脚本参数

每个测试脚本现在都支持浏览器显示参数：

```python
# 原来的调用方式
result = await supervisor.test_from_natural_language(
    user_request=test_request,
    start_url="http://localhost:5173/",
    mode="autonomous"
)

# 新的调用方式（启用浏览器显示）
result = await supervisor.test_from_natural_language(
    user_request=test_request,
    start_url="http://127.0.0.1:8899/",  # 使用你的测试服务器
    mode="autonomous"
)
```

## 📋 支持的测试脚本

### 1. **test_sc_001_auto.py** - 自动化测试

```bash
# 修改代码中的参数
browser_display=True
test_url="http://127.0.0.1:8899/"

# 或使用统一启动器
python browser_launcher.py --test auto --url http://127.0.0.1:8899/
```

### 2. **test_sc_001_login.py** - 完整登录测试

```bash
# 修改代码中的参数
browser_display=True
test_url="http://127.0.0.1:8899/"

# 或使用统一启动器
python browser_launcher.py --test login --url http://127.0.0.1:8899/
```

### 3. **quickstart_sc001.py** - 快速开始测试

```bash
# 修改代码中的参数
browser_display=True
test_url="http://127.0.0.1:8899/"

# 或使用统一启动器
python browser_launcher.py --test quickstart --url http://127.0.0.1:8899/
```

### 4. **deepagent_example.py** - 综合示例

```bash
# 修改代码中的参数
browser_display=True
test_url="http://127.0.0.1:8899/"

# 或使用统一启动器
python browser_launcher.py --test basic --url http://127.0.0.1:8899/
```

### 5. **test_sc001_browser.py** - 专用浏览器测试

```bash
# 这个脚本专门为浏览器显示模式设计
python examples/agent/test_sc001_browser.py

# 选择模式 1 (完整浏览器测试)
```

## 🔧 代码修改示例

### 示例 1: 修改 test_sc_001_auto.py

```python
# 原来的代码
async def run_sc_001_test_auto():
    # ...
    result = await supervisor.test_from_natural_language(
        user_request=test_request,
        start_url="http://localhost:5173/",
        mode="autonomous"
    )

# 修改后的代码
async def run_sc_001_test_auto(browser_display=True, test_url="http://127.0.0.1:8899/"):
    # ...
    result = await supervisor.test_from_natural_language(
        user_request=test_request,
        start_url=test_url,
        mode="autonomous"
    )
```

### 示例 2: 修改 quickstart_sc001.py

```python
# 原来的代码
async def quick_start():
    # ...
    result = await supervisor.test_from_natural_language(
        user_request=test_request,
        start_url="http://localhost:5173/",
        mode="autonomous"
    )

# 修改后的代码
async def quick_start(browser_display=True, test_url="http://127.0.0.1:8899/"):
    # ...
    result = await supervisor.test_from_natural_language(
        user_request=test_request,
        start_url=test_url,
        mode="autonomous"
    )
```

## 💡 使用技巧

### 技巧 1: 在测试请求中明确要求浏览器显示

```python
test_request = """
测试用户登录功能：

重要要求：
- 必须启用浏览器显示模式（headless=false）
- 让我能够看到浏览器操作过程
- 在关键步骤前暂停，方便观察

测试步骤：
1. 打开页面
2. 输入凭据
3. 点击登录
4. 验证结果
"""
```

### 技巧 2: 选择合适的运行模式

- **autonomous**: 快速执行，适合观察完整流程
- **interactive**: 关键步骤确认，适合调试
- **conservative**: 每步确认，最安全

### 技巧 3: 使用正确的测试服务器地址

```bash
# 开发环境
--url http://127.0.0.1:8899/

# 本地测试环境
--url http://localhost:5173/

# 生产环境（谨慎使用）
--url https://your-production-site.com/
```

## 🎯 测试场景示例

### 场景 1: 快速验证

```bash
# 使用快速开始测试
python browser_launcher.py --test quickstart --url http://127.0.0.1:8899/
```

### 场景 2: 完整测试流程

```bash
# 使用完整登录测试
python browser_launcher.py --test login --url http://127.0.0.1:8899/
```

### 场景 3: 自动化回归测试

```bash
# 使用自动化测试
python browser_launcher.py --test auto --url http://127.0.0.1:8899/
```

## 🛠️ 故障排除

### 常见问题

**Q: 浏览器没有打开？**
```bash
# 检查浏览器驱动安装
python -m playwright install chromium

# 验证环境
python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"
```

**Q: 测试服务器连接失败？**
```bash
# 验证服务器可访问
curl http://127.0.0.1:8899/

# 或在浏览器中打开
# http://127.0.0.1:8899/
```

**Q: 测试执行太快看不清？**
```python
# 使用 interactive 模式
mode="interactive"  # 关键步骤会暂停
```

**Q: 元素定位失败？**
```bash
# 检查页面是否正确加载
# 验证URL是否正确
# 增加等待时间
```

## 📊 不同模式的对比

| 测试脚本 | 浏览器支持 | 主要用途 | 推荐场景 |
|---------|-----------|----------|----------|
| test_sc001_browser.py | ✅ 专用 | 浏览器显示测试 | 调试观察 |
| test_sc_001_auto.py | ✅ 支持 | 自动化测试 | CI/CD 集成 |
| test_sc_001_login.py | ✅ 支持 | 完整功能测试 | 功能验证 |
| quickstart_sc001.py | ✅ 支持 | 快速验证 | 日常开发 |
| deepagent_example.py | ✅ 支持 | 综合示例 | 学习探索 |

## 🎓 学习路径

### 1. 观察第一次测试

```bash
# 运行快速开始，观察浏览器操作
python browser_launcher.py --test quickstart --url http://127.0.0.1:8899/
```

### 2. 理解测试流程

观察浏览器执行以下步骤：
1. 🌐 打开页面
2. 🔍 定位元素
3. ⌨️ 输入数据
4. 🖱️ 点击操作
5. ⏱️ 等待响应
6. ✅ 验证结果

### 3. 尝试不同测试

```bash
# 尝试不同的测试类型
python browser_launcher.py --test auto
python browser_launcher.py --test login
python browser_launcher.py --test basic
```

### 4. 自定义测试

修改测试脚本中的 `test_request` 来创建自定义测试。

## 🎉 开始使用

### 推荐的第一次使用

```bash
# 1. 确保测试服务器运行
curl http://127.0.0.1:8899/

# 2. 运行浏览器显示测试
python examples/agent/browser_launcher.py --test quickstart --url http://127.0.0.1:8899/

# 3. 观察浏览器执行测试
# 你应该看到浏览器自动打开并执行测试步骤
```

### 高级使用

```bash
# 运行完整的浏览器测试套件
python examples/agent/test_sc001_browser.py

# 选择模式 1 (完整浏览器测试)
# 观察详细的测试过程和结果分析
```

## 📞 获取帮助

如果遇到问题：

1. 检查测试服务器连接
2. 验证浏览器驱动安装
3. 查看错误日志信息
4. 参考故障排除部分

## 🌟 总结

现在所有 AWT DeepAgent 测试脚本都支持浏览器显示模式！

**主要优势:**
- 🌐 实时观察测试过程
- 🎯 直观的调试体验
- 📊 可视化结果验证
- 🔧 便于问题定位

**推荐使用:**
- 💻 开发调试时
- 🔍 问题分析时
- 📚 学习演示时
- 🎯 功能验证时

🌐 **开始享受可视化的 AI 测试体验吧！**