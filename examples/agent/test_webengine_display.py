"""
直接 WebEngine 显示测试

验证 WebEngine 的 headless=False 是否真的能显示浏览器窗口。
"""

import asyncio
from aat.engine.web import WebEngine
from aat.core.config import EngineConfig


async def test_webengine_display():
    """测试 WebEngine 显示模式"""
    print("🧪 WebEngine 显示模式测试")
    print("=" * 60)

    try:
        # 配置显示模式的浏览器
        config = EngineConfig(
            type="web",
            browser="chromium",
            headless=False,  # 关键：显示浏览器
            timeout_ms=30000,
        )

        print("📋 配置:")
        print(f"  浏览器: {config.browser}")
        print(f"  显示模式: {'显示' if not config.headless else '后台'}")
        print(f"  超时: {config.timeout_ms}ms")
        print("-" * 60)

        # 创建引擎
        print("🚀 创建 WebEngine...")
        engine = WebEngine(config)

        print("🌐 启动浏览器...")
        await engine.start()
        print("✅ 浏览器已启动")
        print("💡 注意：浏览器窗口现在应该已经打开！")
        print("💡 如果没看到，请检查：")
        print("   - 是否有其他窗口遮挡")
        print("   - 是否在 WSL2 环境（需要 WSLg）")
        print("   - 是否有防火墙阻止")

        try:
            # 导航到测试页面
            print("📍 导航到测试页面...")
            await engine.navigate("http://localhost:5173/")
            print("✅ 导航完成")

            # 保持浏览器打开一段时间
            print("\n⏱️  保持浏览器打开 10 秒让你确认能看到窗口...")
            print("💡 请现在检查屏幕上是否有浏览器窗口")

            for i in range(10, 0, -1):
                print(f"   ⏳ 倒计时: {i} 秒...", flush=True)
                await asyncio.sleep(1)

            # 截图
            print("\n📸 截取页面作为证据...")
            screenshot = await engine.screenshot()
            print(f"✅ 截图已保存: {screenshot}")
            print("💡 查看截图确认页面内容")

            return True

        finally:
            print("\n🧹 关闭浏览器...")
            await engine.stop()
            print("✅ 浏览器已关闭")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("🎯 WebEngine 显示模式验证")
    print("=" * 60)
    print("⚠️  这个测试会直接使用 WebEngine，不经过 DeepAgent")
    print("⚠️  目的是验证 WebEngine 的显示模式是否正常工作")
    print("=" * 60)

    print("\n💡 这个测试会：")
    print("  1. 创建 Chromium 浏览器实例")
    print("  2. 设置 headless=False (显示模式)")
    print("  3. 启动浏览器")
    print("  4. 导航到 http://localhost:5173/")
    print("  5. 保持 10 秒让你确认能看到窗口")
    print("  6. 截图并关闭")

    print("\n⚠️  重要：如果在测试过程中看到浏览器窗口，说明：")
    print("  ✅ WebEngine 显示模式正常")
    print("  ✅ 问题在于 DeepAgent 没有调用 WebEngine")
    print("  ⚠️  需要修复 DeepAgent 的工具调用")

    input("\n按 Enter 开始测试...")

    success = await test_webengine_display()

    if success:
        print("\n🏆 WebEngine 显示测试完成！")
        print("\n💡 如果你看到了浏览器窗口：")
        print("  ✅ WebEngine 显示模式正常")
        print("  ✅ 问题确实是 DeepAgent 工具调用问题")
        print("  🔧 我会修复 DeepAgent 使其使用真实 WebEngine")
        print("\n💡 如果仍然看不到窗口：")
        print("  ⚠️  可能是 WSL2 显示问题")
        print("  💡 建议：")
        print("     1. 安装 WSLg: `wsl --install WSLg`")
        print("     2. 或在 Windows PowerShell 中运行")
    else:
        print("\n⚠️  WebEngine 测试失败")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        print("👋 如果需要重新测试，运行: python examples/agent/test_webengine_display.py")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()