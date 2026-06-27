# Agent 浏览器驱动与多轮状态保持

> 适用范围：`aat agent chat`（基于 LangChain Deep Agents 的对话式测试代理）
> 相关代码：`src/aat/agent/`、`src/aat/cli/agent_cmd.py`、`src/aat/engine/web.py`

本文回答两个问题：

1. `aat agent` 是如何调用浏览器、并通过多轮对话操作浏览器的？
2. 在多轮会话中，浏览器的状态（页面 DOM、登录态、cookies）是如何保持的？

---

## 一、整体架构

`aat agent chat` 的本质是 **LangChain Deep Agents 框架 + Tool-Calling（工具调用）+ Playwright 浏览器引擎** 的组合。整条链路由四层构成：

```
CLI 对话循环 (cli/agent_cmd.py)
        │  chat_with_plan(message, history)
        ▼
AgentSupervisor (agent/supervisor.py) ── 协调层
        │  create_deep_agent(model, tools, system_prompt)
        ▼
Deep Agents 框架 (LLM 决策 + 自动工具调用循环)
        │  调用 navigate_tool / click_tool / ...
        ▼
BrowserToolbox (agent/browser_tools.py) ── 工具层
        │  engine.navigate() / engine.page.locator() ...
        ▼
WebEngine (engine/web.py) ── Playwright 真实浏览器
```

关键认知：**LLM 并不"直接"操作浏览器**。浏览器被封装成一组 LangChain `@tool` 函数，LLM 通过标准的 tool-calling 协议（输出 `tool_call` → 框架执行 → 结果回灌）来驱动。真正的"思考 → 操作 → 观察"循环发生在 Deep Agents 框架内部。

---

## 二、浏览器能力 = 一组 LangChain Tools

浏览器操作在 `agent/browser_tools.py` 中被封装为一组 `@tool`（`build_tools()`，`browser_tools.py:171`）：

| 工具 | 作用 | 底层调用 |
|------|------|---------|
| `navigate_tool(url)` | 打开网页 | `engine.navigate()` → `page.goto()` |
| `click_tool(selector)` | 点击元素 | `engine.page.locator(selector).click()` |
| `type_tool(selector, text)` | 输入文本 | `locator.fill(text)` |
| `verify_tool(text)` | 校验文本可见 | `page.inner_text("body")` |
| `get_text_tool(...)` | 读取页面内容（默认截断 8000 字防 token 爆炸） | `page.inner_text()` |
| `screenshot_tool(...)` | 截图存盘 | `engine.screenshot()` |
| `analyze_tool(url)` | 导航 + 统计表单/按钮/链接数 | `page.evaluate(...)` |

设计要点：每个工具返回的是**人类可读字符串**（如 `"Successfully clicked #login"`）。这个字符串会被 Deep Agents 自动作为 tool result 喂回给 LLM，LLM 据此决定下一步。

---

## 三、工具与真实浏览器的绑定（在 `initialize()` 中完成）

`AgentSupervisor.initialize()`（`supervisor.py:74`）做三件事把链条串起来：

1. **创建 WebEngine**（`supervisor.py:88-100`）——若未传入已有引擎，则用 `EngineConfig` 新建一个 Playwright `WebEngine`，交互式聊天固定 `headless=False`（`agent_cmd.py:134`）。
2. **构建工具集**（`supervisor.py:145`）——`BrowserToolbox(self._engine, ...)` 把上面那组 `@tool` 绑定到这个具体的 engine 实例。
3. **创建 Deep Agent**（`supervisor.py:121`）：

   ```python
   create_deep_agent(model=model_instance, tools=..., system_prompt=..., permissions=...)
   ```

   Deep Agents 把 model + tools + system prompt 组装成一个**自带工具调用循环的 agent**：LLM 输出 tool_call → 框架执行对应工具 → 把结果回灌 → 让 LLM 继续，直到 LLM 给出最终文本回复。这一层负责"多步推理 + 反复操作浏览器"。

模型实例化由 `agent/model_factory.py` 按 provider 处理：

- `anthropic` / `openai`：走 `provider:model` 标识符，让 deepagents 直接解析；
- `zhipuai`：用 AWT 自己的 `ZhipuAIAdapter` 构造一个 `ChatOpenAI` 实例（智谱走 OpenAI 兼容协议）。

---

## 四、多轮对话 = history 注入

多轮对话能力来自 `chat_with_plan()`（`supervisor.py:230`）与 CLI 循环（`agent_cmd.py:159`）的配合：

```python
# supervisor.py:242-245
messages = list(history) if history else []
messages.append({"role": "user", "content": message})
agent_response = await self._deep_agent.ainvoke({"messages": messages})
```

```python
# agent_cmd.py:181-184 —— CLI 维护并裁剪历史
history.append({"role": "user", "content": user_input})
history.append({"role": "assistant", "content": response})
if len(history) > 40:
    history = history[-40:]   # 保留最近 20 轮，控制 token
```

每轮把**完整对话历史 + 新消息**整体发送。这样用户说"再点一次刚才那个按钮"时，agent 能从 history 理解上下文。

> 注意：history 只存 *用户/助手文本*。工具调用过程（点击、截图等）发生在单次 `ainvoke` 内部的 tool-calling 循环里，对用户不可见，也不会进入跨轮 history。

此外，`supervisor.py` 集成了 Deep Agents 的 `write_todos` 任务规划工具（通过 `TodoListMiddleware`）。多步任务时 agent 会先写一个 checklist 并跟踪进度；`chat_with_plan` 返回的 `ChatResult.plan` 就是这个计划，CLI 用 `render_plan()` 渲染成可勾选列表展示（`agent_cmd.py:187`）。可通过 `enable_planning` 开关关闭。

---

## 五、多轮会话中浏览器状态如何保持

> 核心结论：**浏览器状态根本不在 LLM 上下文里维持，而是靠一个跨整个会话存活的 Playwright `Page` / `BrowserContext` 对象。**
> LLM 每轮看到的只是文本历史；真实页面状态（DOM、cookies、登录态）活在那个常驻的浏览器进程里。

### 5.1 两条独立链路

| 层面 | 载体 | 生命周期 |
|------|------|---------|
| **浏览器/页面状态**（DOM、cookies、localStorage、登录态） | 单例 `WebEngine` 内的 `_page` / `_context` | 整个 CLI 会话，直到 `cleanup()` |
| **对话上下文**（"刚才点了什么"） | `history` 列表，文本注入 `ainvoke` | 每轮重发，最多保留 20 轮 |

二者**完全独立**维持。常见误解是"多轮 = 把页面状态塞进 LLM"——其实不是。

### 5.2 单例 WebEngine：会话级只创建一次、只销毁一次

状态不丢的根基是 engine 实例只有一个、且活得够久：

```
chat 启动
  └─ create_supervisor() → AgentSupervisor.__init__   (self._engine = None)
       └─ initialize()
            └─ self._engine = WebEngine(...)           ← 唯一实例，赋给 supervisor
                 └─ BrowserToolbox(self._engine, ...)   ← 工具箱持有同一个引用
  └─ while True:  (对话循环 N 轮)
       └─ supervisor.chat_with_plan(...)               ← 每轮都用这同一个 engine
  └─ finally: supervisor.cleanup() → engine.stop()     ← 只在退出时才关浏览器
```

证据：

- `supervisor.py:64` `self._engine = engine` —— supervisor 持有引用
- `supervisor.py:100` `self._engine = WebEngine(config=engine_config)` —— 只在 `initialize()` 建一次
- `agent_cmd.py:199` `await supervisor.cleanup()` 放在 `finally` —— 整个对话循环结束后才 stop
- `browser_tools.py:145` `BrowserToolbox(self._engine, ...)` —— 所有工具共享同一个 engine

因此从第 1 轮到第 N 轮，工具调用的 `engine.page` 永远指向**同一个** Playwright `Page` 对象。

### 5.3 单个 Page：DOM 和导航历史在它内部累积

`WebEngine.start()`（`web.py:175`）只创建**一个** page：

```python
self._browser  = await browser_type.launch(...)
self._context  = await self._browser.new_context(...)
self._page     = await self._context.new_page()   # 全程唯一
```

之后所有 `navigate` / `click` / `type` 都操作这个 `self._page`，从不新建。因此一个典型跨轮登录场景：

- 第 1 轮 `navigate("https://app.com")` → 跳到登录页
- 第 2 轮 `type("#user", ...)` + `click("#login")` → 登录成功，**cookies 写入 `_context`**
- 第 3 轮 `navigate("https://app.com/dashboard")` → 同一个 context 仍带着登录 cookies，**直接进 Dashboard，无需重新登录**

状态能跨轮保持的物理原因：Playwright 的 `BrowserContext` 在进程内持续持有 cookies / localStorage / sessionStorage，而它从第 1 轮一直活到 `cleanup()`。

### 5.4 懒启动 + `_started()` 守卫：保证复用同一个 page

`BrowserToolbox` 不在初始化时启动浏览器，而是**首次调用工具时**才 start（`browser_tools.py:28`）：

```python
async def ensure_started(self):
    if self.engine._page is None:        # browser_tools.py:32
        await self.engine.start()
```

`click` / `type` 等工具靠 `_started()`（`browser_tools.py:35-37`）判断是否已启动。一旦首轮 `ensure_started()` 启动过，`_page` 就不再是 `None`，后续所有轮次工具调用都**复用**而非重启——这正是状态不丢的关键守卫。若每轮重启，cookies 和登录态会全部丢失。

### 5.5 （可选）跨进程持久化：`save_session` / `load_session`

`WebEngine` 还提供把状态**落盘**的能力（`web.py:231-273`）：

```python
await self._context.storage_state(path=str(p))      # 存 cookies + localStorage
# 重新建 context 时用 storage_state=... 恢复
```

不过在当前 `agent chat` 流程里**默认未调用**——agent 多轮会话靠进程内单例，不需要落盘。此能力主要给 `aat run`（脚本化执行、跨次运行恢复登录态）使用。`cleanup()` 时只 `stop()`、不存盘，所以**退出 chat 后状态即消失**，下次需重来。

### 5.6 对话上下文如何补足"页面状态"的认知

浏览器状态自己活着，但 LLM 每轮无状态——它不知道当前页面长什么样。补足方式：

- 每次工具返回的可读字符串（`"Successfully logged in"`、`get_text` 读到的页面文本）会被 Deep Agents 回灌进当轮 LLM 上下文；
- 下一轮用户问"现在页面有什么按钮"时，LLM 会主动再调一次 `get_text_tool` / `analyze_tool` 去**读取当前真实页面**，而不是凭记忆猜。

即：**真实状态在浏览器里，LLM 通过"再次调用工具观察"获取最新状态**；history 只负责对话连贯性，不负责状态快照。

---

## 六、一句话总结

- **驱动**：浏览器操作封装为 LangChain `@tool`，交给 Deep Agents 的 tool-calling 循环自主驱动；Supervisor 只做组装与协调。
- **多轮**：CLI 维护 `history` 列表，每轮整体注入 `ainvoke({"messages": ...})` 实现上下文延续。
- **状态保持**：靠「单例 `WebEngine` + 单个常驻 `Page` / `Context`，从首轮懒启动一直活到 `cleanup()`」——Playwright `BrowserContext` 自动持有 cookies / localStorage，跨轮导航、登录、操作累积自然延续。退出 `agent chat` 即 `stop()`，状态不落盘、随之消失。
