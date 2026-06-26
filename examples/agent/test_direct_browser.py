"""
直接浏览器测试 - 不依赖 AWT 引擎

这个脚本直接使用 Playwright 打开浏览器，避免其他模块的依赖问题。
"""

import asyncio
from playwright.async_api import async_playwright


async def direct_browser_test():
    """直接使用 Playwright 的浏览器测试"""
    print("🌐 直接浏览器测试")
    print("=" * 60)
    print("使用 Playwright 直接打开浏览器")
    print("=" * 60)

    try:
        async with async_playwright() as p:
            print("🚀 启动 Chromium 浏览器...")
            browser = await p.chromium.launch(headless=False)  # 显示浏览器
            print("✅ 浏览器已启动 - 应该能看到浏览器窗口")

            try:
                # 创建页面
                page = await browser.new_page()

                print("📍 导航到测试页面...")
                await page.goto("http://localhost:5173/")
                print("✅ 导航完成")

                print("⏱️  等待 5 秒观察页面...")
                await asyncio.sleep(5)

                print("📸 截取页面...")
                await page.screenshot(path="screenshots/direct_browser_test.png")
                print("✅ 截图已保存: screenshots/direct_browser_test.png")

                print("🎉 测试成功！")
                print("如果你看到了浏览器窗口，说明真实浏览器模式正常工作！")

                return True

            finally:
                print("🧹 关闭浏览器...")
                await browser.close()
                print("✅ 浏览器已关闭")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("💡 直接浏览器模式说明:")
    print("-" * 60)
    print("  • 使用 Playwright 直接打开浏览器")
    print("  • 不依赖 AWT 引擎，避免其他模块问题")
    print("  • 确保测试服务器正在运行: http://localhost:5173/")
    print("  • 确保安装了 Playwright: pip install playwright")
    print("-" * 60)

    print("\n🎯 开始测试")
    print("=" * 60)

    success = await direct_browser_test()

    if success:
        print("\n🏆 测试完成！")
        print("真实浏览器模式工作正常")
    else:
        print("\n⚠️  测试失败，请检查:")
        print("  1. 测试服务器是否运行")
        print("  2. Playwright 是否正确安装")
        print("  3. 网络连接是否正常")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")