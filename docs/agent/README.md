# AWT Smart Agent - 基于 DeepAgents 的智能测试代理

> 🚀 **将 AWT 从 YAML 测试框架升级为智能测试代理系统**

---

## 🎯 项目概述

AWT Smart Agent 是一个革命性的升级，将传统的 AWT 测试框架转变为基于自然语言的智能测试代理系统。用户只需用自然语言描述测试需求，Agent 就能自动探索页面、执行测试、分析失败并提供修复建议。

### 核心特性

- ✅ **自然语言测试**: 用一句话描述测试需求
- 🤖 **智能页面探索**: Agent 自动发现可测试功能
- 🔄 **自主执行测试**: 跨页面多步骤推理测试
- 💡 **智能失败修复**: AI 分析失败并提供修复方案
- 🎭 **对话式交互**: 实时反馈和用户引导
- 🧠 **学习和记忆**: 越用越聪明的测试系统

---

## 🏗️ 架构设计

基于 LangChain DeepAgents 框架的多代理系统：

```
用户自然语言 → Supervisor Agent → 子代理协调 → 测试执行 → 结果反馈
                    ↓
        ┌──────────┼──────────┐
        ↓          ↓          ↓
    Explorer    Tester    Analyzer
     Agent      Agent      Agent
```

### 核心组件

1. **Supervisor Agent**: 主管代理，协调整体测试流程
2. **Explorer Agent**: 探索代理，分析页面结构和功能
3. **Tester Agent**: 测试代理，执行测试步骤和验证
4. **Analyzer Agent**: 分析代理，处理失败并提供修复

---

## 🚀 快速开始

### 安装依赖

```bash
# 安装 DeepAgents 和相关依赖
pip install deepagents langchain langgraph

# 或使用项目 Makefile
make install-agent
```

### 基础使用

```python
from aat.agent.supervisor import create_supervisor
from aat.agent.config import AgentConfig

async def main():
    # 创建代理
    config = AgentConfig(
        ai_model="anthropic:claude-sonnet-4-6"
    )
    supervisor = await create_supervisor(config)

    # 执行测试
    result = await supervisor.test_from_natural_language(
        user_request="测试用户登录功能，包括验证错误处理",
        start_url="http://localhost:3000/login",
        mode="interactive"
    )

    print(result.summary())

asyncio.run(main())
```

### CLI 使用

```bash
# 交互式模式
aat agent "测试登录功能" --url http://localhost:3000 --interactive

# 自主模式
aat agent "测试购物流程" --url http://localhost:3000 --autonomous

# 保守模式（多询问）
aat agent "测试支付流程" --url http://localhost:3000 --conservative
```

---

## 📚 文档结构

```
docs/agent/
├── DEEPAGENTS_IMPLEMENTATION.md  # 详细实现方案
├── README.md                      # 本文件
├── API.md                         # API 参考（待创建）
└── TUTORIAL.md                    # 使用教程（待创建）

src/aat/agent/
├── __init__.py                    # 模块导出
├── supervisor.py                  # 主管代理
├── config.py                      # 配置系统
├── tools/                         # 工具集
│   └── __init__.py
└── subagents/                     # 子代理配置
    └── __init__.py

examples/agent/
└── quickstart.py                  # 快速开始示例
```

---

## 🛠️ 开发状态

### 当前阶段：概念验证 ✅

- [x] 架构设计完成
- [x] 基础代码结构创建
- [x] 工具系统框架建立
- [x] 子代理配置定义
- [x] 示例代码编写

### 下一步：实现 Phase 1

#### Week 1: 环境搭建
```bash
# 安装 DeepAgents
pip install deepagents langchain langgraph

# 配置开发环境
python -m aat.agent.setup
```

#### Week 2-3: 核心实现
- [ ] 集成 DeepAgents 框架
- [ ] 实现 Supervisor Agent
- [ ] 实现子代理通信
- [ ] 集成现有 AWT 组件

#### Week 4: 测试验证
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能测试
- [ ] 文档完善

---

## 🎯 实现路线图

### Phase 1: DeepAgents 集成 (2-3周)
**目标**: 建立基于 DeepAgents 的基础架构

- [ ] 安装和配置 DeepAgents
- [ ] 实现核心代理架构
- [ ] 创建子代理系统
- [ ] 集成现有 AWT 组件
- [ ] 基础功能测试

### Phase 2: 智能能力增强 (2-3周)
**目标**: 增强代理的智能决策能力

- [ ] 实现上下文管理系统
- [ ] 实现探索记忆功能
- [ ] 实现智能失败分析
- [ ] 实现对话式界面
- [ ] 优化性能和稳定性

### Phase 3: CLI 集成 (1周)
**目标**: 集成到现有 AWT CLI

- [ ] 添加 `aat agent` 命令
- [ ] 支持多种运行模式
- [ ] 集成配置系统
- [ ] 完善错误处理

### Phase 4: 完善和优化 (1-2周)
**目标**: 完善功能，优化性能

- [ ] 添加高级功能
- [ ] 性能优化
- [ ] 完善文档
- [ ] 发布准备

---

## 📊 预期效果

### 对比传统 AWT

| 特性 | 传统 AWT | Smart Agent |
|------|----------|-------------|
| 输入方式 | YAML 文件 | 自然语言 |
| 测试生成 | 手动编写 | AI 自动生成 |
| 失败处理 | 手动修复 | AI 智能修复 |
| 探索能力 | 手动扫描 | 自动智能探索 |
| 学习能力 | 静态匹配器 | 动态学习记忆 |
| 交互方式 | 批处理 | 对话式 |

### 性能指标

```
测试效率提升: 3-5x (自动化 vs 手动编写)
失败自动修复率: 70-85%
探索覆盖率: 40-60%
维护成本降低: 60-80%
```

---

## 🔧 技术栈

- **框架**: LangChain DeepAgents
- **AI模型**: Claude Sonnet 4.6 / GPT-4 / 智谱AI
- **浏览器**: Playwright
- **匹配器**: OpenCV + Tesseract + Vision AI
- **语言**: Python 3.11+
- **架构**: 多代理系统 (Multi-Agent)

---

## 🤝 贡献指南

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/ksgisang/AI-Watch-Tester.git
cd AI-Watch-Tester

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
make dev

# 安装 Agent 相关依赖
pip install deepagents langchain langgraph
```

### 开发流程

1. 创建功能分支: `git checkout -b feature/agent-improvement`
2. 进行开发和测试
3. 提交代码: `git commit -m "feat(agent): 添加新功能"`
4. 推送分支: `git push origin feature/agent-improvement`
5. 创建 Pull Request

---

## 📖 参考资料

- [DeepAgents 文档](https://docs.langchain.com/oss/deepagents)
- [LangChain Agent 文档](https://docs.langchain.com/oss/langchain/agents)
- [LangGraph 文档](https://docs.langchain.com/oss/langgraph)
- [AWT 架构文档](../ARCHITECTURE.md)
- [详细实现方案](./DEEPAGENTS_IMPLEMENTATION.md)

---

## 🎉 致谢

感谢 LangChain 团队提供的 DeepAgents 框架，这是实现智能测试代理的关键技术基础。

---

## 📄 许可证

MIT License - 详见 [LICENSE](../../LICENSE)

---

**当前状态**: 🚧 开发中 - 概念验证阶段完成

**下一步**: 开始 Phase 1 实现

**预计完成**: Q3 2026 (7-10周)

---

**让我们一起打造下一代智能测试系统！** 🚀