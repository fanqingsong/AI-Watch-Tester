# AAT Generate 底层实现详解

## 🎯 `aat generate` 命令概述

`aat generate` 是 AAT 的 AI 场景生成功能，通过分析需求文档自动生成可执行的测试场景 YAML 文件。

## 🏗️ 底层实现流程

### 1. 命令入口和参数验证

```python
# generate_cmd.py
def generate_command(
    file_path: str | None = typer.Option(None, "--from", "-f"),
    config_path: str | None = typer.Option(None, "--config", "-c"),
    output_dir: str | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Generate test scenarios from spec document using AI."""
    
    # 参数验证
    if file_path is None:
        typer.echo("Error: --from / -f is required")
        raise typer.Exit(code=1)
    
    source = Path(file_path)
    if not source.exists():
        typer.echo(f"File does not exist: {file_path}")
        raise typer.Exit(code=1)
```

### 2. 异步执行流程

```python
async def _generate(source, config_path, output_dir):
    # 1. 加载配置
    config = load_config(config_path)
    
    # 2. 获取解析器
    parser = _get_parser(source.suffix.lower())
    
    # 3. 解析文档
    text, images = await parser.parse(source)
    
    # 4. 检查缓存
    cached = get_cached_scenarios(cache_key, config.data_dir)
    if cached:
        return [Scenario(**s) for s in cached]
    
    # 5. 成本估算
    est = estimate_cost(config.ai.provider, config.ai.model, text)
    
    # 6. 创建 AI 适配器
    adapter = _get_adapter(config)
    
    # 7. 生成场景
    scenarios = await adapter.generate_scenarios(text, images)
    
    # 8. 保存场景
    for scenario in scenarios:
        save_scenario_yaml(scenario, dest_dir)
```

### 3. 文档解析

#### MarkdownParser 实现

```python
class MarkdownParser(BaseParser):
    """解析 markdown 和纯文本文件"""
    
    async def parse(self, file_path: Path) -> tuple[str, list[bytes]]:
        # 读取文本内容
        text = file_path.read_text(encoding="utf-8")
        
        # 提取图片引用
        images = []
        for match in _IMAGE_REF_RE.finditer(text):
            # ![alt](path) -> 提取图片字节
            img_path = (file_path.parent / img_rel).resolve()
            img_bytes = img_path.read_bytes()
            images.append(img_bytes)
        
        return text, images
```

#### 支持的文件格式

- `.md` - Markdown 文件（支持图片提取）
- `.txt` - 纯文本文件（无图片）

### 4. AI 提示词系统

#### 系统提示词模板

```python
_SYSTEM_GENERATE_SCENARIOS = """
You are an expert QA engineer. Given a specification document, generate test scenarios as a JSON array.

Each scenario must follow this EXACT format:
{
  "id": "SC-001",
  "name": "Short name",
  "description": "What this tests",
  "tags": ["tag1"],
  "steps": [...],
  "expected_result": []
}

VALID ACTIONS:
- "navigate" — 导航到URL
- "find_and_click" — 查找并点击元素
- "find_and_type" — 查找并输入文本
- "type_text" — 输入文本
- "press_key" — 按键
- "assert" — 断言
- "wait" — 等待
- "screenshot" — 截图

CRITICAL RULES:
- 使用 {{url}} 作为基础URL
- 场景按业务流程排序
- 后续场景可以依赖前置场景

Return ONLY a valid JSON array, no markdown fences.
"""
```

#### 用户提示词构建

```python
content = f"""Analyze this specification and generate test scenarios:

{document_text[:8000]}  # 限制输入长度

Generate 3-5 test scenarios covering main user flows."""

messages = [
    {"role": "system", "content": _SYSTEM_GENERATE_SCENARIOS},
    {"role": "user", "content": content},
]
```

### 5. AI 适配器调用

#### ZhipuAI 实现

```python
async def generate_scenarios(self, document_text, images):
    # 构建请求
    content = f"""Analyze this specification and generate test scenarios:
    
{document_text[:8000]}

Generate 3-5 test scenarios covering main user flows."""

    messages = [
        {"role": "system", "content": _SYSTEM_GENERATE_SCENARIOS},
        {"role": "user", "content": content},
    ]
    
    # 调用 API
    response = await self._call_api(messages, max_tokens=4096)
    
    # 解析响应（支持 JSON 和 YAML）
    scenarios_data = parse_ai_response(response)
    
    # 转换为 Scenario 对象
    scenarios = []
    for item in scenarios_data:
        if "id" not in item:
            item["id"] = f"scenario-{i}"
        scenario = Scenario.model_validate(item)
        scenarios.append(scenario)
    
    return scenarios
```

#### 响应解析

```python
def parse_ai_response(response):
    # 清理可能的 markdown 代码块
    cleaned_response = response.strip()
    if cleaned_response.startswith("```"):
        lines = cleaned_response.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]  # 移除首行
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]  # 移除末行
        cleaned_response = "\n".join(lines)
    
    # 先尝试 JSON 解析
    try:
        return json.loads(cleaned_response)
    except json.JSONDecodeError:
        # 如果 JSON 失败，尝试 YAML 解析
        return yaml.safe_load(cleaned_response)
```

### 6. 场景数据模型

#### Scenario 结构

```python
class Scenario(BaseModel):
    id: str                          # 场景ID
    name: str                        # 场景名称
    description: str                 # 场景描述
    tags: list[str] = []             # 标签
    depends_on: list[str] = []      # 依赖的场景
    vars: dict = {}                  # 变量
    steps: list[Step]               # 测试步骤
    expected_result: list[Expect] = []  # 预期结果
    teardown: list = []              # 清理步骤
```

#### Step 结构

```python
class Step(BaseModel):
    step: int                       # 步骤编号
    action: str                      # 动作类型
    target: Target | None           # 目标元素
    value: str | None                # 输入值
    description: str                # 步骤描述
    humanize: bool = True           # 人类化执行
    method: str = "auto"            # 执行方法
    learn: bool = True              # 学习模式
    fallback: bool = True          # 降级策略
    timeout_ms: int = 10000        # 超时时间
    # ... 更多字段
```

### 7. 场景保存

```python
# 保存为 YAML 文件
for scenario in scenarios:
    safe_name = scenario.name.replace(" ", "_").lower()
    filename = f"{scenario.id}_{safe_name}.yaml"
    out_path = dest_dir / filename
    
    data = scenario.model_dump(mode="json")
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, 
                      default_flow_style=False, 
                      allow_unicode=True, 
                      sort_keys=False)
```

## 🎯 AI 生成逻辑

### 1. 业务流程排序

AI 会按照业务流程逻辑对场景进行排序：

```json
[
  {
    "id": "SC-001",
    "name": "User Registration",
    "depends_on": []
  },
  {
    "id": "SC-002", 
    "name": "User Login",
    "depends_on": ["SC-001"]  // 必须先注册才能登录
  },
  {
    "id": "SC-003",
    "name": "Dashboard Access",
    "depends_on": ["SC-002"]  // 必须先登录才能访问
  }
]
```

### 2. 动作类型智能选择

AI 根据需求描述自动选择合适的动作类型：

| 需求描述 | AI 选择的动作 | 示例 |
|----------|---------------|------|
| "打开登录页面" | `navigate` | `{"action": "navigate", "value": "{{url}}/login"}` |
| "输入用户名" | `find_and_type` | `{"action": "find_and_type", "target": {"text": "Email"}, "value": "user@test.com"}` |
| "点击登录按钮" | `find_and_click` | `{"action": "find_and_click", "target": {"text": "Login"}}` |
| "等待页面加载" | `wait` | `{"action": "wait", "value": "2000"}` |
| "验证显示用户信息" | `assert` | `{"action": "assert", "assert_type": "text_visible", "expected": [{"type": "text_visible", "value": "用户信息"}]}` |

### 3. 元素定位策略

AI 会智能选择最可靠的元素定位方式：

```python
# 优先级：text > selector > image
"target": {
    "text": "Login",        # 文字匹配（OCR + DOM）
    "selector": "#login-btn", # CSS选择器（可选）
    "image": null,          # 图片匹配（可选）
    "icon": null            # 图标匹配（可选）
}
```

## 🔧 技术架构

### 完整数据流

```
用户需求文档 (requirements.md)
    ↓
MarkdownParser 解析
    ↓
提取文本内容和图片
    ↓
成本估算和确认
    ↓
AI Adapter (ZhipuAI/OpenAI/etc.)
    ↓
发送提示词到 LLM
    ↓
接收响应并解析 (JSON/YAML)
    ↓
Pydantic 数据验证
    ↓
生成 Scenario 对象
    ↓
保存为 YAML 文件
    ↓
scenarios/SC-001_*.yaml
```

### 模块协作

```
generate_cmd.py (CLI入口)
    ↓
parsers/markdown_parser.py (文档解析)
    ↓
adapters/zhipuai.py (AI调用)
    ↓
adapters/prompts.py (提示词模板)
    ↓
core/scenario_models.py (数据验证)
    ↓
yaml.dump (文件保存)
```

## 💡 高级特性

### 1. 缓存机制

```python
# 基于URL和内容生成缓存键
cache_key = spec_cache_key(config.url, text)

# 检查缓存
cached = get_cached_scenarios(cache_key, config.data_dir)
if cached:
    return [Scenario(**s) for s in cached]

# 保存到缓存
save_cached_scenarios(cache_key, scenario_dicts, config.data_dir)
```

### 2. 成本估算

```python
# 调用前估算成本
est = estimate_cost(
    config.ai.provider,
    config.ai.model,
    text,
    estimated_output_tokens=4096
)

# 显示成本估算
typer.echo(f"Estimated cost: ${est['cost_usd']:.4f}")

# 实际成本记录
actual_cost = log_cost(
    config.ai.provider,
    config.ai.model,
    "generate_scenarios",
    est["input_tokens"],
    est["output_tokens"],
    config.data_dir
)
```

### 3. 错误处理

```python
# 文档解析错误
if not source.exists():
    raise ParserError(f"File not found: {file_path}")

# AI 响应解析错误
if scenarios_data is None:
    raise AdapterError(f"Failed to parse scenarios: {parse_error}")

# 数据验证错误
scenario = Scenario.model_validate(item)  # Pydantic 验证
```

### 4. 多格式支持

```python
# 支持 JSON 和 YAML 格式的 AI 响应
try:
    scenarios_data = json.loads(cleaned_response)
except json.JSONDecodeError:
    scenarios_data = yaml.safe_load(cleaned_response)
```

## 🎯 实际应用示例

### 输入需求文档

```markdown
# 用户登录功能测试需求

## 测试目标
验证用户登录功能的正确性

## 测试页面
- URL: http://localhost:5173/

## 测试步骤
1. 打开登录页面
2. 输入用户名 "admin@example.com"
3. 输入密码 "changethis"
4. 点击登录按钮
5. 验证登录成功，跳转到首页

## 预期结果
- 用户成功登录
- 页面跳转到首页
- 显示用户信息
```

### AI 生成过程

```python
# 1. 提取文档内容
text = """# 用户登录功能测试需求

## 测试目标
验证用户登录功能的正确性
## 测试步骤
1. 打开登录页面
2. 输入用户名 "admin@example.com"
..."""

# 2. 构建提示词
messages = [
    {
        "role": "system", 
        "content": "You are an expert QA engineer. Generate test scenarios..."
    },
    {
        "role": "user",
        "content": f"Analyze this specification:\n\n{text}\n\nGenerate test scenarios..."
    }
]

# 3. 调用 AI API
response = await zhipuai_api.chat(messages)

# 4. 解析响应
scenarios_data = json.loads(response)
```

### 输出场景文件

生成的 `scenarios/SC-001_valid_user_login.yaml`：

```yaml
id: SC-001
name: Valid User Login
description: Verify user can log in with correct credentials and access the home page
tags:
  - login
  - smoke
  - positive
steps:
  - step: 1
    action: navigate
    value: '{{url}}'
    description: Navigate to login page
    
  - step: 2
    action: find_and_type
    target:
      text: Email
    value: admin@example.com
    description: Enter valid email
    
  - step: 3
    action: find_and_type
    target:
      text: Password
    value: changethis
    description: Enter valid password
    
  - step: 4
    action: find_and_click
    target:
      text: Login
    description: Click login button
    
  - step: 5
    action: wait
    value: '2000'
    description: Wait for redirection

expected_result:
  - type: text_visible
    value: 用户信息
```

## 📊 性能和成本

### 成本分析

| AI 模型 | 输入成本 | 输出成本 | 总成本 (单次生成) |
|---------|----------|----------|------------------|
| GLM-4.7 | ¥0.001/1K tokens | ¥0.002/1K tokens | ~¥0.05 |
| GLM-5.1 | ¥0.004/1K tokens | ¥0.008/1K tokens | ~¥0.15 |
| GPT-4o | $0.15/1M tokens | $0.60/1M tokens | ~$0.10 |

### 性能指标

- **解析速度**: <100ms (文档解析)
- **AI 调用**: 5-15秒 (取决于模型和文档长度)
- **场景生成**: 3-5个场景
- **文件保存**: <10ms

## 🔍 最佳实践

### 1. 需求文档编写

```markdown
# 清晰的结构
## 测试目标
[明确的目标描述]

## 业务流程
[详细的步骤说明]

## 预期结果
[具体的验证标准]
```

### 2. 分场景生成

```markdown
# 单个文件包含多个场景
# user_flow.md

## 场景1: 用户注册
[注册流程描述]

## 场景2: 用户登录
[登录流程描述]

## 场景3: 密码重置
[密码重置流程]
```

### 3. 迭代优化

```bash
# 初次生成
aat generate --from v1_requirements.md

# 手动调整生成的场景
vim scenarios/SC-001_*.yaml

# 更新需求后重新生成
aat generate --from v2_requirements.md --output scenarios/v2/
```

### 4. 结合使用

```bash
# 完整工作流
aat scan --url http://localhost:5173/     # 扫描页面
aat generate --from requirements.md          # 生成场景
aat validate scenarios/                      # 验证场景
aat run scenarios/SC-001_*.yaml               # 运行测试
```

## 🛠️ 调试和故障排除

### 常见问题

#### 1. AI 响应格式错误

```bash
# 检查 AI 响应格式
# 如果 AI 返回的不是有效 JSON/YAML，会解析失败
# 解决：调整提示词或重新生成
```

#### 2. 场景验证失败

```bash
# Pydantic 验证失败
# 检查生成的场景是否缺少必需字段
aat validate scenarios/SC-001_*.yaml
```

#### 3. 成本过高

```bash
# 使用更经济的模型
aat config set model glm-4-flash
aat generate --from requirements.md
```

## 🎓 技术亮点

### 1. 智能业务流程分析

AI 自动理解业务逻辑并排序场景：
- 注册 → 登录 → 使用流程
- 依赖关系自动建立

### 2. 多格式兼容性

- 支持 JSON 和 YAML 格式
- 自动清理 Markdown 代码块
- 双格式解析容错

### 3. 成本优化

- 缓存机制避免重复调用
- 成本预估算用户确认
- Token 数量控制

### 4. 数据验证

- Pydantic 模型验证
- 自动补充缺失字段
- 类型安全保证

### 5. 可扩展性

- 插件化解析器架构
- 统一的 AI 适配器接口
- 共享提示词模板

---

**相关文档**:
- [SCAN_IMPLEMENTATION.md](SCAN_IMPLEMENTATION.md) - 扫描实现详解
- [README.md](README.md) - 使用指南
- [CLI_USAGE.md] - 命令行工具详解