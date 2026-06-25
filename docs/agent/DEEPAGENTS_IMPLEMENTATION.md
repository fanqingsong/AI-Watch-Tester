# AWT Smart Agent 基于 DeepAgents 的实现方案

> **目标**: 将 AWT 从 YAML 测试框架升级为智能测试 Agent，使用 LangChain DeepAgents 作为 harness 框架

---

## 📋 目录

1. [架构设计](#架构设计)
2. [DeepAgents 能力映射](#deepagents-能力映射)
3. [多代理系统设计](#多代理系统设计)
4. [工具系统设计](#工具系统设计)
5. [实现路线图](#实现路线图)
6. [代码示例](#代码示例)

---

## 🏗️ 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    AWT Smart Agent System                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Supervisor Agent (主代理)                   │   │
│  │  - 接收用户自然语言测试需求                           │   │
│  │  - 协调子代理工作                                    │   │
│  │  - 人工审批和中断                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                         │                                    │
│          ┌──────────────┼──────────────┐                 │
│          ▼              ▼               ▼                 │
│  ┌──────────────┐ ┌──────────┐ ┌──────────────┐        │
│  │ Explorer     │ │ Tester   │ │ Analyzer     │        │
│  │ Agent        │ │ Agent    │ │ Agent        │        │
│  │              │ │          │ │              │        │
│  │ - 页面探索   │ │ - 执行   │ │ - 失败分析   │        │
│  │ - 发现功能   │ │ - 断言   │ │ - 生成修复   │        │
│  │ - 构建图谱   │ │ - 回归   │ │ - 智能建议   │        │
│  └──────────────┘ └──────────┘ └──────────────┘        │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         DeepAgents Harness Layer                    │   │
│  │  - 执行环境 (沙盒、工具、REPL)                       │   │
│  │  - 上下文管理 (记忆、缓存、技能)                     │   │
│  │  - 代理通信 (消息传递、状态同步)                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         AWT Engine Layer (现有)                     │   │
│  │  - WebEngine (Playwright)                           │   │
│  │  - Matchers (OCR/Vision/Template)                   │   │
│  │  - Adapters (AI providers)                          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 DeepAgents 能力映射

### 1. Execution Environment (执行环境)

**DeepAgents 提供**:
- 沙盒执行环境
- 虚拟文件系统
- 工具调用系统
- REPL/解释器

**AWT 集成**:
```python
# AWT 沙盒环境
class AWTsandbox:
    """AWT 测试沙盒"""
    
    def __init__(self):
        self.browser_pool = BrowserPool()  # 隔离的浏览器环境
        self.test_workspace = VirtualFS()   # 虚拟文件系统
        
    async def execute_test_step(self, step: TestStep):
        """在沙盒中执行测试步骤"""
        async with self.browser_pool.acquire() as browser:
            result = await self._run_step(browser, step)
            return self._sanitize_result(result)
```

### 2. Context Management (上下文管理)

**DeepAgents 提供**:
- 技能系统 (Skills)
- 记忆系统 (Memory)
- 摘要压缩 (Summarization)
- 上下文卸载 (Context Offloading)

**AWT 集成**:
```python
# AWT 上下文管理
class AWTContext:
    """AWT 测试上下文"""
    
    def __init__(self):
        self.exploration_memory = ExplorationMemory()
        self.user_preferences = UserPreferences()
        self.test_history = TestHistory()
        
    async def manage_context(self, current_context: TestContext):
        """智能上下文管理"""
        # 1. 提取关键信息
        key_info = self._extract_key_elements(current_context)
        
        # 2. 压缩历史上下文
        compressed = self._summarize_history(self.test_history)
        
        # 3. 卸载不重要的信息
        offloaded = self._offload_secondary_info(current_context)
        
        return ContextSummary(key_info, compressed, offloaded)
```

### 3. Delegation (委托/子代理)

**DeepAgents 提供**:
- 子代理生成 (Subagent Spawning)
- 任务规划 (Task Planning)
- 并行执行 (Parallel Execution)

**AWT 集成**:
```python
# AWT 多代理系统
class AWTAgentSupervisor:
    """AWT 主代理协调器"""
    
    def __init__(self):
        self.explorer_agent = ExplorerAgent()
        self.tester_agent = TesterAgent()
        self.analyzer_agent = AnalyzerAgent()
        
    async def delegate_task(self, task: TestTask):
        """智能任务委托"""
        if task.type == "exploration":
            return await self.explorer_agent.run(task)
        elif task.type == "testing":
            # 并行运行多个测试代理
            results = await asyncio.gather(*[
                self.tester_agent.run(sub_task)
                for sub_task in task.subtasks
            ])
            return results
        elif task.type == "analysis":
            return await self.analyzer_agent.run(task)
```

### 4. Steering (引导/人工干预)

**DeepAgents 提供**:
- 人工审批 (Human Approval)
- 中断和恢复 (Interrupt & Resume)
- 引导决策 (Steering Decisions)

**AWT 集成**:
```python
# AWT 人工引导
class AWTSteering:
    """AWT 人工引导系统"""
    
    async def request_approval(self, action: ProposedAction):
        """请求人工审批"""
        # 显示建议的操作
        await self._show_proposal(action)
        
        # 等待用户反馈
        user_decision = await self._get_user_input()
        
        if user_decision.approved:
            return await self._execute_approved(action)
        else:
            return await self._handle_alternative(user_decision.alternative)
```

---

## 🤖 多代理系统设计

### 1. Supervisor Agent (主代理)

**职责**: 接收用户需求，协调整体测试流程

```python
class SupervisorAgent:
    """AWT 主代理"""
    
    system_prompt = """
    你是一个智能测试主管。你的职责是：
    1. 理解用户的自然语言测试需求
    2. 将需求分解为具体任务
    3. 协调子代理完成任务
    4. 汇总结果并反馈给用户
    """
    
    def __init__(self):
        self.tools = [
            self.delegate_to_explorer,
            self.delegate_to_tester,
            self.delegate_to_analyzer,
            self.request_user_approval
        ]
        
    async def process_test_request(self, user_request: str, url: str):
        """处理用户测试请求"""
        # 1. 理解用户意图
        intent = await self._understand_intent(user_request)
        
        # 2. 委托给探索代理
        page_context = await self.delegate_to_explorer(url, intent)
        
        # 3. 委托给测试代理
        test_results = await self.delegate_to_tester(page_context, intent)
        
        # 4. 如果失败，委托给分析代理
        if test_results.has_failures:
            fixes = await self.delegate_to_analyzer(test_results)
            
        # 5. 汇总结果
        return self._summarize_results(test_results, fixes)
```

### 2. Explorer Agent (探索代理)

**职责**: 探索页面结构，发现可测试功能

```python
class ExplorerAgent:
    """页面探索代理"""
    
    system_prompt = """
    你是一个页面探索专家。你的职责是：
    1. 分析页面结构和功能
    2. 发现可测试的用户路径
    3. 识别关键的交互元素
    4. 构建页面功能图谱
    """
    
    tools = [
        navigate_to_page,
        analyze_page_structure,
        discover_interactive_elements,
        identify_user_journeys,
        build_page_graph
    ]
    
    async def explore_for_testing(self, url: str, test_intent: TestIntent):
        """为测试目的探索页面"""
        # 导航到目标页面
        await self._navigate(url)
        
        # 分析页面结构
        structure = await self._analyze_structure()
        
        # 发现交互元素
        interactive = await self._discover_interactive()
        
        # 基于测试意图，探索相关路径
        relevant_paths = await self._explore_paths(
            structure, 
            interactive, 
            test_intent
        )
        
        return PageContext(
            structure=structure,
            interactive_elements=interactive,
            relevant_paths=relevant_paths
        )
```

### 3. Tester Agent (测试代理)

**职责**: 执行具体测试步骤，验证功能

```python
class TesterAgent:
    """测试执行代理"""
    
    system_prompt = """
    你是一个测试执行专家。你的职责是：
    1. 基于页面上下文设计测试步骤
    2. 智能定位和操作页面元素
    3. 执行测试并验证结果
    4. 记录详细的测试过程
    """
    
    tools = [
        smart_click,      # 智能点击（多层匹配）
        smart_type,       # 智能输入
        smart_navigate,   # 智能导航
        verify_assertion, # 验证断言
        take_screenshot,  # 截图
        wait_for_element  # 等待元素
    ]
    
    async def execute_test(self, page_context: PageContext, test_intent: TestIntent):
        """执行测试"""
        # 基于上下文生成测试计划
        test_plan = await self._generate_test_plan(page_context, test_intent)
        
        results = []
        
        # 执行每个测试步骤
        for step in test_plan.steps:
            try:
                # 智能执行步骤
                result = await self._execute_step(step)
                results.append(result)
                
                # 如果失败，尝试智能恢复
                if not result.success:
                    recovery = await self._attempt_recovery(step, result)
                    if recovery:
                        results.append(recovery)
                        
            except Exception as e:
                results.append(TestResult.failure(step, str(e)))
        
        return TestSummary(results)
```

### 4. Analyzer Agent (分析代理)

**职责**: 分析测试失败，生成修复建议

```python
class AnalyzerAgent:
    """失败分析代理"""
    
    system_prompt = """
    你是一个测试分析专家。你的职责是：
    1. 分析测试失败的根本原因
    2. 判断是测试问题还是应用缺陷
    3. 生成智能修复建议
    4. 如果是应用缺陷，提供代码修复
    """
    
    tools = [
        analyze_failure,
        identify_root_cause,
        generate_test_fix,
        generate_code_fix,
        suggest_alternative_approach
    ]
    
    async def analyze_failure(self, test_result: TestResult):
        """分析测试失败"""
        if test_result.success:
            return AnalysisResult.no_action_needed()
        
        # 1. 分析失败原因
        root_cause = await self._identify_root_cause(test_result)
        
        # 2. 判断失败类型
        failure_type = self._classify_failure(root_cause)
        
        # 3. 生成修复方案
        if failure_type == "test_issue":
            fix = await self._generate_test_fix(test_result, root_cause)
        elif failure_type == "app_bug":
            fix = await self._generate_code_fix(test_result, root_cause)
        else:
            fix = await self._suggest_alternative(test_result, root_cause)
        
        return AnalysisResult(
            root_cause=root_cause,
            failure_type=failure_type,
            suggested_fix=fix,
            confidence=self._calculate_confidence(root_cause)
        )
```

---

## 🛠️ 工具系统设计

### AWT 工具集

```python
# AWT 工具定义
awt_tools = [
    # 导航工具
    Tool(
        name="smart_navigate",
        description="智能导航到指定URL，支持等待页面加载完成",
        function=smart_navigate,
        schema={
            "url": str,
            "wait_for_load": bool,
            "timeout": int
        }
    ),
    
    # 元素定位工具
    Tool(
        name="locate_element",
        description="使用多层匹配策略定位页面元素（OCR、视觉、CSS选择器）",
        function=locate_element,
        schema={
            "target_description": str,
            "matching_strategy": str,  # "hybrid", "ocr", "vision", "selector"
            "timeout": int
        }
    ),
    
    # 智能点击工具
    Tool(
        name="smart_click",
        description="智能点击元素，支持贝塞尔曲线移动模拟真人操作",
        function=smart_click,
        schema={
            "target": str,
            "humanize": bool,
            "double_click": bool
        }
    ),
    
    # 智能输入工具
    Tool(
        name="smart_type",
        description="智能输入文本，支持变速输入模拟真人",
        function=smart_type,
        schema={
            "target": str,
            "text": str,
            "humanize": bool,
            "clear_first": bool
        }
    ),
    
    # 断言验证工具
    Tool(
        name="verify_assertion",
        description="验证断言条件，支持多种验证类型",
        function=verify_assertion,
        schema={
            "assertion_type": str,  # "text_visible", "url_contains", "element_exists"
            "expected_value": str,
            "timeout": int
        }
    ),
    
    # 页面分析工具
    Tool(
        name="analyze_page",
        description="分析当前页面结构，提取关键信息",
        function=analyze_page,
        schema={
            "analysis_depth": str,  # "basic", "detailed", "full"
            "include_hidden": bool
        }
    ),
    
    # 截图工具
    Tool(
        name="take_screenshot",
        description="截图保存，支持多种格式和区域选择",
        function=take_screenshot,
        schema={
            "filename": str,
            "full_page": bool,
            "element_selector": str
        }
    ),
    
    # 控制台检查工具
    Tool(
        name="check_console",
        description="检查浏览器控制台错误和警告",
        function=check_console,
        schema={
            "level": str,  # "error", "warning", "all"
            "clear_after_check": bool
        }
    )
]
```

---

## 📅 实现路线图

### Phase 1: DeepAgents 集成 (2-3周)

**目标**: 建立基于 DeepAgents 的基础架构

```bash
# Week 1: 环境搭建
- 安装 DeepAgents (Python 版本)
- 配置开发环境
- 创建基础项目结构
- 集成现有 AWT 组件

# Week 2: 核心代理实现
- 实现 Supervisor Agent
- 实现 Explorer Agent
- 实现 Tester Agent
- 建立代理间通信

# Week 3: 工具系统
- 实现 AWT 工具集
- 集成现有 WebEngine
- 集成现有 Matchers
- 测试基本功能
```

### Phase 2: 智能能力增强 (2-3周)

**目标**: 增强代理的智能决策能力

```bash
# Week 4: 上下文管理
- 实现探索记忆系统
- 实现用户偏好学习
- 实现上下文压缩和卸载
- 优化 token 使用

# Week 5: 智能决策
- 实现失败分析和恢复
- 实现智能重试策略
- 实现动态测试调整
- 人工引导系统

# Week 6: 交互系统
- 实现对话式界面
- 实现实时反馈
- 实现进度可视化
- 用户输入处理
```

### Phase 3: CLI 集成 (1周)

**目标**: 集成到现有 AWT CLI

```bash
# Week 7: CLI 集成
- 新增 `aat agent` 命令
- 支持 `--interactive` 模式
- 支持 `--autonomous` 模式
- 集成现有配置系统
```

### Phase 4: 完善和优化 (1-2周)

**目标**: 完善功能，优化性能

```bash
# Week 8: 功能完善
- 添加高级功能
- 性能优化
- 错误处理
- 文档完善

# Week 9: 测试和发布
- 集成测试
- 性能测试
- 文档完善
- 发布准备
```

---

## 💻 代码示例

### 示例 1: 基础代理创建

```python
# src/aat/agent/supervisor.py
from langchain.agents import create_agent
from deepagents import (
    create_filesystem_middleware,
    create_subagent_middleware,
    StateBackend
)

from aat.agent.tools import awt_tools
from aat.agent.subagents import explorer_agent, tester_agent, analyzer_agent

class AWTSupervisorAgent:
    """AWT 智能测试主管代理"""
    
    def __init__(self, config: AWTConfig):
        self.backend = StateBackend()
        
        # 创建主管代理
        self.agent = create_agent(
            model=config.ai_model,
            tools=awt_tools,
            middleware=[
                create_filesystem_middleware({ "backend": self.backend }),
                create_subagent_middleware({
                    "defaultModel": config.ai_model,
                    "defaultTools": awt_tools,
                    "subagents": [
                        explorer_agent.config,
                        tester_agent.config,
                        analyzer_agent.config
                    ]
                })
            ],
            system_prompt=self._get_supervisor_prompt()
        )
    
    def _get_supervisor_prompt(self) -> str:
        return """
        你是一个智能测试主管。你的职责是：
        1. 理解用户的自然语言测试需求
        2. 协调子代理完成测试任务
        3. 分析测试结果并提供反馈
        4. 在需要时请求用户指导
        
        工作流程：
        - 接收用户测试需求
        - 委托 Explorer Agent 探索页面
        - 委托 Tester Agent 执行测试
        - 委托 Analyzer Agent 分析失败
        - 汇总结果并反馈给用户
        """
    
    async def test_from_natural_language(
        self, 
        user_request: str, 
        start_url: str,
        mode: str = "interactive"
    ) -> TestResult:
        """从自然语言执行测试"""
        
        # 构建测试任务
        task = TestTask(
            description=user_request,
            start_url=start_url,
            mode=mode
        )
        
        # 执行代理任务
        result = await self.agent.ainvoke({
            "input": f"""
            测试需求：{user_request}
            起始URL：{start_url}
            模式：{mode}
            
            请协调子代理完成这个测试任务。
            """
        })
        
        return TestResult.parse(result)
```

### 示例 2: 子代理配置

```python
# src/aat/agent/subagents/explorer.py
from langchain.agents import tool
from aat.engine import WebEngine
from aat.matchers import HybridMatcher

@tool
async def explore_page_structure(url: str) -> PageStructure:
    """探索页面结构"""
    engine = WebEngine()
    await engine.navigate(url)
    
    structure = await engine.analyze_page()
    return structure

@tool
async def discover_interactive_elements(structure: PageStructure) -> List[InteractiveElement]:
    """发现交互元素"""
    matcher = HybridMatcher()
    elements = await matcher.discover_elements(structure)
    return elements

# Explorer Agent 配置
explorer_agent = {
    "name": "explorer",
    "description": "页面探索专家，负责分析和发现可测试功能",
    "system_prompt": """
    你是一个页面探索专家。你的职责是：
    1. 分析页面结构和功能
    2. 发现可测试的用户路径
    3. 识别关键的交互元素
    4. 构建页面功能图谱
    """,
    "tools": [explore_page_structure, discover_interactive_elements],
    "model": "anthropic:claude-sonnet-4-6",
    "middleware": []
}
```

### 示例 3: 智能工具实现

```python
# src/aat/agent/tools/smart_click.py
from langchain.agents import tool
from aat.engine import WebEngine
from aat.matchers import HybridMatcher
from aat.agent.humanizer import Humanizer

@tool
async def smart_click(
    target_description: str,
    humanize: bool = True,
    timeout: int = 10000
) -> ClickResult:
    """
    智能点击工具
    
    Args:
        target_description: 目标元素的描述
        humanize: 是否模拟真人操作
        timeout: 超时时间(毫秒)
    
    Returns:
        ClickResult: 点击结果
    """
    # 获取浏览器实例
    engine = WebEngine()
    
    # 使用多层匹配策略定位元素
    matcher = HybridMatcher()
    element = await matcher.locate(
        target_description,
        timeout=timeout
    )
    
    if not element:
        return ClickResult.failure(f"无法找到元素: {target_description}")
    
    # 模拟真人操作
    if humanize:
        humanizer = Humanizer()
        await humanizer.move_to_element(element)
        await humanizer.human_pause()
    
    # 执行点击
    await element.click()
    
    # 等待页面响应
    await engine.wait_for_navigation()
    
    return ClickResult.success(
        element=element,
        screenshot=await engine.take_screenshot()
    )
```

### 示例 4: CLI 集成

```python
# src/aat/cli/agent.py
import typer
import asyncio
from aat.agent.supervisor import AWTSupervisorAgent
from aat.config import get_config

app = typer.Typer()

@app.command()
def agent(
    description: str = typer.Argument(..., help="自然语言测试描述"),
    url: str = typer.Option(..., "--url", help="起始URL"),
    mode: str = typer.Option("interactive", "--mode", help="interactive|autonomous"),
    model: str = typer.Option(None, "--model", help="AI模型")
):
    """智能代理测试 - 从自然语言到测试结果"""
    
    async def run_agent():
        # 获取配置
        config = get_config()
        if model:
            config.ai_model = model
        
        # 创建代理
        supervisor = AWTSupervisorAgent(config)
        
        # 执行测试
        result = await supervisor.test_from_natural_language(
            user_request=description,
            start_url=url,
            mode=mode
        )
        
        # 显示结果
        display_test_result(result)
    
    # 运行代理
    asyncio.run(run_agent())
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装 DeepAgents
pip install deepagents langchain langgraph

# 或使用 Node.js 版本
npm install deepagents
```

### 2. 创建第一个智能测试

```python
# examples/quickstart.py
from aat.agent.supervisor import AWTSupervisorAgent
from aat.config import AWTConfig

async def main():
    # 创建配置
    config = AWTConfig(
        ai_model="anthropic:claude-sonnet-4-6"
    )
    
    # 创建代理
    supervisor = AWTSupervisorAgent(config)
    
    # 执行测试
    result = await supervisor.test_from_natural_language(
        user_request="测试用户登录功能，包括验证错误处理",
        start_url="http://localhost:3000/login",
        mode="interactive"
    )
    
    # 查看结果
    print(result.summary())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 3. 运行测试

```bash
# 使用 CLI
aat agent "测试用户注册流程" --url http://localhost:3000 --interactive

# 或使用 Python 脚本
python examples/quickstart.py
```

---

## 📊 预期效果

### 对比: 传统 AWT vs Smart Agent

| 特性 | 传统 AWT | Smart Agent |
|------|----------|-------------|
| **输入方式** | YAML 文件 | 自然语言 |
| **测试生成** | 手动编写 | AI 自动生成 |
| **失败处理** | 手动修复 | AI 智能修复 |
| **探索能力** | 手动扫描 | 自动智能探索 |
| **学习能力** | 静态匹配器 | 动态学习记忆 |
| **交互方式** | 批处理 | 对话式 |
| **适应性** | 需要更新 YAML | 自动适应变化 |

### 性能指标

```
测试效率提升: 3-5x (自动化 vs 手动编写)
失败恢复率: 70-85% (AI 智能修复)
探索覆盖率: 40-60% (智能探索 vs 手动设计)
维护成本: 降低 60-80% (自修复能力)
```

---

## 🎯 成功指标

### 技术指标
- [ ] 支持 90% 的现有 AWT 测试场景
- [ ] 智能探索覆盖率 >50%
- [ ] 失败自动修复率 >70%
- [ ] 响应时间 <30秒/页面

### 用户体验指标
- [ ] 自然语言理解准确率 >85%
- [ ] 用户满意度 >4.0/5.0
- [ ] 新用户上手时间 <10分钟

### 商业指标
- [ ] 开源社区 Star 增长 50%
- [ ] 企业试用转化率 >30%
- [ ] 用户留存率 >60%

---

## 🔧 开发计划

### 立即开始 (本周)

1. **环境搭建**
   ```bash
   # 创建开发分支
   git checkout -b feature/smart-agent
   
   # 安装依赖
   pip install deepagents langchain langgraph
   
   # 创建项目结构
   mkdir -p src/aat/agent
   mkdir -p examples/agent
   mkdir -p tests/agent
   ```

2. **概念验证**
   ```python
   # 创建简单的概念验证
   # tests/agent/concept_test.py
   
   async def test_basic_agent():
       """验证基础代理功能"""
       agent = create_simple_agent()
       result = await agent.test("点击登录按钮")
       assert result.success
   ```

3. **设计文档**
   - 完善代理架构
   - 定义工具接口
   - 设计通信协议

### 第一个月目标

- [ ] 完成 DeepAgents 集成
- [ ] 实现基础代理功能
- [ ] 支持简单的测试场景
- [ ] 发布 MVP 版本

### 第二个月目标

- [ ] 完善智能决策
- [ ] 实现上下文管理
- [ ] 优化性能和稳定性
- [ ] 完善文档和示例

---

## 📚 参考资料

- [DeepAgents 文档](https://docs.langchain.com/oss/deepagents)
- [LangChain Agent 文档](https://docs.langchain.com/oss/langchain/agents)
- [LangGraph 文档](https://docs.langchain.com/oss/langgraph)
- [现有 AWT 架构](../ARCHITECTURE.md)

---

**下一步**: 开始实现 Phase 1 - DeepAgents 集成基础架构