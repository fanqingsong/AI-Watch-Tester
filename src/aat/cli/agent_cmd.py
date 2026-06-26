"""
════════════════════════════════════════════════════════════════════════════════
                   🤖 AWT Smart Agent Command Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
──────────────────────────────────────────────────────────────────────────────
Provides a unified conversational testing interface that coordinates specialized
subagents for different testing tasks (test, analyze, plan, demo).

🎯 USE CASE EXAMPLE
──────────────────────────────────────────────────────────────────────────────
```bash
# Interactive conversational testing (single entry point)
aat agent chat

# Within chat, you can:
# - Request test execution: "Test the login functionality"
# - Request page analysis: "Analyze the current page"
# - Request test planning: "Create a test plan for checkout flow"
# - Request demonstrations: "Show me a demo of navigation testing"
```

⚙️  AGENT ARCHITECTURE
──────────────────────────────────────────────────────────────────────────────
                    ┌────────────────────────────────┐
                    │     UnifiedSupervisor          │
                    │   (Coordination Layer)         │
                    └──────────┬─────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼────┐          ┌─────▼──────┐        ┌─────▼──────┐
   │  Test   │          │  Analyze   │        │   Plan     │
   │  Agent  │          │   Agent    │        │   Agent    │
   │(Subagent)│          │ (Subagent) │        │ (Subagent) │
   └─────────┘          └────────────┘        └────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **chat**: Single conversational interface that coordinates all testing tasks
  - Test execution (via TestAgent subagent)
  - Page analysis (via AnalyzeAgent subagent)
  - Test planning (via PlanAgent subagent)
  - Demonstrations (via DemoAgent subagent)

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Requires valid AI provider configuration (Claude, OpenAI, or ZhipuAI)
- Network connectivity required for AI operations
- All testing functions are now accessed through the chat interface

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Use chat mode as the primary interface for all testing tasks
- The supervisor will automatically route requests to appropriate subagents
- Natural language requests work best for test descriptions
- Use specific, clear descriptions for better results

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Natural language test descriptions without writing YAML
✅ Exploratory testing with AI assistance
✅ Complex page analysis and flow discovery
✅ Test planning and documentation generation
❌ Not for production CI/CD pipelines (use aat run instead)

════════════════════════════════════════════════════════════════════════════════
"""

import asyncio

import typer

from aat.agent import (
    AgentSupervisor,
    create_supervisor,
)

# 创建 agent 命令组
agent_app = typer.Typer(help="AWT 智能测试代理命令")


@agent_app.command()
def chat(model: str | None = typer.Option(None, "--model", help="AI 模型")):
    """
    启动对话式测试代理 (Deep Agents)

    这是唯一的用户入口点，通过自然语言对话协调所有测试功能。
    supervisor 会自动理解用户意图并调用相应的 subagent。

    功能支持:
    - 测试执行: "测试登录功能" / "Test login functionality"
    - 页面分析: "分析当前页面" / "Analyze current page"
    - 测试计划: "生成测试计划" / "Create test plan"
    - 演示示例: "演示导航测试" / "Demo navigation testing"

    Deep Agents 功能:
    - 自动子代理生成 - 并行处理复杂任务
    - 虚拟文件系统 - 上下文管理和持久化
    - 人在回路 - 关键操作需要批准
    - 内置工具 - 浏览器操作、页面分析、测试执行

    示例:
        aat agent chat
        aat agent chat --model anthropic:claude-sonnet-4-6
    """

    async def run_chat():
        try:
            # 显示启动信息
            typer.echo("💬 AWT 对话式测试代理 (Deep Agents)")
            typer.echo("─────────────────────────────────────────────────────────")
            typer.echo("使用 LangChain Deep Agents 框架")
            typer.echo("支持: 虚拟文件系统 | 子代理生成 | 上下文管理")
            typer.echo("输入 'quit' 或 'exit' 退出")
            typer.echo("─────────────────────────────────────────────────────────")

            # 创建 Agent Supervisor
            typer.echo("\n⚙️  初始化 Agent Supervisor...")
            supervisor = await create_supervisor()
            typer.echo("✅ Agent Supervisor 已启动")

            # 显示 Deep Agents 功能
            typer.echo("\n🤖 Deep Agents 功能:")
            typer.echo("  • 自动子代理生成 - 并行处理复杂任务")
            typer.echo("  • 虚拟文件系统 - 上下文管理和持久化")
            typer.echo("  • 人在回路 - 关键操作需要批准")
            typer.echo("  • 内置工具 - 浏览器操作、页面分析、测试执行")

            typer.echo("")

            # 对话循环
            while True:
                try:
                    user_input = typer.prompt("\n👤 你").strip()

                    if not user_input:
                        continue

                    if user_input.lower() in ["quit", "exit", "q"]:
                        typer.echo("👋 再见！")
                        break

                    # 获取代理回复 - supervisor 会自动路由到合适的 subagent
                    typer.echo("🤖 代理正在思考...")
                    response = await supervisor.chat(user_input)
                    typer.echo(f"🤖 代理: {response}")

                except KeyboardInterrupt:
                    typer.echo("\n👋 再见！")
                    break
                except Exception as e:
                    typer.echo(f"❌ 错误: {str(e)}")

        except Exception as e:
            typer.echo(f"❌ 初始化失败: {str(e)}")
            raise typer.Exit(1)

    asyncio.run(run_chat())


if __name__ == "__main__":
    agent_app()
