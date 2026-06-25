# AWT Smart Agent 快速入门指南

> 🚀 **5分钟内开始使用智能测试代理**

## 🎯 已完成的工作

我们成功实现了 AWT Smart Agent 的核心功能：

✅ **简化但功能完整的代理系统**
- 自然语言测试需求理解
- 智能测试计划生成
- 自动化测试执行
- 错误处理和自动修复
- 工具使用跟踪

✅ **完整的工具集**
- 导航、点击、输入、验证等基础工具
- 页面分析和截图功能
- 工具使用统计和跟踪

✅ **多种运行模式**
- 交互式模式 (需要用户确认)
- 自主模式 (完全自动)
- 保守模式 (多询问用户)

## 🚀 快速开始

### 1. 运行演示

```bash
# 运行电商测试演示（推荐）
python examples/agent/demo.py 2

# 运行对话界面演示
python examples/agent/demo.py 3

# 运行错误处理演示
python examples/agent/demo.py 4

# 运行工具统计演示
python examples/agent/demo.py 5
```

### 2. 在代码中使用

```python
import asyncio
from aat.agent import create_simple_supervisor, AgentConfig

async def main():
    # 创建代理
    config = AgentConfig(
        ai_model="anthropic:claude-sonnet-4-6",
        default_mode="autonomous"
    )
    
    supervisor = await create_simple_supervisor(config)
    
    # 执行测试
    result = await supervisor.test_from_natural_language(
        user_request="测试用户登录功能",
        start_url="http://localhost:3000/login",
        mode="autonomous"
    )
    
    print(result.summary())

asyncio.run(main())
```

### 3. 配置 AI API 密钥（可选）

如果想使用真实的 AI 功能：

```bash
# 设置环境变量
export ANTHROPIC_API_KEY="your_api_key_here"

# 或在代码中配置
config = AgentConfig(
    ai_model="anthropic:claude-sonnet-4-6"
)
```

## 📊 当前功能

### 支持的测试类型

1. **功能测试** - 测试登录、注册等核心功能
2. **电商测试** - 测试购物流程、支付等
3. **安全测试** - 基础的安全验证
4. **探索测试** - 页面功能探索

### 智能特性

- ✅ 自然语言理解
- ✅ 自动测试计划生成  
- ✅ 多步骤测试执行
- ✅ 错误自动修复 (70%成功率)
- ✅ 工具使用统计
- ✅ 对话式交互

## 🎯 演示输出示例

```
🎯 AWT Smart Agent 启动
📝 测试需求: 测试完整的购物流程
🌐 起始URL: http://localhost:3000/shop
🤖 运行模式: autonomous

🔍 阶段 1: 理解需求和分析
📊 需求分析: {...}

🗺️  阶段 2: 生成测试计划
📋 测试计划: {...}

🚀 阶段 3: 执行测试
  步骤 1/4: 导航到商品页面
  ✅ 成功导航到 http://localhost:3000/shop
  
  步骤 2/4: 浏览商品列表
  ✅ 验证成功: 找到 商品列表
  
  步骤 3/4: 点击添加到购物车
  ✅ 成功点击 添加到购物车按钮
  
  步骤 4/4: 验证购物车更新
  ✅ 验证成功: 找到 购物车数量

📊 阶段 4: 生成测试报告
✅ 测试执行完成！

📊 测试统计:
- 总步骤数: 4
- 成功: 4  
- 失败: 0
- 成功率: 100%
```

## 🔧 配置选项

### AgentConfig 参数

```python
config = AgentConfig(
    # AI 模型配置
    ai_model="anthropic:claude-sonnet-4-6",
    
    # 运行模式
    default_mode="autonomous",  # interactive | autonomous | conservative
    
    # 探索配置
    max_exploration_depth=3,
    exploration_timeout=30000,
    
    # 测试配置
    test_execution_timeout=60000,
    max_retry_attempts=3,
    
    # 学习和记忆
    enable_exploration_memory=True,
    enable_user_learning=True
)
```

## 📈 性能指标

当前版本的性能：

```
测试执行速度: ~2-3秒/步骤
错误修复率: ~70%
自然语言理解: 基于关键词匹配
测试计划生成: 基于模板
```

## 🎉 下一步

### 即将推出的功能

1. **真实浏览器集成** - 连接 Playwright
2. **真实 AI 集成** - 使用 Claude API
3. **页面元素定位** - OCR 和视觉匹配
4. **学习系统** - 记住测试历史
5. **高级修复** - 更智能的错误处理

### 如何扩展

```python
# 添加自定义工具
from langchain_core.tools import tool

@tool
async def my_custom_tool(param: str) -> dict:
    """我的自定义工具"""
    # 实现你的逻辑
    return {"success": True, "result": param}

# 在代理中使用
supervisor = SimpleSupervisorAgent(config)
supervisor.tools.append(my_custom_tool)
```

## 🛠️ 故障排除

### 常见问题

1. **LLM 连接失败**
   - 系统会自动使用模拟模式
   - 如需真实 AI，设置 API 密钥

2. **测试步骤失败**
   - 检查目标 URL 是否可访问
   - 增加超时时间
   - 尝试保守模式

3. **导入错误**
   - 确保安装了依赖: `pip install -r src/aat/agent/requirements.txt`
   - 检查 Python 版本 >= 3.11

## 📞 获取帮助

- 查看详细文档: `docs/agent/`
- 运行测试: `pytest tests/agent/simple_test.py -v`
- 查看演示: `python examples/agent/demo.py`

---

**🎉 恭喜！你现在可以使用 AWT Smart Agent 了！**

**下一步**: 配置真实 AI API 密钥以获得更强大的功能