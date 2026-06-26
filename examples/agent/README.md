# AWT DeepAgent 测试示例集合

本目录包含了基于官方 LangChain DeepAgents 框架的 AWT 测试示例，展示了从基础到高级的各种使用场景。

## 🌐 浏览器显示模式支持

**🎉 新功能！** 所有测试脚本现在都支持浏览器显示模式，让你可以实时观察测试执行过程。

### 快速启用浏览器显示

```bash
# 使用统一启动器（推荐）
python examples/agent/browser_launcher.py --test quickstart --url http://127.0.0.1:8899/

# 或直接运行专用浏览器测试
python examples/agent/test_sc001_browser.py
```

**📖 详细指南:** 参见 [BROWSER_DISPLAY_GUIDE.md](BROWSER_DISPLAY_GUIDE.md)

## 📁 示例文件列表

### 🎯 快速开始

| 文件名 | 描述 | 适合人群 |
|--------|------|----------|
| **quickstart_sc001.py** | 最简单的快速开始示例 | 初学者 |
| **README_SC001.md** | SC-001 详细使用指南 | 所有用户 |

### 🧪 测试脚本

| 文件名 | 描述 | 功能 |
|--------|------|------|
| **test_deepagent_simple.py** | 基础功能测试 | 验证 DeepAgent 基本功能 |
| **test_deepagent_creation.py** | DeepAgent 创建测试 | 测试代理创建和调用 |
| **test_deepagent_e2e.py** | 端到端测试 | 完整工作流程测试 |
| **test_deepagent_basic.py** | 单元测试 | 工具和功能单元测试 |

### 🎯 场景测试

| 文件名 | 描述 | 对应场景 |
|--------|------|----------|
| **test_sc_001_login.py** | SC-001 用户登录测试 | 完整交互式测试 |
| **test_sc_001_auto.py** | SC-001 自动化测试 | CI/CD 集成测试 |

### 📖 示例和文档

| 文件名 | 描述 | 内容 |
|--------|------|------|
| **deepagent_example.py** | 综合示例程序 | 7 种不同的使用示例 |
| **README.md** | 本文件 | 总体导航和说明 |

## 🚀 快速开始

### 1. 环境准备

```bash
# 确保依赖已安装
pip install -e .

# 验证安装
python -c "from deepagents import create_deep_agent; print('✅ DeepAgent 安装成功')"
```

### 2. 运行第一个测试

```bash
# 最简单的快速开始
python examples/agent/quickstart_sc001.py
```

### 3. 探索更多示例

```bash
# 基础功能测试
python examples/agent/test_deepagent_simple.py

# DeepAgent 创建测试
python examples/agent/test_deepagent_creation.py

# SC-001 场景测试
python examples/agent/test_sc_001_auto.py
```

## 📋 使用场景指南

### 场景 1: 学习和探索

**推荐顺序:**
1. `quickstart_sc001.py` - 了解基本概念
2. `README_SC001.md` - 深入理解使用方式
3. `test_deepagent_simple.py` - 测试各种功能
4. `deepagent_example.py` - 探索高级特性

### 场景 2: 日常开发测试

**推荐使用:**
- `test_sc_001_auto.py` - 快速自动化测试
- `quickstart_sc001.py` - 简单功能验证

### 场景 3: CI/CD 集成

**推荐使用:**
- `test_sc_001_auto.py` - 标准退出码，便于集成
- `test_deepagent_simple.py` - 预检查测试

### 场景 4: 深度测试和调试

**推荐使用:**
- `test_sc_001_login.py` - 交互式调试
- `test_deepagent_e2e.py` - 完整流程测试
- `test_deepagent_creation.py` - 深入功能测试

### 场景 5: 回归和验证

**推荐使用:**
- `test_deepagent_basic.py` - 单元测试验证
- `test_deepagent_simple.py` - 集成测试验证

## 🎯 基于 YAML 场景的测试

### 转换现有 YAML 场景

如果你有现有的 YAML 测试场景（如 `SC-001_successful_user_login.yaml`），可以按以下步骤转换为 DeepAgent 测试：

#### 步骤 1: 理解 YAML 场景

```yaml
steps:
  - action: navigate
    value: http://localhost:5173/
  - action: find_and_type
    value: admin@example.com
  # ... 更多步骤
```

#### 步骤 2: 转换为自然语言

```python
test_request = """
测试场景：
1. 导航到 http://localhost:5173/
2. 输入邮箱 admin@example.com
3. 输入密码 changethis
4. 点击登录按钮
5. 验证登录成功
"""
```

#### 步骤 3: 执行测试

```python
result = await supervisor.test_from_natural_language(
    user_request=test_request,
    start_url="http://localhost:5173/",
    mode="autonomous"
)
```

### 参考示例

查看 `test_sc_001_login.py` 和 `test_sc_001_auto.py` 了解完整的转换示例。

## 🔧 工具和功能

### 可用工具 (15个)

#### 导航工具
- `smart_navigate` - 智能导航
- `go_back` - 返回上一页
- `go_forward` - 前进到下一页
- `refresh_page` - 刷新页面

#### 交互工具
- `smart_click` - 智能点击
- `smart_type` - 智能输入
- `select_option` - 选择下拉选项

#### 验证工具
- `verify_text_visible` - 验证文本可见
- `verify_element_exists` - 验证元素存在
- `verify_url_contains` - 验证URL包含

#### 分析工具
- `analyze_page` - 分析页面结构
- `take_screenshot` - 截取屏幕截图
- `check_console` - 检查控制台
- `wait_for_element` - 等待元素出现
- `locate_element` - 定位页面元素

### 运行模式

- **interactive** - 交互式模式，重要操作前确认
- **autonomous** - 自主模式，自动执行
- **conservative** - 保守模式，每步都确认
- **aggressive** - 激进模式，大胆探索

## 💡 使用技巧

### 技巧 1: 逐步调试

```python
# 从简单测试开始
result = await supervisor.test_from_natural_language(
    "测试导航到登录页",
    "http://localhost:5173/",
    "autonomous"
)

# 逐步增加复杂度
result = await supervisor.test_from_natural_language(
    "测试导航、输入和点击",
    "http://localhost:5173/",
    "autonomous"
)
```

### 技巧 2: 使用不同模式

```python
# 开发时用交互模式
result = await supervisor.test_from_natural_language(
    test_request, start_url, mode="interactive"
)

# 生产时用自主模式
result = await supervisor.test_from_natural_language(
    test_request, start_url, mode="autonomous"
)
```

### 技巧 3: 错误处理

```python
try:
    result = await supervisor.test_from_natural_language(...)
    if not result.success:
        print(f"失败原因: {result.failures}")
except Exception as e:
    print(f"执行错误: {str(e)}")
```

### 技巧 4: 批量测试

```python
scenarios = [
    ("测试登录", "登录功能测试"),
    ("测试注册", "注册功能测试"),
    ("测试购物车", "购物车功能测试"),
]

for name, desc in scenarios:
    result = await supervisor.test_from_natural_language(
        desc, "http://localhost:5173/", "autonomous"
    )
    print(f"{name}: {'✅' if result.success else '❌'}")
```

## 📊 测试结果分析

### 结果结构

```python
result.success          # 是否成功
result.summary          # 测试摘要
result.steps_completed  # 完成步骤数
result.failures         # 失败列表
result.screenshots      # 截图列表
result.timestamp       # 时间戳
result.raw_result       # 原始结果
```

### 结果解析

```python
# 检查测试是否成功
if result.success:
    print("测试通过")
else:
    # 分析失败原因
    for failure in result.failures:
        print(f"失败: {failure}")

# 查看详细信息
print(f"完成步骤: {result.steps_completed}")
print(f"测试摘要: {result.summary}")
```

## 🛠️ 故障排除

### 常见问题

**Q: 导入错误？**
```bash
pip install -e .
```

**Q: AI 连接失败？**
检查 `aat.config.yaml` 中的 AI 配置

**Q: 工具调用失败？**
```python
# 验证工具加载
from aat.agent import get_awt_deepagent_tools
print(len(get_awt_deepagent_tools()))  # 应该是 15
```

**Q: 测试超时？**
增加超时时间或调整测试步骤

## 📚 学习路径

### 初学者路径

1. 运行 `quickstart_sc001.py` 了解基本概念
2. 阅读 `README_SC001.md` 理解详细用法
3. 运行 `test_deepagent_simple.py` 测试功能
4. 修改 `quickstart_sc001.py` 创建自己的测试

### 中级用户路径

1. 运行 `test_sc_001_login.py` 了解完整功能
2. 运行 `deepagent_example.py` 探索高级特性
3. 查看 `test_deepagent_creation.py` 理解代理创建
4. 转换自己的 YAML 场景为 DeepAgent

### 高级用户路径

1. 运行 `test_deepagent_e2e.py` 了解端到端流程
2. 运行 `test_deepagent_basic.py` 了解单元测试
3. 创建自定义工具和功能
4. 集成到自己的 CI/CD 流程

## 🎉 开始使用

选择一个适合你的示例开始：

```bash
# 快速开始（推荐）
python examples/agent/quickstart_sc001.py

# 基础测试
python examples/agent/test_deepagent_simple.py

# 场景测试
python examples/agent/test_sc_001_auto.py

# 完整示例
python examples/agent/deepagent_example.py
```

🚀 享受 AI 驱动的智能测试体验！