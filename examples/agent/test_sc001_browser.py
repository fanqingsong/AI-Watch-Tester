"""
SC-001 测试脚本 - 带浏览器显示模式

这个脚本会在真实的浏览器中执行 SC-001 测试，让你可以看到测试过程。
测试服务器: http://127.0.0.1:8899/
"""

import asyncio
import sys
from aat.agent import create_supervisor_from_config


async def test_sc001_with_browser_display():
    """
    SC-001 测试 - 浏览器显示模式

    测试服务器: http://127.0.0.1:8899/
    测试场景: 成功用户登录
    """

    print("🚀 AWT DeepAgent 测试 - SC-001 (浏览器显示模式)")
    print("=" * 60)
    print("测试服务器: http://127.0.0.1:8899/")
    print("测试场景: 成功用户登录")
    print("=" * 60)

    try:
        # 创建 DeepAgent 主管代理
        print("📝 步骤 1: 创建 DeepAgent 主管代理...")
        supervisor = await create_supervisor_from_config()
        print("✅ 主管代理创建成功")

        # 定义测试任务（明确要求浏览器显示）
        test_request = """
        我需要在真实的浏览器中执行用户登录测试，请启用浏览器显示模式。

        测试步骤：
        1. 打开浏览器，导航到: http://127.0.0.1:8899/
        2. 在页面中找到邮箱输入框，输入: admin@example.com
        3. 找到密码输入框，输入: changethis
        4. 找到并点击登录按钮（Submit 按钮）
        5. 等待页面响应（约 2-3 秒）
        6. 验证登录成功，检查页面上是否显示 "User" 文本

        重要要求：
        - 必须启用浏览器显示模式（headless=false）
        - 让我能够看到浏览器操作过程
        - 在关键步骤前暂停一下，方便观察
        - 如果遇到问题，详细描述看到的页面状态

        测试目标：
        - 验证用户认证功能正常工作
        - 确认登录后的界面正常显示
        - 检查主要用户界面元素可访问性

        请执行测试，我会观察浏览器中的操作过程。
        """

        print("\n📝 步骤 2: 配置浏览器显示模式...")
        print("启用: 浏览器可见模式 (headless=false)")
        print("这样你可以看到整个测试过程")

        # 执行测试（交互模式，方便观察）
        print("\n🤖 步骤 3: 启动浏览器执行测试...")
        print("模式: interactive（交互模式，方便观察）")
        print("注意: 浏览器窗口将会打开，执行测试步骤")
        print("-" * 60)

        result = await supervisor.test_from_natural_language(
            user_request=test_request,
            start_url="http://127.0.0.1:8899/",
            mode="interactive"  # 交互模式，适合观察
        )

        # 显示测试结果
        print("\n" + "=" * 60)
        print("📊 测试结果")
        print("=" * 60)
        print(f"测试状态: {'✅ 成功' if result.success else '❌ 失败'}")
        print(f"完成步骤: {result.steps_completed}")

        print(f"\n📋 测试摘要:")
        print("-" * 60)
        # 显示摘要的前 800 个字符
        summary_display = result.summary[:800] if len(result.summary) > 800 else result.summary
        print(summary_display)
        if len(result.summary) > 800:
            print("...")
        print("-" * 60)

        if result.failures:
            print(f"\n❌ 失败信息:")
            for failure in result.failures:
                print(f"  - {failure}")

        if result.screenshots:
            print(f"\n📸 生成的截图:")
            for screenshot in result.screenshots:
                print(f"  - {screenshot}")

        # 浏览器模式特定信息
        print(f"\n🌐 浏览器模式执行信息:")
        print(f"  - 测试服务器: http://127.0.0.1:8899/")
        print(f"  - 浏览器状态: 已启用显示模式")
        print(f"  - 观察方式: 实时浏览器操作")

        return result.success

    except Exception as e:
        print(f"\n❌ 测试执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_browser_modes_comparison():
    """
    对比不同浏览器模式的测试
    """
    print("\n🎯 浏览器模式对比测试")
    print("=" * 60)

    modes = [
        ("autonomous", "自主模式 - 自动执行，适合快速测试"),
        ("interactive", "交互模式 - 关键步骤确认，适合调试"),
        ("conservative", "保守模式 - 每步确认，适合生产验证"),
    ]

    print("可用的浏览器测试模式:")
    for mode, description in modes:
        print(f"  - {mode}: {description}")

    print("\n💡 推荐使用 'interactive' 模式进行浏览器显示测试")
    print("  这样可以清楚地观察测试过程，同时在关键步骤暂停")


async def quick_browser_test():
    """
    快速浏览器测试 - 最简单的版本
    """
    print("⚡ 快速浏览器测试模式")
    print("=" * 60)

    try:
        supervisor = await create_supervisor_from_config()

        # 简化的测试请求
        test_request = """
        在浏览器中测试登录功能：http://127.0.0.1:8899/
        输入 admin@example.com / changethis，验证登录成功
        请启用浏览器显示模式。
        """

        print("启动浏览器测试...")

        result = await supervisor.test_from_natural_language(
            user_request=test_request,
            start_url="http://127.0.0.1:8899/",
            mode="autonomous"
        )

        print(f"\n快速测试结果: {'✅ 成功' if result.success else '❌ 失败'}")
        return result.success

    except Exception as e:
        print(f"❌ 快速测试出错: {str(e)}")
        return False


async def main():
    """主函数"""
    print("🌐 AWT DeepAgent 浏览器显示模式测试")
    print("=" * 60)
    print("测试目标: http://127.0.0.1:8899/")
    print("测试场景: SC-001 成功用户登录")
    print("=" * 60)

    print("\n📋 测试说明:")
    print("  - 测试将在可见的浏览器中执行")
    print("  - 你可以实时观察测试过程")
    print("  - 适合调试和验证测试流程")
    print("  - 确保测试服务器正在运行")

    print("\n" + "=" * 60)
    print("选择测试模式:")
    print("=" * 60)
    print("1. 完整浏览器测试 (推荐)")
    print("2. 快速浏览器测试")
    print("3. 模式对比说明")
    print("q. 退出")

    try:
        choice = input("\n请选择 (1-3 或 q): ").strip().lower()

        if choice == 'q':
            print("退出测试")
            return
        elif choice == '1':
            # 完整浏览器测试
            print("\n🔍 启动完整浏览器测试...")
            print("注意: 浏览器窗口将会打开")

            # 给用户一点时间准备
            print("3秒后开始测试...")
            await asyncio.sleep(1)
            print("2秒后开始测试...")
            await asyncio.sleep(1)
            print("1秒后开始测试...")
            await asyncio.sleep(1)

            success = await test_sc001_with_browser_display()

        elif choice == '2':
            # 快速浏览器测试
            print("\n⚡ 启动快速浏览器测试...")
            success = await quick_browser_test()

        elif choice == '3':
            # 模式对比
            print("\n📊 浏览器模式对比...")
            await test_browser_modes_comparison()
            return

        else:
            print("无效选择，运行默认测试")
            success = await test_sc001_with_browser_display()

        print("\n" + "=" * 60)
        if success:
            print("🏆 浏览器测试完成！")
            print("你应该已经看到浏览器执行了测试步骤")
        else:
            print("⚠️  测试遇到问题")
            print("请检查:")
            print("  1. 测试服务器是否运行: http://127.0.0.1:8899/")
            print("  2. 浏览器驱动是否正确安装")
            print("  3. 网络连接是否正常")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试执行出错: {str(e)}")


if __name__ == "__main__":
    print("💡 浏览器显示模式提示:")
    print("-" * 60)
    print("  • 测试将在可见浏览器中执行")
    print("  • 确保测试服务器正在运行: http://127.0.0.1:8899/")
    print("  • 推荐使用 'interactive' 模式观察测试过程")
    print("  • 测试过程中不要关闭浏览器窗口")
    print("-" * 60)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")
        sys.exit(1)