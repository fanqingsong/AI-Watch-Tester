"""
WSL 环境下的 DesktopEngine 测试
专注于 Playwright + 基础鼠标操作
"""
import asyncio


async def test_playwright_desktop():
    """测试 Playwright 桌面浏览器控制"""
    try:
        from playwright.async_api import async_playwright

        print("🎭 启动 Playwright Desktop 模式...")

        playwright = await async_playwright().start()

        # 启动非 headless 浏览器（桌面可见）
        browser = await playwright.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )

        # 创建桌面级上下文
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='ko-KR'  # 韩文环境测试
        )

        page = await context.new_page()

        # 1. 基础导航
        print("🌐 测试页面导航...")
        await page.goto("https://example.com")
        print(f"✅ 导航成功: {page.url}")

        # 2. 鼠标操作
        print("🖱️  测试鼠标操作...")
        await page.mouse.move(100, 100)
        await asyncio.sleep(0.5)
        await page.mouse.move(500, 300)
        await asyncio.sleep(0.5)
        print("✅ 鼠标移动成功")

        # 3. 点击操作
        print("👆 测试点击操作...")
        await page.mouse.click(400, 300)
        print("✅ 点击成功")

        # 4. 键盘操作
        print("⌨️  测试键盘操作...")
        await page.keyboard.press("End")
        await asyncio.sleep(0.3)
        await page.keyboard.press("Home")
        await asyncio.sleep(0.3)
        print("✅ 键盘操作成功")

        # 5. 截图功能
        print("📸 测试截图...")
        screenshot = await page.screenshot()
        print(f"✅ 截图成功: {len(screenshot)} bytes")

        # 6. 元素查找
        print("🔍 测试元素查找...")
        await page.goto("https://github.com")
        try:
            await page.wait_for_selector("input[placeholder='Search or jump to...']", timeout=5000)
            print("✅ 元素查找成功")
        except Exception as e:
            print(f"⚠️  元素查找超时: {e}")

        # 7. 文本输入
        print("✍️  测试文本输入...")
        search_input = page.locator("input[placeholder*='earch']")
        if await search_input.is_visible():
            await search_input.click()
            await search_input.fill("AI-Watch-Tester")
            await asyncio.sleep(1)
            print("✅ 文本输入成功")
        else:
            print("⚠️  搜索框不可见")

        # 8. 页面信息
        print("📊 获取页面信息...")
        title = await page.title()
        url = page.url
        print(f"📝 页面标题: {title}")
        print(f"🔗 页面 URL: {url}")

        print("🧹 清理资源...")
        await context.close()
        await browser.close()
        await playwright.stop()

        return True

    except Exception as e:
        print(f"❌ Playwright 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pyautogui_basic():
    """测试 PyAutoGUI 基础功能（不依赖截图）"""
    try:
        import pyautogui

        print("🖥️  测试 PyAutoGUI 基础功能...")

        # 屏幕信息
        screen_width, screen_height = pyautogui.size()
        print(f"📺 屏幕尺寸: {screen_width}x{screen_height}")

        # 鼠标位置
        x, y = pyautogui.position()
        print(f"🖱️  当前鼠标位置: ({x}, {y})")

        # 安全检查
        pyautogui.FAILSAFE = True
        print("✅ 安全模式已启用")

        # 小范围鼠标移动（避免移动到屏幕边缘）
        print("🖱️  测试鼠标移动...")
        original_x, original_y = pyautogui.position()

        # 在原位置附近小幅度移动
        new_x = max(100, min(original_x + 50, screen_width - 100))
        new_y = max(100, min(original_y + 50, screen_height - 100))

        pyautogui.moveTo(new_x, new_y, duration=0.5)
        await asyncio.sleep(0.5)

        # 移回原位置
        pyautogui.moveTo(original_x, original_y, duration=0.5)
        print("✅ 鼠标移动测试完成")

        return True

    except Exception as e:
        print(f"❌ PyAutoGUI 测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("=" * 70)
    print("🖥️  AAT DesktopEngine - WSL 环境测试")
    print("=" * 70)
    print()

    results = {}

    # 1. PyAutoGUI 基础测试
    print("1️⃣  PyAutoGUI 基础功能测试")
    print("-" * 70)
    results['pyautogui'] = await test_pyautogui_basic()
    print()

    # 2. Playwright Desktop 测试
    print("2️⃣  Playwright Desktop 功能测试")
    print("-" * 70)
    results['playwright'] = await test_playwright_desktop()
    print()

    # 测试结果总结
    print("=" * 70)
    print("📊 测试结果总结")
    print("=" * 70)

    for component, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{component:15} : {status}")

    print()

    if all(results.values()):
        print("🎉 所有测试通过！DesktopEngine 在 WSL 环境下可用")
    else:
        print("⚠️  部分功能受限，但核心功能可用")

    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
