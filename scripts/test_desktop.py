"""
Desktop Engine 功能测试脚本
测试 PyAutoGUI + Playwright 混合引擎的基本功能
"""
import asyncio
from pathlib import Path

from aat.core import EngineConfig
from aat.engine.desktop import DesktopEngine


async def test_desktop_engine():
    """测试 DesktopEngine 基本功能"""

    print("🖥️  初始化 DesktopEngine...")
    config = EngineConfig(
        type="desktop",
        browser="chromium",
        viewport_width=1280,
        viewport_height=720,
        window_x=100,
        window_y=100,
    )

    engine = DesktopEngine(config)

    try:
        # 1. 启动引擎
        print("🚀 启动引擎...")
        await engine.start()
        print("✅ 引擎启动成功")

        # 2. 导航到测试页面
        print("🌐 导航到测试页面...")
        await engine.navigate("https://example.com")
        print(f"✅ 当前 URL: {await engine.get_url()}")

        # 3. 截图测试
        print("📸 截取全屏...")
        screenshot_path = Path("test_screenshot.png")
        await engine.save_screenshot(screenshot_path)
        print(f"✅ 截图已保存: {screenshot_path}")

        # 4. 鼠标移动测试
        print("🖱️  移动鼠标...")
        await engine.move_mouse(100, 100)
        await asyncio.sleep(0.5)
        await engine.move_mouse(500, 300)
        print(f"✅ 鼠标位置: {engine.mouse_position}")

        # 5. 文本定位测试
        print("🔍 查找页面文本...")
        text_pos = await engine.find_text_position("Example Domain")
        if text_pos:
            print(f"✅ 找到文本位置: {text_pos}")
        else:
            print("❌ 未找到文本")

        # 6. 键盘输入测试（如果有输入框）
        print("⌨️  键盘输入测试...")
        await engine.press_key("End")
        await asyncio.sleep(0.3)
        print("✅ 键盘操作完成")

        print("\n🎉 所有测试完成!")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理
        print("🧹 清理资源...")
        try:
            await engine.stop()
            print("✅ 引擎已停止")
        except Exception as e:
            print(f"⚠️  停止引擎时出错: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Desktop Engine 功能测试")
    print("=" * 60)
    print()

    try:
        asyncio.run(test_desktop_engine())
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
