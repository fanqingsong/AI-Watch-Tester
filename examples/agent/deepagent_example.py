"""
AWT DeepAgent Example - 使用官方 DeepAgents 框架的示例

这个示例展示了如何使用基于官方 LangChain DeepAgents 框架的 AWT Smart Agent。
"""

import asyncio
from aat.agent import (
    DeepAgentSupervisor,
    create_supervisor_from_config,
)


async def basic_test_example(browser_display=False, test_url="https://example.com/login"):
    """基础测试示例"""
    print("=" * 60)
    print("AWT DeepAgent 基础测试示例")
    print(f"测试服务器: {test_url}")
    print(f"浏览器模式: {'🌐 显示模式' if browser_display else '🔇 后台模式'}")
    print("=" * 60)

    # 创建 DeepAgent 主管代理（自动从配置文件加载）
    supervisor = await create_supervisor_from_config()

    # 执行自然语言测试
    test_request = f"""
    测试登录功能，验证用户名和密码输入。

    {"请启用浏览器显示模式，让我看到操作过程。" if browser_display else "请执行测试并报告结果。"}
    """

    result = await supervisor.test_from_natural_language(
        user_request=test_request,
        start_url=test_url,
        mode="interactive"
    )

    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果:")
    print("=" * 60)
    print(f"成功: {result.success}")
    print(f"摘要: {result.summary}")
    print(f"完成步骤: {result.steps_completed}")
    if result.failures:
        print(f"失败: {result.failures}")
    if result.screenshots:
        print(f"截图: {result.screenshots}")


async def autonomous_test_example():
    """自主模式测试示例"""
    print("\n" + "=" * 60)
    print("AWT DeepAgent 自主模式测试示例")
    print("=" * 60)

    # 创建代理
    supervisor = await create_supervisor_from_config()

    # 自主模式执行测试
    result = await supervisor.test_from_natural_language(
        user_request="测试购物车功能，验证添加商品和结账流程",
        start_url="https://example.com/shop",
        mode="autonomous"  # 自主模式，减少确认
    )

    print(f"\n自主模式测试结果: {result.success}")


async def conversation_example():
    """对话交互示例"""
    print("\n" + "=" * 60)
    print("AWT DeepAgent 对话交互示例")
    print("=" * 60)

    # 创建代理
    supervisor = await create_supervisor_from_config()

    # 进行对话
    questions = [
        "如何测试一个登录表单？",
        "应该如何处理测试失败？",
        "什么是自主测试模式？"
    ]

    for question in questions:
        print(f"\n问题: {question}")
        answer = await supervisor.chat(question)
        print(f"回答: {answer}")


async def multi_mode_example():
    """多模式对比示例"""
    print("\n" + "=" * 60)
    print("AWT DeepAgent 多模式对比测试")
    print("=" * 60)

    supervisor = await create_supervisor_from_config()

    modes = ["interactive", "autonomous", "conservative"]
    test_request = "测试用户注册功能"

    for mode in modes:
        print(f"\n--- {mode.upper()} 模式 ---")
        result = await supervisor.test_from_natural_language(
            user_request=test_request,
            start_url="https://example.com/register",
            mode=mode
        )
        print(f"模式 {mode}: {result.success}")


async def error_handling_example():
    """错误处理示例"""
    print("\n" + "=" * 60)
    print("AWT DeepAgent 错误处理示例")
    print("=" * 60)

    try:
        # 创建代理
        supervisor = await create_supervisor_from_config()

        # 模拟可能出错的测试
        result = await supervisor.test_from_natural_language(
            user_request="测试一个不存在的功能",
            start_url="https://example.com",
            mode="autonomous"
        )

        if not result.success:
            print(f"测试失败，但代理正常处理: {result.summary}")
            print(f"失败信息: {result.failures}")

    except Exception as e:
        print(f"捕获到异常: {str(e)}")
        print("DeepAgent 优雅地处理了错误情况")


async def custom_config_example():
    """自定义配置示例"""
    print("\n" + "=" * 60)
    print("AWT DeepAgent 自定义配置示例")
    print("=" * 60)

    from aat.agent import AgentConfig, DeepAgentSupervisor

    # 创建自定义配置
    config = AgentConfig(
        ai_model="anthropic:claude-sonnet-4-6",
        default_mode="autonomous",
        max_exploration_depth=5,
        exploration_timeout=60000,
        test_execution_timeout=120000,
        max_retry_attempts=5,
    )

    # 使用自定义配置创建代理
    supervisor = DeepAgentSupervisor(config)
    await supervisor.initialize()

    result = await supervisor.test_from_natural_language(
        user_request="测试页面导航功能",
        start_url="https://example.com",
        mode="autonomous"
    )

    print(f"使用自定义配置的测试结果: {result.success}")


async def tool_exploration_example():
    """工具探索示例"""
    print("\n" + "=" * 60)
    print("AWT DeepAgent 工具系统探索")
    print("=" * 60)

    from aat.agent import (
        get_awt_deepagent_tools,
        get_navigation_tools,
        get_interaction_tools,
        get_verification_tools,
        get_analysis_tools,
        get_tools_by_category
    )

    # 查看所有可用工具
    all_tools = get_awt_deepagent_tools()
    print(f"\n总工具数: {len(all_tools)}")
    print("可用工具:")
    for tool in all_tools:
        print(f"  - {tool.name}: {tool.description}")

    # 按类别查看工具
    print("\n按类别组织的工具:")
    categories = {
        "导航工具": get_navigation_tools,
        "交互工具": get_interaction_tools,
        "验证工具": get_verification_tools,
        "分析工具": get_analysis_tools
    }

    for category_name, get_tools_func in categories.items():
        tools = get_tools_func()
        print(f"\n{category_name} ({len(tools)} 个):")
        for tool in tools:
            print(f"  - {tool.name}")


async def main():
    """运行所有示例"""
    print("🚀 AWT DeepAgent 示例程序")
    print("=" * 60)
    print("这个程序展示了基于官方 LangChain DeepAgents 框架的 AWT Smart Agent 功能")
    print("=" * 60)

    examples = [
        ("基础测试", basic_test_example),
        ("自主模式测试", autonomous_test_example),
        ("对话交互", conversation_example),
        ("多模式对比", multi_mode_example),
        ("错误处理", error_handling_example),
        ("自定义配置", custom_config_example),
        ("工具探索", tool_exploration_example),
    ]

    print("\n可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")

    print("\n选择要运行的示例（输入数字，或 'all' 运行所有，或 'q' 退出）:")
    user_input = input("> ").strip().lower()

    if user_input == 'q':
        print("再见！")
        return
    elif user_input == 'all':
        for name, example_func in examples:
            try:
                print(f"\n📍 运行示例: {name}")
                await example_func()
            except Exception as e:
                print(f"❌ 示例 '{name}' 执行出错: {str(e)}")
    elif user_input.isdigit() and 1 <= int(user_input) <= len(examples):
        idx = int(user_input) - 1
        name, example_func = examples[idx]
        try:
            print(f"\n📍 运行示例: {name}")
            await example_func()
        except Exception as e:
            print(f"❌ 示例执行出错: {str(e)}")
    else:
        print("无效选择，运行基础测试示例")
        await basic_test_example()


if __name__ == "__main__":
    # 运行示例程序
    asyncio.run(main())