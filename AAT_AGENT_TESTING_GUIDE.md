# AAT Agent Testing Guide

## Overview
This guide provides comprehensive testing procedures for the AAT (AI Auto Tester) agent functionality.

## Prerequisites
- AAT installed and configured
- Valid AI provider API keys (ZhipuAI/GLM-4.7 configured by default)
- Python 3.11+ environment
- Active web application for testing (optional)

## Quick Start Test

### 1. Basic Import Test
```bash
# Test that agent modules can be imported
python test_agent_basic.py
```

Expected output:
```
🚀 AAT Agent Basic Functionality Test
==================================================
🧪 Testing agent imports...
✅ Agent command module imported successfully
✅ Agent config imported successfully  
✅ Simple supervisor imported successfully

🧪 Testing agent configuration...
✅ AgentConfig created: zhipuai:glm-4.7
   Mode: AgentMode.INTERACTIVE
   Max retries: 3

🧪 Testing agent tools...
✅ Tools loaded: X tools available
==================================================
📊 Results: 3/3 tests passed
✅ All basic tests passed!
```

## Agent Command Tests

### 2. Help Command Test
```bash
aat agent --help
```

Should display:
- Available subcommands: test, chat, analyze, plan, demo
- Command descriptions and options

### 3. Chat Mode Test (Interactive)
```bash
aat agent chat
```

Test conversation flow:
1. Should start with: "💬 AWT 对话式测试代理"
2. Enter: "你好" (Hello)
3. Should respond with greeting
4. Enter: "quit" to exit

### 4. Analyze Command Test
```bash
# Basic analysis
aat agent analyze https://example.com --depth basic

# Detailed analysis with output
aat agent analyze https://example.com --depth detailed --output analysis.json
```

Expected output:
- Page title
- Interactive elements list
- Navigation links
- Forms found
- Analysis result saved to file if --output specified

### 5. Plan Command Test
```bash
# Generate test plan for authentication
aat agent plan "测试登录功能" --url http://localhost:3000/login --type functional

# Generate e-commerce test plan
aat agent plan "测试购物流程" --url http://localhost:3000 --type ecommerce --output plan.json
```

Expected output:
- Test approach description
- Step-by-step test plan
- Each step with: number, description, action, target, value (if applicable)
- Plan saved to file if --output specified

### 6. Demo Command Test
```bash
# Run demo 1 (basic authentication)
aat agent demo --number 1

# Run demo 2 (e-commerce flow)
aat agent demo --number 2
```

Available demos:
1. Basic authentication test
2. E-commerce shopping flow test
3. Conversational interface
4. Error handling and repair
5. Tool usage statistics

### 7. Test Command Test (Advanced)
```bash
# Natural language test execution
aat agent test "测试登录功能" --url http://localhost:3000/login --mode autonomous

# Conservative mode with retries
aat agent test "测试注册功能" --url http://localhost:3000/register --mode conservative --retries 5

# With output file
aat agent test "测试搜索功能" --url http://localhost:3000 --output test_result.json
```

Expected output:
- Start information with test description and URL
- Execution progress
- Final test results with:
  - Success/failure status
  - Steps completed count
  - List of failures (if any)
  - Screenshots captured
  - Result saved to file if --output specified

## Configuration Tests

### 8. Config File Verification
```bash
# Check current configuration
cat aat.config.yaml
```

Verify:
- AI provider: zhipuai
- Model: glm-4.7
- API key is present
- Engine settings configured
- Browser settings present

## Advanced Testing

### 9. Agent Supervisor Test
```python
# Create a test script: test_supervisor.py
import asyncio
from aat.agent.simple_supervisor import create_simple_supervisor
from aat.agent.config import AgentConfig, AgentMode

async def test_supervisor():
    config = AgentConfig(
        ai_model="zhipuai:glm-4.7",
        default_mode=AgentMode.INTERACTIVE
    )
    
    supervisor = await create_simple_supervisor(config)
    
    # Test intent understanding
    intent = await supervisor._understand_intent("测试登录功能")
    print(f"✅ Intent understood: {intent}")
    
    # Test chat functionality
    response = await supervisor.chat("你好，请帮我测试登录页面")
    print(f"✅ Chat response: {response}")

asyncio.run(test_supervisor())
```

### 10. Tools Integration Test
```python
# Test individual agent tools
import asyncio
from aat.agent.simple_tools import get_simple_tools

async def test_tools():
    tools = get_simple_tools()
    print(f"✅ Available tools: {len(tools)}")
    
    # Test navigation tool
    nav_tool = next(t for t in tools if t.name == "smart_navigate")
    result = await nav_tool.ainvoke({"url": "https://example.com"})
    print(f"✅ Navigation test: {result['success']}")

asyncio.run(test_tools())
```

## Integration Testing

### 11. End-to-End Test Flow
```bash
# Complete test workflow
# 1. Analyze a page
aat agent analyze https://example.com --depth detailed --output analysis.json

# 2. Generate test plan
aat agent plan "测试用户注册流程" --url https://example.com/register --output plan.json

# 3. Execute test (when ready)
aat agent test "测试用户注册流程" --url https://example.com/register --mode autonomous --output result.json

# 4. Review results
cat result.json
```

## Troubleshooting

### Common Issues

**Issue 1: Import Errors**
```bash
# Solution: Ensure virtual environment is activated
source .venv/bin/activate
pip install -e .
```

**Issue 2: API Key Problems**
```bash
# Solution: Check API key in config
grep api_key aat.config.yaml
```

**Issue 3: Browser Not Found**
```bash
# Solution: Install Playwright browsers
python -m playwright install chromium
```

**Issue 4: Module Not Found**
```bash
# Solution: Ensure src directory is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

## Test Result Checklist

After testing, verify:
- ✅ All agent commands respond without errors
- ✅ Chat mode maintains conversation context
- ✅ Analyze command produces structured output
- ✅ Plan command generates actionable test steps
- ✅ Demo commands execute successfully
- ✅ Configuration is properly loaded
- ✅ Tools are accessible and functional
- ✅ AI integration works with configured provider

## Next Steps

Once basic tests pass:
1. Test with real web applications
2. Create custom test scenarios
3. Integrate into CI/CD pipeline
4. Monitor AI token usage and costs
5. Collect feedback for improvements

## Support

For issues or questions:
- Check logs: `~/.aat/logs/`
- Review config: `aat.config.yaml`
- Run diagnostics: `aat doctor`
- Check documentation: `docs/AWT_Agent_Skill_Comprehensive_Guide.md`