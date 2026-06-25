"""
AWT CLI Agent Command

将智能测试代理集成到 AWT CLI 系统中
"""

import asyncio
import typer
from typing import Optional
from pathlib import Path

from aat.agent.simple_supervisor import create_simple_supervisor
from aat.agent.config import AgentConfig, AgentMode

# 创建 agent 命令组
agent_app = typer.Typer(help="AWT 智能测试代理命令")


@agent_app.command()
def test(
    description: str = typer.Argument(..., help="自然语言测试描述"),
    url: str = typer.Option(..., "--url", help="起始URL"),
    mode: str = typer.Option("autonomous", "--mode", help="运行模式: interactive|autonomous|conservative"),
    model: Optional[str] = typer.Option(None, "--model", help="AI 模型"),
    retries: int = typer.Option(3, "--retries", help="最大重试次数"),
    output: Optional[str] = typer.Option(None, "--output", help="结果输出文件")
):
    """
    使用智能代理执行测试

    示例:
        aat agent test "测试登录功能" --url http://localhost:3000/login
        aat agent test "测试购物流程" --url http://localhost:3000 --mode autonomous
        aat agent test "测试注册功能" --url http://localhost:3000/register --mode conservative
    """
    async def run_test():
        try:
            # 创建配置
            config = AgentConfig(
                ai_model=model or "anthropic:claude-sonnet-4-6",
                default_mode=AgentMode(mode),
                max_retry_attempts=retries
            )

            # 显示开始信息
            typer.echo(f"🎯 AWT 智能测试代理")
            typer.echo(f"📝 测试需求: {description}")
            typer.echo(f"🌐 起始URL: {url}")
            typer.echo(f"🤖 运行模式: {mode}")
            typer.echo("-" * 50)

            # 创建代理并执行测试
            supervisor = await create_simple_supervisor(config)
            result = await supervisor.test_from_natural_language(
                user_request=description,
                start_url=url,
                mode=mode
            )

            # 显示结果
            typer.echo("\n" + "=" * 50)
            typer.echo("📊 测试结果")
            typer.echo("=" * 50)
            typer.echo(result.summary)

            # 保存结果到文件
            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                import json
                with open(output_path, 'w', encoding='utf-8') as f:
                    if hasattr(result, 'to_dict'):
                        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
                    else:
                        json.dump(result, f, indent=2, ensure_ascii=False, default=str)

                typer.echo(f"\n💾 结果已保存到: {output}")

            # 根据结果设置退出码
            if result.failures:
                raise typer.Exit(1)

        except KeyboardInterrupt:
            typer.echo("\n⏹️  测试被用户中断")
            raise typer.Exit(130)
        except Exception as e:
            typer.echo(f"\n❌ 测试执行出错: {str(e)}")
            raise typer.Exit(1)

    asyncio.run(run_test())


@agent_app.command()
def chat(
    model: Optional[str] = typer.Option(None, "--model", help="AI 模型")
):
    """
    启动对话式测试代理

    示例:
        aat agent chat
        aat agent chat --model anthropic:claude-sonnet-4-6
    """
    async def run_chat():
        try:
            # 创建配置
            config = AgentConfig(
                ai_model=model or "anthropic:claude-sonnet-4-6",
                default_mode=AgentMode.INTERACTIVE
            )

            typer.echo("💬 AWT 对话式测试代理")
            typer.echo("输入 'quit' 或 'exit' 退出")
            typer.echo("-" * 50)

            # 创建代理
            supervisor = await create_simple_supervisor(config)

            # 对话循环
            while True:
                try:
                    user_input = typer.prompt("\n👤 你").strip()

                    if not user_input:
                        continue

                    if user_input.lower() in ['quit', 'exit', 'q']:
                        typer.echo("👋 再见！")
                        break

                    # 获取代理回复
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


@agent_app.command()
def analyze(
    url: str = typer.Argument(..., help="要分析的URL"),
    depth: str = typer.Option("basic", "--depth", help="分析深度: basic|detailed|full"),
    output: Optional[str] = typer.Option(None, "--output", help="分析结果输出文件")
):
    """
    分析页面并生成测试建议

    示例:
        aat agent analyze http://localhost:3000
        aat agent analyze http://localhost:3000 --depth detailed --output analysis.json
    """
    async def run_analyze():
        try:
            from aat.agent.simple_tools import simple_analyze

            typer.echo(f"🔬 分析页面: {url}")
            typer.echo(f"📊 分析深度: {depth}")
            typer.echo("-" * 50)

            # 执行分析 - 使用ainvoke方法
            result = await simple_analyze.ainvoke(depth)

            # 显示结果
            typer.echo("\n📊 页面分析结果:")
            typer.echo("-" * 50)

            analysis = result.get("analysis", {})
            typer.echo(f"页面标题: {analysis.get('page_title', 'N/A')}")

            typer.echo("\n🔘 交互元素:")
            for element in analysis.get('interactive_elements', []):
                typer.echo(f"  - {element.get('type')}: {element.get('text')} ({element.get('id', 'N/A')})")

            typer.echo("\n🔗 导航链接:")
            for nav in analysis.get('navigation', []):
                typer.echo(f"  - {nav.get('text')}: {nav.get('url')}")

            typer.echo("\n📝 表单:")
            for form in analysis.get('forms', []):
                typer.echo(f"  - 表单 {form.get('id')}: {', '.join(form.get('fields', []))}")

            # 保存结果
            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                import json
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                typer.echo(f"\n💾 分析结果已保存到: {output}")

        except Exception as e:
            typer.echo(f"❌ 分析失败: {str(e)}")
            raise typer.Exit(1)

    asyncio.run(run_analyze())


@agent_app.command()
def plan(
    description: str = typer.Argument(..., help="测试需求描述"),
    url: str = typer.Option(..., "--url", help="目标URL"),
    type: str = typer.Option("auto", "--type", help="测试类型: auto|functional|security|ecommerce"),
    output: Optional[str] = typer.Option(None, "--output", help="计划输出文件")
):
    """
    生成测试计划而不执行

    示例:
        aat agent plan "测试登录功能" --url http://localhost:3000/login
        aat agent plan "测试购物流程" --url http://localhost:3000 --type ecommerce --output test_plan.json
    """
    async def run_plan():
        try:
            from aat.agent.simple_supervisor import SimpleSupervisorAgent

            typer.echo(f"📋 生成测试计划")
            typer.echo(f"📝 测试需求: {description}")
            typer.echo(f"🌐 目标URL: {url}")
            typer.echo(f"🎯 测试类型: {type}")
            typer.echo("-" * 50)

            # 创建代理
            config = AgentConfig()
            supervisor = SimpleSupervisorAgent(config)

            # 创建测试上下文
            supervisor.context = await supervisor._understand_intent(description)
            supervisor.context.current_url = url

            # 理解意图
            intent = await supervisor._understand_intent(description)

            # 生成计划
            if type == "auto":
                if "authentication" in intent.target_features:
                    test_plan = supervisor._get_auth_test_plan()
                elif "ecommerce" in intent.target_features:
                    test_plan = supervisor._get_ecommerce_test_plan()
                else:
                    test_plan = supervisor._get_generic_test_plan()
            elif type == "functional":
                test_plan = supervisor._get_auth_test_plan()
            elif type == "ecommerce":
                test_plan = supervisor._get_ecommerce_test_plan()
            else:
                test_plan = supervisor._get_generic_test_plan()

            # 显示计划
            typer.echo(f"\n🎯 测试方法: {test_plan['approach']}")
            typer.echo(f"\n📝 测试步骤:")

            for step in test_plan['steps']:
                typer.echo(f"\n  步骤 {step['step_number']}: {step['description']}")
                typer.echo(f"    动作: {step['action']}")
                typer.echo(f"    目标: {step['target']}")
                if step.get('value'):
                    typer.echo(f"    值: {step['value']}")
                if step.get('needs_confirmation'):
                    typer.echo(f"    需要确认: 是")

            # 保存计划
            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                import json
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(test_plan, f, indent=2, ensure_ascii=False)

                typer.echo(f"\n💾 测试计划已保存到: {output}")

        except Exception as e:
            typer.echo(f"❌ 计划生成失败: {str(e)}")
            raise typer.Exit(1)

    asyncio.run(run_plan())


@agent_app.command()
def demo(
    number: int = typer.Option(1, "--number", "-n", help="演示编号 (1-5)")
):
    """
    运行智能代理演示

    可用演示:
        1 - 基础认证测试
        2 - 电商购物流程测试
        3 - 对话式界面
        4 - 错误处理和修复
        5 - 工具使用统计

    示例:
        aat agent demo
        aat agent demo --number 2
    """
    import subprocess
    import sys

    # 修正路径：从 src/aat/cli/agent_cmd.py 到 examples/agent/demo.py
    current_file = Path(__file__)  # src/aat/cli/agent_cmd.py
    demo_script = current_file.parent.parent.parent.parent / "examples" / "agent" / "demo.py"

    if not demo_script.exists():
        typer.echo(f"❌ 演示脚本不存在: {demo_script}")
        raise typer.Exit(1)

    try:
        result = subprocess.run(
            [sys.executable, str(demo_script), str(number)],
            check=True
        )
        raise typer.Exit(result.returncode)
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ 演示执行失败: {e}")
        raise typer.Exit(e.returncode)
    except KeyboardInterrupt:
        typer.echo("\n⏹️  演示被用户中断")
        raise typer.Exit(130)


if __name__ == "__main__":
    agent_app()