"""
可见浏览器测试 - 确保浏览器窗口可见

这个脚本会打开浏览器并保持足够长的时间让你看到。
"""

import asyncio
import sys
from playwright.async_api import async_playwright


async def visible_browser_test():
    """确保浏览器可见的测试"""
    print("🌐 可见浏览器测试")
    print("=" * 60)
    print("⚠️  重要：浏览器窗口将会打开并保持一段时间")
    print("⚠️  请不要关闭浏览器窗口")
    print("=" * 60)

    try:
        async with async_playwright() as p:
            print("🚀 启动 Chromium 浏览器...")
            print("💡 提示：浏览器窗口应该在屏幕上出现")

            browser = await p.chromium.launch(
                headless=False,  # 显示浏览器
                args=[
                    '--start-maximized',  # 最大化窗口
                    '--disable-blink-features=---animations'  # 禁用动画，更清晰
                ]
            )
            print("✅ 浏览器已启动")
            print("💡 如果没有看到浏览器窗口，可能是：")
            print("   - 窗口在其他桌面空间")
            print("   - 浏览器在后台运行")
            print("   - 需要检查显示设置")

            try:
                # 创建页面
                page = await browser.new_page()
                viewport = page.viewport_size

                print(f"📋 浏览器信息:")
                print(f"   窗口大小: {viewport}")
                print(f"   用户代理: {await page.evaluate('navigator.userAgent')}")
                print("-" * 60)

                print("📍 导航到测试页面...")
                await page.goto("http://localhost:5173/")
                print("✅ 导航完成")
                print("💡 现在应该能看到浏览器窗口显示的页面")

                # 获取页面信息
                title = await page.title()
                url = page.url
                print(f"📄 页面信息:")
                print(f"   标题: {title}")
                print(f"   URL: {url}")

                print("\n⏱️  保持浏览器打开 10 秒，让你观察...")
                print("💡 请确认你能看到浏览器窗口")

                # 倒计时
                for i in range(10, 0, -1):
                    print(f"   ⏳ 还剩 {i} 秒...", flush=True)
                    await asyncio.sleep(1)

                print("\n📸 截取页面...")
                timestamp = asyncio.get_event_loop().time()
                screenshot_path = f"screenshots/visible_browser_{int(timestamp)}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"✅ 截图已保存: {screenshot_path}")

                print("\n⏱️  再保持 5 秒供最后观察...")
                await asyncio.sleep(5)

                print("\n🎉 测试成功！")
                print("✅ 如果在上述过程中看到了浏览器窗口，说明显示模式正常工作")
                print("✅ 如果没有看到，可能需要检查：")
                print("   - 浏览器窗口是否在其他桌面空间")
                print("   - 显示设置是否正确")
                print("   - 防火墙/安全软件是否阻止了窗口显示")

                return True

            finally:
                print("\n🧹 准备关闭浏览器...")
                print("⏱️  3秒后关闭...")
                await asyncio.sleep(3)
                await browser.close()
                print("✅ 浏览器已关闭")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def check_playwright_installation():
    """检查 Playwright 安装"""
    print("🔍 检查 Playwright 安装...")
    try:
        from playwright.async_api import async_playwright
        print("✅ Playwright Python 包已安装")

        # 检查浏览器
        async with async_playwright() as p:
            browsers = [
                ("Chromium", p.chromium),
                ("Firefox", p.firefox),
                ("WebKit", p.webkit),
            ]

            installed_browsers = []
            for name, browser in browsers:
                try:
                    exec_path = browser.executable_path
                    if exec_path:
                        installed_browsers.append(name)
                        print(f"  ✅ {name}: {exec_path}")
                    else:
                        print(f"  ⚠️  {name}: 未安装")
                except:
                    print(f"  ❌ {name}: 不可用")

            if not installed_browsers:
                print("\n⚠️  没有找到已安装的浏览器")
                print("📦 安装浏览器:")
                print("   python -m playwright install chromium")
                return False

            print(f"\n✅ 找到 {len(installed_browsers)} 个可用浏览器")
            return True

    except ImportError:
        print("❌ Playwright 未安装")
        print("📦 安装 Playwright:")
        print("   pip install playwright")
        print("   python -m playwright install chromium")
        return False
    except Exception as e:
        print(f"❌ 检查失败: {str(e)}")
        return False


async def test_server_connection():
    """测试服务器连接"""
    print("🌐 测试服务器连接...")
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5173/", timeout=5.0)
            print(f"✅ 服务器响应: {response.status_code}")
            return True
    except Exception as e:
        print(f"❌ 服务器连接失败: {str(e)}")
        print("💡 请确保测试服务器正在运行: http://localhost:5173/")
        return False


async def main():
    """主函数"""
    print("🎯 可见浏览器测试程序")
    print("=" * 60)

    # 检查 Playwright
    playwright_ok = await check_playwright_installation()
    if not playwright_ok:
        print("\n⚠️  请先安装 Playwright 和浏览器")
        return

    print("-" * 60)

    # 检查服务器
    server_ok = await test_server_connection()
    if not server_ok:
        print("\n⚠️  请先启动测试服务器")
        return

    print("-" * 60)
    print("\n🎯 开始浏览器可见性测试")
    print("=" * 60)

    # 确认用户准备
    print("⚠️  重要提示:")
    print("  • 浏览器窗口将会打开")
    print("  • 请留意屏幕上的窗口变化")
    print("  • 测试过程约需 20 秒")
    print("  • 测试过程中请勿操作浏览器")

    input("\n按 Enter 键开始测试...")

    success = await visible_browser_test()

    if success:
        print("\n🏆 可见浏览器测试完成！")
        print("\n💡 如果你看到了浏览器窗口，说明显示模式正常")
        print("💡 如果没有看到，建议：")
        print("   1. 检查系统任务栏是否有浏览器进程")
        print("   2. 检查是否有弹窗被阻止")
        print("   3. 尝试手动打开浏览器确认能访问 http://localhost:5173/")
    else:
        print("\n⚠️  测试失败")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        print("👋 再见！")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()