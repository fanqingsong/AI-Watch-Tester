"""
简单的真实浏览器测试
"""

import asyncio
from aat.engine.web import WebEngine
from aat.core.config import EngineConfig


async def simple_browser_test():
    """简单的浏览器测试"""
    print("🌐 启动真实浏览器测试")
    print("=" * 60)

    try:
        # 配置 WebEngine
        config = EngineConfig(
            type="web",
            browser="chromium",
            headless=False,  # 显示浏览器
        )

        print("📋 配置:")
        print(f"  浏览器: {config.browser}")
        print(f"  显示模式: {'显示' if not config.headless else '后台'}")
        print("-" * 60)

        # 创建引擎
        engine = WebEngine(config)

        print("🚀 启动浏览器...")
        await engine.start()
        print("✅ 浏览器已启动 - 应该能看到浏览器窗口")

        # 导航到测试页面
        print("📍 导航到测试页面...")
        await engine.navigate("http://localhost:5173/")
        print("✅ 导航完成")

        # 等待观察
        print("⏱️  等待 5 秒观察页面...")
        await asyncio.sleep(5)

        # 截图
        print("📸 截取页面...")
        screenshot = await engine.screenshot()
        print(f"✅ 截图已保存: {screenshot}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if 'engine' in locals():
            print("🧹 关闭浏览器...")
            await engine.stop()
            print("✅ 浏览器已关闭")


if __name__ == "__main__":
    print("💡 真实浏览器测试")
    print("=" * 60)
    print("这个测试会真正打开浏览器窗口")
    print("=" * 60)

    success = asyncio.run(simple_browser_test())

    if success:
        print("\n🏆 测试成功！")
        print("如果你看到了浏览器窗口，说明真实浏览器模式正常工作")
    else:
        print("\n⚠️  测试失败")