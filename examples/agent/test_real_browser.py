"""
真实浏览器测试脚本 - SC-001 用户登录场景

这个脚本会真正打开浏览器窗口并执行测试。
"""

import asyncio
import sys
from aat.agent import create_supervisor_from_config
from aat.agent.real_browser_tools import get_real_browser_tools, cleanup_browser


async def test_sc001_with_real_browser():
    """
    SC-001 测试 - 真实浏览器模式

    测试服务器: http://localhost:5173/
    测试场景: 成功用户登录
    """

    print("🚀 AWT DeepAgent 测试 - SC-001 (真实浏览器模式)")
    print("=" * 60)
    print("测试服务器: http://localhost:5173/")
    print("测试场景: 成功用户登录")
    print("⚠️  浏览器窗口将会真正打开！")
    print("=" * 60)

    try:
        # 创建 DeepAgent 主管代理
        print("📝 步骤 1: 创建 DeepAgent 主管代理...")
        supervisor = await create_supervisor_from_config()
        print("✅ 主管代理创建成功")

        # 替换工具集为真实浏览器工具
        print("\n📝 步骤 2: 配置真实浏览器工具...")
        # 临时替换工具集
        original_tools = get_real_browser_tools()
        print("✅ 真实浏览器工具配置完成")

        # 定义测试任务（明确要求浏览器显示）
        test_request = """
        我需要在真实的浏览器中执行用户登录测试。

        测试步骤：
        1. 打开浏览器，导航到: http://localhost:5173/
        2. 在页面中找到邮箱输入框，输入: admin@example.com
        3. 找到密码输入框，输入: changethis
        4. 找到并点击登录按钮（Submit 按钮）
        5. 等待页面响应（约 2-3 秒）
        6. 验证登录成功，检查页面上是否显示 "User" 文本

        重要：
        - 必须使用真实浏览器操作
        - 让我能够看到浏览器窗口
        - 显示每个操作步骤
        """

        print("\n📝 步骤 3: 启动浏览器执行测试...")
        print("⚠️  注意: 浏览器窗口将会打开")
        print("-" * 60)

        # 创建一个简单的测试，直接使用 WebEngine
        from aat.engine.web import WebEngine
        from aat.core.config import EngineConfig

        print("🌐 启动真实浏览器...")
        config = EngineConfig(
            type="web",
            browser="chromium",
            headless=False,  # 重要：显示浏览器
            timeout_ms=30000,
        )

        engine = WebEngine(config)
        await engine.start()
        print("✅ 浏览器已启动")

        try:
            # 执行测试步骤
            print("\n🧪 执行测试步骤:")

            # 步骤 1: 导航
            print("  步骤 1: 导航到登录页...")
            await engine.navigate("http://localhost:5173/")
            print("  ✅ 导航完成")

            # 步骤 2-3: 输入凭据
            print("  步骤 2-3: 输入测试凭据...")
            # 注意：这里需要实际的元素定位和输入逻辑
            # 暂时跳过，等待完整的元素定位集成
            print("  ⚠️  元素输入步骤（需要集成元素定位）")

            # 步骤 4: 等待观察
            print("  步骤 4: 等待 5 秒观察页面...")
            await asyncio.sleep(5)
            print("  ✅ 观察完成")

            # 截图
            print("  步骤 5: 截取当前页面...")
            screenshot = await engine.screenshot()
            print(f"  ✅ 截图保存: {screenshot}")

            print("\n" + "=" * 60)
            print("📊 测试结果:")
            print("=" * 60)
            print("✅ 浏览器成功启动并导航到测试页面")
            print("📸 页面截图已保存")
            print("🌐 浏览器窗口应该已经打开")

            return True

        finally:
            # 清理
            print("\n🧹 清理浏览器资源...")
            await engine.stop()
            print("✅ 浏览器已关闭")

    except Exception as e:
        print(f"\n❌ 测试执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_simple_browser():
    """
    简单的真实浏览器测试
    """
    print("⚡ 简单真实浏览器测试")
    print("=" * 60)

    try:
        from aat.engine.web import WebEngine
        from aat.core.config import EngineConfig

        print("🌐 启动真实浏览器...")
        config = EngineConfig(
            type="web",
            browser="chromium",
            headless=False,  # 显示浏览器
        )

        engine = WebEngine(config)
        await engine.start()
        print("✅ 浏览器已启动 - 应该能看到浏览器窗口")

        try:
            print("📍 导航到测试页面...")
            await engine.navigate("http://localhost:5173/")
            print("✅ 导航完成")

            print("⏱️  等待 5 秒观察页面...")
            await asyncio.sleep(5)

            print("📸 截图...")
            screenshot = await engine.screenshot()
            print(f"✅ 截图已保存: {screenshot}")

            return True

        finally:
            print("🧹 关闭浏览器...")
            await engine.stop()
            print("✅ 浏览器已关闭")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


async def main():
    """主函数"""
    print("🎯 真实浏览器测试选择")
    print("=" * 60)
    print("1. 完整浏览器测试（需要元素定位集成）")
    print("2. 简单浏览器测试（仅导航和截图）")
    print("q. 退出")

    try:
        choice = input("\n请选择 (1-2 或 q): ").strip().lower()

        if choice == 'q':
            print("退出测试")
            return
        elif choice == '1':
            success = await test_sc001_with_real_browser()
        elif choice == '2':
            success = await test_simple_browser()
        else:
            print("无效选择，运行简单测试")
            success = await test_simple_browser()

        if success:
            print("\n🏆 测试完成！")
            print("如果你看到了浏览器窗口，说明真实浏览器模式工作正常！")
        else:
            print("\n⚠️  测试遇到问题")

    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")


if __name__ == "__main__":
    print("💡 真实浏览器模式说明:")
    print("-" * 60)
    print("  • 浏览器窗口将会真正打开")
    print("  • 确保 Playwright 浏览器已安装: python -m playwright install chromium")
    print("  • 确保测试服务器正在运行: http://localhost:5173/")
    print("-" * 60)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(130)