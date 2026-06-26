"""
AWT DeepAgent 测试脚本 - 基于 SC-001 用户登录场景

这个脚本演示了如何使用 DeepAgent 执行与 SC-001_successful_user_login.yaml
相同的测试用例，但使用自然语言的方式而不是 YAML 配置。

对应场景：SC-001_successful_user_login.yaml
测试目标：验证用户可以使用正确的凭据登录并访问仪表板
"""

import asyncio
from aat.agent import create_supervisor_from_config


async def test_sc_001_successful_login(browser_display=False, test_url="http://localhost:5173/"):
    """
    测试 SC-001: 成功用户登录

    对应 YAML 步骤：
    1. 导航到登录页面 (http://localhost:5173/)
    2. 输入有效邮箱 (admin@example.com)
    3. 输入有效密码 (changethis)
    4. 点击提交按钮
    5. 等待导航完成
    6. 验证 "User" 文本可见

    Args:
        browser_display: 是否启用浏览器显示模式
        test_url: 测试服务器 URL
    """

    print("🚀 AWT DeepAgent 测试 - SC-001: 成功用户登录")
    print("=" * 60)
    print("对应场景文件: SC-001_successful_user_login.yaml")
    print(f"测试服务器: {test_url}")
    print(f"浏览器模式: {'🌐 显示模式' if browser_display else '🔇 后台模式'}")
    print("=" * 60)

    try:
        # 创建 DeepAgent 主管代理
        supervisor = await create_supervisor_from_config()
        print("✅ DeepAgent 主管代理创建成功")

        # 定义测试任务（自然语言描述）
        test_request = f"""
        测试用户登录功能：

        测试步骤：
        1. 打开登录页面：{test_url}
        2. 在邮箱输入框输入：admin@example.com
        3. 在密码输入框输入：changethis
        4. 点击提交按钮（Submit）
        5. 等待页面导航完成（约2秒）
        6. 验证页面上显示 "User" 文本，表示登录成功

        测试目标：
        - 验证用户可以使用正确的凭据成功登录
        - 确认登录后能正确访问仪表板
        - 检查主要的用户界面元素是否正常显示

        {"重要要求：必须启用浏览器显示模式（headless=false），让我能够看到操作过程。" if browser_display else "请执行这个测试并报告结果。"}

        {"请执行真实的操作，让我看到浏览器中的操作过程。" if browser_display else "如果是演示环境，请详细说明你会如何执行这个测试。"}
        """

        print("\n📝 测试请求:")
        print("-" * 60)
        print(test_request)
        print("-" * 60)

        # 执行测试（自主模式）
        print("\n🤖 DeepAgent 开始执行测试...")
        print("模式: autonomous（自主执行）")
        print("-" * 60)

        result = await supervisor.test_from_natural_language(
            user_request=test_request,
            start_url=test_url,
            mode="autonomous"
        )

        # 显示测试结果
        print("\n" + "=" * 60)
        print("📊 测试结果")
        print("=" * 60)
        print(f"成功状态: {'✅ 成功' if result.success else '❌ 失败'}")
        print(f"完成步骤数: {result.steps_completed}")
        print(f"\n测试摘要:")
        print("-" * 60)
        print(result.summary)
        print("-" * 60)

        if result.failures:
            print(f"\n❌ 失败信息:")
            for failure in result.failures:
                print(f"  - {failure}")

        if result.screenshots:
            print(f"\n📸 生成的截图:")
            for screenshot in result.screenshots:
                print(f"  - {screenshot}")

        # 与原始 YAML 场景对比
        print("\n" + "=" * 60)
        print("📋 与原始 YAML 场景 (SC-001) 的对应关系")
        print("=" * 60)

        yaml_steps = [
            "步骤1: navigate → http://localhost:5173/",
            "步骤2: find_and_type → admin@example.com (邮箱)",
            "步骤3: find_and_type → changethis (密码)",
            "步骤4: find_and_click → Submit 按钮",
            "步骤5: wait → 2000ms",
            "预期: text_visible → 'User' 文本"
        ]

        for i, step in enumerate(yaml_steps, 1):
            print(f"YAML {i}: {step}")

        print("\nDeepAgent 优势:")
        print("  ✅ 使用自然语言描述，更直观")
        print("  ✅ 自动理解测试意图和目标")
        print("  ✅ 智能选择最佳工具和策略")
        print("  ✅ 自动处理错误和重试")
        print("  ✅ 生成详细的测试报告")

        return result.success

    except Exception as e:
        print(f"\n❌ 测试执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_sc_001_interactive_mode():
    """
    交互模式测试 - SC-001
    在关键操作前请求用户确认
    """

    print("\n🎯 交互模式测试 - SC-001")
    print("=" * 60)
    print("此模式在关键操作前会请求用户确认")
    print("=" * 60)

    try:
        supervisor = await create_supervisor_from_config()

        test_request = """
        请测试用户登录功能，但在执行以下关键操作前请求我的确认：
        - 在输入框中输入数据前
        - 点击提交按钮前

        测试环境：http://localhost:5173/
        测试凭据：admin@example.com / changethis
        """

        print("⚠️  注意：交互模式需要人工确认")
        print("在实际运行时，DeepAgent 会在关键步骤暂停并等待确认")

        result = await supervisor.test_from_natural_language(
            user_request=test_request,
            start_url="http://localhost:5173/",
            mode="interactive"
        )

        print(f"\n交互模式测试结果: {'✅ 成功' if result.success else '❌ 失败'}")
        return result.success

    except Exception as e:
        print(f"❌ 交互模式测试失败: {str(e)}")
        return False


async def test_sc_001_conservative_mode():
    """
    保守模式测试 - SC-001
    每个步骤都请求用户确认
    """

    print("\n🛡️  保守模式测试 - SC-001")
    print("=" * 60)
    print("此模式每个步骤都会请求用户确认")
    print("适合对生产环境进行谨慎测试")
    print("=" * 60)

    try:
        supervisor = await create_supervisor_from_config()

        test_request = """
        请以最谨慎的方式测试用户登录功能。
        每个操作步骤都需要我的确认才能执行。

        测试环境：http://localhost:5173/
        """

        print("⚠️  注意：保守模式需要逐步确认")
        print("适合对生产环境进行安全的测试验证")

        result = await supervisor.test_from_natural_language(
            user_request=test_request,
            start_url="http://localhost:5173/",
            mode="conservative"
        )

        print(f"\n保守模式测试结果: {'✅ 成功' if result.success else '❌ 失败'}")
        return result.success

    except Exception as e:
        print(f"❌ 保守模式测试失败: {str(e)}")
        return False


async def compare_yaml_vs_deepagent():
    """
    对比 YAML 方式和 DeepAgent 方式
    """

    print("\n📊 YAML vs DeepAgent 对比分析")
    print("=" * 60)

    comparison = [
        ("配置方式", "YAML 文件", "自然语言描述"),
        ("可读性", "需要理解YAML语法", "直观的中文描述"),
        ("灵活性", "需要修改YAML结构", "直接修改描述文本"),
        ("智能性", "机械执行步骤", "理解意图，智能执行"),
        ("错误处理", "需要预定义错误处理", "自动分析和修复"),
        ("适应性", "固定步骤", "根据实际情况调整"),
        ("维护性", "需要手动更新", "自然语言容易理解"),
        ("学习曲线", "需要学习YAML格式", "无需特殊培训"),
    ]

    print(f"{'维度':<12} {'YAML 方式':<20} {'DeepAgent 方式':<20}")
    print("-" * 60)

    for aspect, yaml_way, agent_way in comparison:
        print(f"{aspect:<12} {yaml_way:<20} {agent_way:<20}")

    print("\n" + "=" * 60)
    print("💡 DeepAgent 的核心优势:")
    print("=" * 60)
    print("1. 🎯 自然语言：用日常语言描述测试意图")
    print("2. 🤖 智能理解：AI 自动理解测试目标和策略")
    print("3. 🔧 自动工具选择：根据情况选择最佳工具")
    print("4. 🛠️ 智能错误处理：自动分析失败原因并尝试修复")
    print("5. 📊 详细报告：生成人类可读的测试报告")
    print("6. 🔄 持续学习：从历史测试中学习和改进")


async def main():
    """主函数：运行所有测试"""
    print("🎯 AWT DeepAgent 测试套件 - SC-001 用户登录场景")
    print("=" * 60)
    print("基于场景文件: SC-001_successful_user_login.yaml")
    print("=" * 60)

    # 运行对比分析
    await compare_yaml_vs_deepagent()

    print("\n" + "=" * 60)
    print("选择测试模式:")
    print("=" * 60)
    print("1. 自主模式测试 (推荐)")
    print("2. 交互模式测试")
    print("3. 保守模式测试")
    print("4. 运行所有模式")
    print("q. 退出")

    try:
        choice = input("\n请选择 (1-4 或 q): ").strip().lower()

        if choice == 'q':
            print("退出测试")
            return
        elif choice == '1':
            success = await test_sc_001_successful_login()
        elif choice == '2':
            success = await test_sc_001_interactive_mode()
        elif choice == '3':
            success = await test_sc_001_conservative_mode()
        elif choice == '4':
            print("\n运行所有模式...")
            results = []
            results.append(("自主模式", await test_sc_001_successful_login()))
            results.append(("交互模式", await test_sc_001_interactive_mode()))
            results.append(("保守模式", await test_sc_001_conservative_mode()))

            print("\n" + "=" * 60)
            print("📊 所有模式测试结果汇总")
            print("=" * 60)
            for mode, success in results:
                status = "✅ 成功" if success else "❌ 失败"
                print(f"{mode}: {status}")

            success = all(result for _, result in results)
        else:
            print("无效选择，运行默认测试")
            success = await test_sc_001_successful_login()

        print("\n" + "=" * 60)
        if success:
            print("🏆 测试完成！DeepAgent 成功执行了 SC-001 场景")
        else:
            print("⚠️  测试遇到问题，请查看错误信息")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试执行出错: {str(e)}")


if __name__ == "__main__":
    print("💡 提示：这个脚本演示了如何用 DeepAgent 替代 YAML 配置")
    print("💡 提示：在实际运行前，确保测试服务器 http://localhost:5173/ 可访问")
    print("💡 提示：可以修改此脚本以适配你的具体测试环境\n")

    asyncio.run(main())