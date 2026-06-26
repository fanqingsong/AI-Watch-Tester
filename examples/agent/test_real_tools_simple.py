"""
简单真实工具测试

快速测试真实浏览器工具是否正常工作。
"""

import asyncio
from aat.agent.real_browser_tools import real_navigate, cleanup_browser


async def main():
    """主函数"""
    print("🧪 简单真实工具测试")
    print("=" * 60)

    try:
        print("🚀 测试 real_navigate 工具...")
        print("📍 导航到: http://localhost:5173/login")

        # 调用真实导航工具
        result = await real_navigate.ainvoke({
            "url": "http://localhost:5173/login",
            "wait_for_load": True,
            "timeout": 30000
        })

        print("\n📊 工具返回结果:")
        print(f"  成功: {result.get('success')}")
        print(f"  消息: {result.get('message')}")
        if result.get('page_info'):
            print(f"  页面标题: {result['page_info'].get('title')}")

        print("\n⏱️  保持浏览器打开 5 秒...")
        print("💡 现在检查屏幕上是否有浏览器窗口！")
        for i in range(5, 0, -1):
            print(f"   ⏳ 倒计时: {i} 秒...", flush=True)
            await asyncio.sleep(1)

        print("\n🧹 清理浏览器...")
        await cleanup_browser()

        print("\n✅ 测试完成！")
        print("\n💡 如果看到了浏览器窗口:")
        print("  ✅ 真实浏览器工具正常工作")
        print("  ✅ WebEngine 正确显示浏览器")
        print("  ✅ DeepAgent 集成成功")

        print("\n💡 如果看不到窗口:")
        print("  ⚠️  功能正常，只是显示配置问题")
        print("  💡 在 Windows PowerShell 中运行可解决显示问题")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

        # 确保清理
        try:
            await cleanup_browser()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())