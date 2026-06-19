# AAT Dashboard 使用指南

## 🌐 界面概览

访问地址：http://localhost:9500

```
┌─────────────────────────────────────────────────────────────────┐
│ AAT Dashboard                                                 │
├─────────────┬───────────────────┬─────────────────────────────────────┤
│ Setup       │ Test Management    │ Event Log                               │
├─────────────┴───────────────────┴─────────────────────────────────────┤
│                                                               │
│  ┌─────────┐                   ┌─────────────────────┐              │
│  │Config   │                   │  Scenario List       │              │
│  │         │                   │  - SC-001 Register    │              │
│  │AI:      │                   │  - SC-002 Login      │              │
│  │Provider │                   │  - SC-003 Main Nav  │              │
│  │Model:   │                   │                      │              │
│  │API Key  │                   │  [Select All] [Run]    │              │
│  │         │                   │  [Loop] [Delete]     │              │
│  │         │                   │                      │              │
│  │URL:     │                   └─────────────────────┘              │
│  │http://..│                                                   │
│  │         │                   ┌─────────────────────┐              │
│  │         │                   │  Execution          │              │
│  │[Save]   │                   │  Progress bar        │              │
│  │         │                   │  [Stop]              │              │
│  │         │                   │                      │              │
│  └─────────┘                   └─────────────────────┘              │
│                                                               │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Server Management  │ Test Settings  │ Live Screenshot    │ │
│ │                     │                │                     │ │
│ │ [Start Server]        │ Engine: web    │                     │ │
│ │                     │ Browser: chromium│                     │ │
│ │                     │ Headless: Yes  │                     │ │
│ │                     │ Approval: manual│                     │ │
│ │                     │                │                     │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                               │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Event Log (实时日志)                                          │ │
│ │ [INFO] Config loaded                                        │ │
│ │ [SUCCESS] Scenario loaded                                    │ │
│ │ [ERROR] Test failed                                         │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 基础使用流程

### 1️⃣ 配置设置

#### AI 配置

1. **AI Provider** - 选择AI提供商
   - `claude` - Anthropic Claude
   - `openai` - OpenAI GPT
   - `zhipuai` - 智谱AI
   - `ollama` - 本地 Ollama

2. **Model** - 选择模型
   - Provider变更后，下拉菜单会自动更新可用模型
   - 或选择"Custom"输入自定义模型名称

3. **API Key** - 输入API密钥
   - 输入后点击 **[Save]** 保存
   - 保存成功后显示：`✓ API key已配置 (583dd9e6...)`
   - 刷新页面后会保留（绿色边框提示）

#### 测试配置

- **URL** - 被测应用地址
- **Engine** - 浏览器引擎（web/desktop）
- **Browser** - 浏览器类型（chromium/firefox/webkit）
- **Headless** - 是否显示浏览器窗口
- **Approval** - DevQA Loop批准模式
  - `manual` - 手动批准每次修复
  - `branch` - Git分支隔离
  - `auto` - 自动应用修复

#### 保存配置

- 修改任何配置后，**必须点击 [Save]** 按钮
- 成功提示：`✅ Config saved`
- 配置保存到：`.aat/config.yaml`

---

### 2️⃣ 场景管理

#### 加载场景

1. **查看场景列表**
   - 右侧面板显示所有可用场景
   - 显示：ID、名称、步骤数、状态

2. **刷新场景**
   - 点击 **[Refresh]** 按钮重新加载
   - 或修改场景路径后点击 **[Load]**

#### 执行场景

**单场景执行：**
1. 点击场景选中（或使用Shift+Click多选）
2. 点击 **[Run]** 按钮
3. 实时查看进度和日志

**批量执行：**
1. 点击 **[Select All]** 选中所有场景
2. 点击 **[Run]** 批量执行

**删除场景：**
- 选中场景后点击 **[Delete]**

---

### 3️⃣ 测试执行

#### 执行流程

```
┌─────────────────────────────────────────────────────┐
│ 1. 选择场景并点击 [Run]                          │
│    ↓                                                 │
│ 2. Execution 面板显示进度条                           │
│    - Running: 0% → 100%                            │
│    - 实时显示当前执行的步骤                          │
│    ↓                                                 │
│ 3. 查看测试结果                                       │
│    - Event Log 显示详细日志                            │
│    - 截图自动保存到 .aat/screenshots/                 │
│    ↓                                                 │
│  4. 查看最终结果                                       │
│    - scenarios/last_run.json 包含完整结果             │
└─────────────────────────────────────────────────────┘
```

#### 执行选项

- **verbosity** - 日志详细程度
  - `concise` - 快速模式（跳过等待/截图）
  - `detailed` - 完整模式（所有步骤）

- **screenshots** - 截图保存策略
  - `all` - 保存所有步骤截图
  - `before-after` - 只保存操作前后
  - `on-failure` - 仅失败时保存

---

### 4️⃣ DevQA Loop（AI自动修复）

#### 启动 DevQA Loop

1. 选中场景
2. 点击 **[Loop]** 按钮
3. AI自动执行：测试 → 分析失败 → 生成修复 → 重新测试

#### DevQA Loop 流程

```
┌───────────────────────────────────────────────────────┐
│ 1. 运行测试                                         │
│    ↓ 失败                                           │
│ 2. AI 分析失败原因                                    │
│    ↓ 生成修复建议                                      │
│ 3. 用户批准修复方案                                  │
│    - 显示修复内容                                     │
│    - 按 Enter 确认或输入 n 拒绝                     │
│    ↓                                                 │
│ 4. AI 应用代码修复                                   │
│    - 修改源代码文件                                   │
│    - 提交 Git commit（branch模式）                     │
│    ↓                                                 │
│ 5. 重新测试                                           │
│    ↓ 通过 → 完成                                       │
│    ↓ 失败 → 重复循环（最多10次）                      │
└───────────────────────────────────────────────────────┘
```

#### 批准模式说明

| 模式 | 行为 |
|------|------|
| **manual** | 每次修复都在终端提示批准 |
| **branch** | Git分支隔离，安全修复 |
| **auto** | 自动应用修复（谨慎使用） |

---

### 5️⃣ Server Management（被测应用管理）

#### 启动被测应用

1. **选择服务器类型**
   - Python (http.server) - 静态文件
   - Node.js (npx serve) - Node托管
   - React/Vue/Next.js - 前端框架
   - Flask/Django - 后端框架
   - Custom - 自定义命令

2. **设置参数**
   - **Port** - 服务端口（如3000, 5000, 8000）
   - **Path** - 项目目录路径

3. **启动服务器**
   - 点击 **[Start]** 按钮
   - 状态指示器变为绿色
   - URL自动填充到测试配置

#### 服务器管理

- **[Stop]** - 停止服务器
- **状态** - 显示服务器运行状态
- **日志** - Mini Log显示服务器输出

---

### 6️⃣ 实时监控

#### Live Screenshot

- 执行测试时实时显示浏览器截图
- 帮助确认测试步骤是否正确执行

#### Event Log

实时日志级别：
- **INFO** - 信息提示
- **SUCCESS** - 成功操作
- **WARNING** - 警告信息
- **ERROR** - 错误信息

---

## 🎯 典型使用场景

### 场景1：测试Web应用

```
1. 配置：
   - URL: http://localhost:3000
   - Engine: web, Browser: chromium
   
2. Server Management：
   - Type: React (npm run dev)
   - Port: 3000
   - Path: /path/to/react-app
   - [Start]
   
3. 测试：
   - 加载场景 → [Run]
```

### 场景2：测试Django应用

```
1. Server Management：
   - Type: Django
   - Port: 8000
   - Path: /path/to/django-app
   - [Start]
   
2. 配置：
   - URL: http://localhost:8000
   
3. 测试：
   - 选择场景 → [Run]
```

### 场景3：DevQA自动修复

```
1. 配置 AI Provider + API Key
2. 选择失败场景
3. [Loop] → 自动修复测试失败
4. 查看修复后的代码
5. 验证测试通过
```

---

## 🔧 故障排除

### API Key丢失

**问题**：刷新页面后API key为空

**解决**：
1. 检查 `.aat/config.yaml` 中的 `ai.api_key` 值
2. 重新输入API key并点击 [Save]
3. 确认保存后显示：`✓ API key已配置`

### 测试失败

**问题**：测试无法执行或一直失败

**排查步骤**：
1. 检查URL是否正确
2. 检查服务器是否运行（Server Management）
3. 查看Event Log详细错误信息
4. 检查Playwright浏览器是否安装（`playwright install chromium`）

### 场景加载失败

**解决**：
- 确认场景路径正确
- 点击 [Refresh] 重新加载
- 检查YAML格式是否正确

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `.aat/config.yaml` | 配置文件（AI、引擎、测试设置） |
| `.aat/screenshots/` | 测试截图 |
| `.aat/sessions/` | 浏览器会话 |
| `scenarios/` | 测试场景目录 |
| `scenarios/last_run.json` | 最近一次测试结果 |

---

## ⌨️ 快捷键提示

- **[Save]** - 保存配置更改（必须操作）
- **[Refresh]** - 刷新场景列表
- **[Select All]** - 全选场景
- **[Run]** - 执行选中的场景
- **[Loop]** - 启动AI自动修复
- **[Stop]** - 停止服务器或测试
