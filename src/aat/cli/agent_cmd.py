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

from aat.agent import AgentConfig, clean_response, create_supervisor
from aat.core.config import load_config

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
            # 加载项目配置
            typer.echo("📋 加载项目配置...")
            aat_config = load_config()

            # 显示启动信息
            typer.echo("💬 AWT 对话式测试代理 (Deep Agents)")
            typer.echo("─────────────────────────────────────────────────────────")
            typer.echo("使用 LangChain Deep Agents 框架")
            typer.echo("支持: 虚拟文件系统 | 子代理生成 | 上下文管理")
            typer.echo("输入 'quit' 或 'exit' 退出")
            typer.echo("─────────────────────────────────────────────────────────")

            # 创建 Agent Supervisor (从项目配置读取AI设置)
            typer.echo("\n⚙️  初始化 Agent Supervisor...")

            # 从 AAT 配置创建 AgentConfig
            # headless 由 AgentConfig 默认值决定 (False = 显示浏览器);
            # CLI 不再覆盖此设置，保证配置单向流动。
            agent_config = AgentConfig(
                provider=aat_config.ai.provider,
                model=model or aat_config.ai.model,
                api_key=aat_config.ai.api_key,
                temperature=aat_config.ai.temperature,
                max_tokens=aat_config.ai.max_tokens,
                browser_type=aat_config.engine.browser,
                headless=False,  # 交互式聊天总是显示浏览器
                browser_timeout=aat_config.engine.timeout_ms,
            )

            supervisor = await create_supervisor(config=agent_config)
            typer.echo(
                f"✅ Agent Supervisor 已启动 "
                f"(使用 {agent_config.provider}:{agent_config.model})"
            )
            typer.echo("🌐 浏览器模式: 非无头模式 (可以看到浏览器操作)")

            # 显示 Deep Agents 功能
            typer.echo("\n🤖 Deep Agents 功能:")
            typer.echo("  • 任务规划 - 多步测试自动生成计划并跟踪进度")
            typer.echo("  • 自动子代理生成 - 并行处理复杂任务")
            typer.echo("  • 虚拟文件系统 - 上下文管理和持久化")
            typer.echo("  • 人在回路 - 关键操作需要批准")
            typer.echo("  • 内置工具 - 浏览器操作、页面分析、测试执行")

            typer.echo("")

            # 对话历史 — 让 agent 能理解上下文 (e.g. "再跑一次刚才的测试")
            history: list[dict] = []

            # 对话循环
            try:
                while True:
                    try:
                        user_input = typer.prompt("\n👤 你").strip()

                        if not user_input:
                            continue

                        if user_input.lower() in ["quit", "exit", "q"]:
                            typer.echo("👋 再见！")
                            break

                        typer.echo("🤖 代理正在思考...")

                        try:
                            result = await supervisor.chat_with_plan(
                                user_input, history=history
                            )
                        except Exception as exc:
                            typer.echo(f"❌ 代理调用失败: {exc}")
                            continue

                        response = result.text

                        # 维护对话历史，保留最近 20 轮避免 token 膨胀
                        history.append({"role": "user", "content": user_input})
                        history.append({"role": "assistant", "content": response})
                        if len(history) > 40:
                            history = history[-40:]

                        # 若 agent 用了 write_todos，先展示任务计划进度
                        plan_view = supervisor.render_plan()
                        if plan_view:
                            typer.echo(plan_view)

                        typer.echo(f"🤖 代理: {clean_response(response)}")

                    except KeyboardInterrupt:
                        typer.echo("\n👋 再见！")
                        break
                    except Exception as e:
                        typer.echo(f"❌ 错误: {str(e)}")
            finally:
                await supervisor.cleanup()

        except Exception as e:
            typer.echo(f"❌ 初始化失败: {str(e)}")
            raise typer.Exit(1) from e

    asyncio.run(run_chat())


if __name__ == "__main__":
    agent_app()
