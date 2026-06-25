"""
AWT Smart Agent 实际演示

展示智能测试代理的实际工作流程和功能
"""

import asyncio
from aat.agent.simple_supervisor import SimpleSupervisorAgent, create_simple_supervisor
from aat.agent.config import AgentConfig


async def demo_1_basic_auth_test():
    """演示 1: 基础认证测试"""
    print("\n" + "="*70)
    print("🎯 演示 1: 基础认证功能测试")
    print("="*70)

    # 创建代理
    config = AgentConfig(
        ai_model="anthropic:claude-sonnet-4-6",
        default_mode="interactive"
    )

    supervisor = await create_simple_supervisor(config)

    # 执行测试
    result = await supervisor.test_from_natural_language(
        user_request="测试用户登录功能，包括验证错误处理",
        start_url="http://localhost:3000/login",
        mode="conservative"
    )

    # 显示结果
    print("\n" + "="*70)
    print("📊 测试结果")
    print("="*70)
    print(result.summary)

    return result


async def demo_2_ecommerce_test():
    """演示 2: 电商流程测试"""
    print("\n" + "="*70)
    print("🛒 演示 2: 电商购物流程测试")
    print("="*70)

    config = AgentConfig(
        ai_model="anthropic:claude-sonnet-4-6",
        default_mode="autonomous"
    )

    supervisor = await create_simple_supervisor(config)

    result = await supervisor.test_from_natural_language(
        user_request="测试完整的购物流程：浏览商品、添加到购物车、结账",
        start_url="http://localhost:3000/shop",
        mode="autonomous"
    )

    print("\n" + "="*70)
    print("📊 测试结果")
    print("="*70)
    print(result.summary)

    return result


async def demo_3_chat_interface():
    """演示 3: 对话式界面"""
    print("\n" + "="*70)
    print("💬 演示 3: 对话式测试代理")
    print("="*70)

    config = AgentConfig()
    supervisor = await create_simple_supervisor(config)

    # 模拟对话
    conversations = [
        "我想测试登录功能",
        "重点关注错误处理",
        "帮我生成测试计划",
        "如何修复测试失败？"
    ]

    for message in conversations:
        print(f"\n👤 用户: {message}")
        response = await supervisor.chat(message)
        print(f"🤖 代理: {response}")


async def demo_4_error_handling():
    """演示 4: 错误处理和自动修复"""
    print("\n" + "="*70)
    print("🔧 演示 4: 智能错误处理和自动修复")
    print("="*70)

    config = AgentConfig(
        ai_model="anthropic:claude-sonnet-4-6",
        max_retry_attempts=3
    )

    supervisor = await create_simple_supervisor(config)

    # 执行一个可能有错误的测试
    result = await supervisor.test_from_natural_language(
        user_request="测试表单验证功能，包括错误提示",
        start_url="http://localhost:3000/register",
        mode="autonomous"
    )

    print("\n" + "="*70)
    print("📊 测试结果")
    print("="*70)
    print(result.summary)

    if result.failures:
        print("\n❌ 失败的步骤:")
        for failure in result.failures:
            print(f"  - {failure}")
    else:
        print("\n✅ 所有步骤都成功执行！")

    return result


async def demo_5_tool_tracking():
    """演示 5: 工具使用跟踪"""
    print("\n" + "="*70)
    print("📈 演示 5: 工具使用统计和跟踪")
    print("="*70)

    config = AgentConfig()
    supervisor = await create_simple_supervisor(config)

    # 执行一些测试来生成统计数据
    print("\n🔄 执行测试以收集统计数据...")

    result = await supervisor.test_from_natural_language(
        user_request="测试页面导航和基本交互",
        start_url="http://localhost:3000",
        mode="autonomous"
    )

    # 显示工具使用统计
    from aat.agent.simple_tools import tool_tracker

    stats = tool_tracker.get_stats()
    most_used = tool_tracker.get_most_used_tools(3)

    print("\n📊 工具使用统计:")
    print("-" * 50)

    for tool_name, tool_stats in most_used:
        print(f"""
        🔧 {tool_name}:
          - 总调用次数: {tool_stats['total_calls']}
          - 成功率: {(tool_stats['successful_calls']/tool_stats['total_calls']*100):.1f}%
          - 平均执行时间: {tool_stats['avg_time']:.3f}秒
        """)


async def run_all_demos():
    """运行所有演示"""
    print("🚀 AWT Smart Agent 演示程序")
    print("=" * 70)
    print("\n这个演示将展示 AWT Smart Agent 的核心功能：")
    print("1. 自然语言理解")
    print("2. 智能测试计划生成")
    print("3. 自动化测试执行")
    print("4. 错误处理和修复")
    print("5. 对话式交互")

    print("\n⚠️  注意事项:")
    print("- 这是演示版本，使用模拟的工具和响应")
    print("- 实际使用需要配置 AI API 密钥")
    print("- 需要有可访问的测试网站")

    input("\n按 Enter 开始演示...")

    try:
        # 演示 1: 基础测试
        await demo_1_basic_auth_test()

        input("\n按 Enter 继续下一个演示...")

        # 演示 2: 电商测试
        await demo_2_ecommerce_test()

        input("\n按 Enter 继续下一个演示...")

        # 演示 3: 对话界面
        await demo_3_chat_interface()

        input("\n按 Enter 继续下一个演示...")

        # 演示 4: 错误处理
        await demo_4_error_handling()

        input("\n按 Enter 继续下一个演示...")

        # 演示 5: 工具跟踪
        await demo_5_tool_tracking()

        print("\n" + "="*70)
        print("🎉 所有演示完成！")
        print("="*70)

        print("\n📖 下一步:")
        print("1. 配置真实的 AI API 密钥")
        print("2. 集成真实的浏览器操作")
        print("3. 连接到实际的测试网站")
        print("4. 查看完整文档: docs/agent/")

    except KeyboardInterrupt:
        print("\n\n⏹️  演示被用户中断")
    except Exception as e:
        print(f"\n\n❌ 演示出错: {str(e)}")


async def single_demo(demo_number: int):
    """运行单个演示"""
    demos = {
        1: ("基础认证测试", demo_1_basic_auth_test),
        2: ("电商流程测试", demo_2_ecommerce_test),
        3: ("对话式界面", demo_3_chat_interface),
        4: ("错误处理和修复", demo_4_error_handling),
        5: ("工具使用统计", demo_5_tool_tracking)
    }

    if demo_number not in demos:
        print(f"❌ 无效的演示编号: {demo_number}")
        print(f"可用的演示: {', '.join(map(str, demos.keys()))}")
        return

    name, demo_func = demos[demo_number]
    print(f"🎯 运行演示 {demo_number}: {name}")

    try:
        await demo_func()
        print(f"\n✅ 演示 {demo_number} 完成")
    except Exception as e:
        print(f"\n❌ 演示 {demo_number} 出错: {str(e)}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 运行单个演示
        demo_num = int(sys.argv[1])
        asyncio.run(single_demo(demo_num))
    else:
        # 运行所有演示
        asyncio.run(run_all_demos())