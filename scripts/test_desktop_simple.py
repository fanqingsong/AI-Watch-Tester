"""
简化的 DesktopEngine 测试
"""
import asyncio

# 测试 PyAutoGUI 基本功能
async def test_pyautogui():
    """测试 PyAutoGUI 基本功能"""
    try:
        import pyautogui

        print("✅ PyAutoGUI 导入成功")

        # 获取屏幕尺寸
        screen_width, screen_height = pyautogui.size()
        print(f"📺 屏幕尺寸: {screen_width}x{screen_height}")

        # 获取当前鼠标位置
        current_x, current_y = pyautogui.position()
        print(f"🖱️  当前鼠标位置: ({current_x}, {current_y})")

        # 测试截图功能
        print("📸 测试截图...")
        screenshot = pyautogui.screenshot()
        print(f"✅ 截图成功: {screenshot.size}")

        # 测试鼠标移动（小范围）
        print("🖱️  测试鼠标移动...")
        pyautogui.moveTo(current_x + 10, current_y + 10, duration=0.5)
        print("✅ 鼠标移动成功")

        return True

    except Exception as e:
        print(f"❌ PyAutoGUI 测试失败: {e}")
        return False


async def test_playwright():
    """测试 Playwright 基本功能"""
    try:
        from playwright.async_api import async_playwright

        print("✅ Playwright 导入成功")

        print("🚀 启动浏览器...")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1280, 'height': 720})
        page = await context.new_page()

        print("🌐 导航到测试页面...")
        await page.goto("https://example.com")
        print(f"✅ 当前 URL: {page.url}")

        print("📸 测试截图...")
        screenshot_bytes = await page.screenshot()
        print(f"✅ 截图成功: {len(screenshot_bytes)} bytes")

        print("🧹 清理资源...")
        await context.close()
        await browser.close()
        await playwright.stop()
        print("✅ Playwright 测试成功")

        return True

    except Exception as e:
        print(f"❌ Playwright 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("=" * 60)
    print("🖥️  Desktop Engine 组件测试")
    print("=" * 60)
    print()

    # 测试 PyAutoGUI
    print("1️⃣  测试 PyAutoGUI...")
    pyautogui_ok = await test_pyautogui()
    print()

    # 测试 Playwright
    print("2️⃣  测试 Playwright...")
    playwright_ok = await test_playwright()
    print()

    # 总结
    print("=" * 60)
    if pyautogui_ok and playwright_ok:
        print("🎉 所有组件测试通过！")
    else:
        print("⚠️  部分测试失败，请检查错误信息")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
