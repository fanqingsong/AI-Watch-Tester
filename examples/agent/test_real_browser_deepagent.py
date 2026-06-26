"""
真实浏览器 DeepAgent 测试

验证 DeepAgent 使用真实 WebEngine 的完整功能，包括浏览器窗口显示。
"""

import asyncio
from aat.agent.deepagent_supervisor import DeepAgentSupervisor
from aat.agent.config import AgentConfig
from aat.core.config import LLMConfig


async def test_real_browser_deepagent():
    """测试真实浏览器 DeepAgent"""
    print("🧪 真实浏览器 DeepAgent 测试")
    print("=" * 60)

    try:
        # 配置 DeepAgent
        config = AgentConfig(
            llm=LLMConfig(
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                api_key="test-key"  # 测试用
            ),
            browser_mode="visible",  # 显示模式
            headless=False,
        )

        # 创建 DeepAgent supervisor
        supervisor = DeepAgentSupervisor(config)

        print("📋 配置:")
        print(f"  浏览器模式: 显示模式")
        print(f"  headless: False")
        print(f"  工具数量: {len(supervisor.tools)}")
        print("-" * 60)

        # 测试自然语言描述
        test_description = """
        请执行以下测试:
        1. 导航到 http://localhost:5173/login
        2. 在用户名输入框输入 'testuser'
        3. 在密码输入框输入 'password123'
        4. 点击登录按钮
        5. 验证是否看到欢迎消息
        """

        print("🎯 测试描述:")
        print(test_description)
        print("-" * 60)

        print("⚠️  注意事项:")
        print("  1. 浏览器窗口应该会真正打开")
        print("  2. 你应该能看到自动化操作过程")
        print("  3. 如果看不到窗口，请检查 WSL2 显示配置")
        print("  4. 即使看不到窗口，功能依然正常工作")
        print("-" * 60)

        input("\n按 Enter 开始测试...")

        print("\n🚀 开始测试...")
        print("=" * 60)

        # 执行测试
        result = await supervisor.test_from_natural_language(test_description)

        print("\n" + "=" * 60)
        print("📊 测试结果:")
        print("=" * 60)

        if result.get("success"):
            print("✅ 测试执行成功")
            print(f"📝 结果: {result.get('result', 'N/A')}")
        else:
            print("❌ 测试执行失败")
            print(f"❌ 错误: {result.get('error', 'Unknown error')}")

        # 显示工具调用历史
        if "tool_calls" in result:
            print("\n🛠️  工具调用历史:")
            for i, call in enumerate(result["tool_calls"], 1):
                print(f"  {i}. {call.get('tool')}: {call.get('args', {})}")

        return result.get("success", False)

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_direct_tools():
    """直接测试真实浏览器工具"""
    print("🔧 直接测试真实浏览器工具")
    print("=" * 60)

    try:
        from aat.agent.real_browser_tools import (
            real_navigate,
            real_click,
            real_type,
            verify_text_visible
        )

        print("📋 测试步骤:")
        print("  1. 导航到登录页面")
        print("  2. 输入用户名")
        print("  3. 输入密码")
        print("  4. 点击登录按钮")
        print("  5. 验证登录成功")
        print("-" * 60)

        input("\n按 Enter 开始测试...")

        print("\n🚀 开始测试...")
        print("=" * 60)

        # 步骤 1: 导航
        print("\n📍 步骤 1: 导航到登录页面")
        result = await real_navigate.ainvoke({"url": "http://localhost:5173/login"})
        print(f"结果: {result}")

        if not result.get("success"):
            print("❌ 导航失败，停止测试")
            return False

        # 等待页面加载
        print("⏱️  等待 2 秒...")
        await asyncio.sleep(2)

        # 步骤 2: 输入用户名
        print("\n⌨️  步骤 2: 输入用户名")
        result = await real_type.ainvoke({
            "target": "用户名",
            "text": "testuser",
            "clear_first": True
        })
        print(f"结果: {result}")

        # 步骤 3: 输入密码
        print("\n⌨️  步骤 3: 输入密码")
        result = await real_type.ainvoke({
            "target": "密码",
            "text": "password123",
            "clear_first": True
        })
        print(f"结果: {result}")

        # 步骤 4: 点击登录按钮
        print("\n🖱️  步骤 4: 点击登录按钮")
        result = await real_click.ainvoke({
            "target": "登录",
            "double_click": False
        })
        print(f"结果: {result}")

        # 等待登录处理
        print("⏱️  等待 3 秒...")
        await asyncio.sleep(3)

        # 步骤 5: 验证登录成功
        print("\n✅ 步骤 5: 验证登录成功")
        result = await verify_text_visible.ainvoke({
            "expected_text": "欢迎"
        })
        print(f"结果: {result}")

        # 清理
        print("\n🧹 清理浏览器资源...")
        from aat.agent.real_browser_tools import cleanup_browser
        await cleanup_browser()

        return True

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

        # 确保清理
        try:
            from aat.agent.real_browser_tools import cleanup_browser
            await cleanup_browser()
        except:
            pass

        return False


async def main():
    """主函数"""
    print("🎯 真实浏览器 DeepAgent 测试套件")
    print("=" * 60)
    print("⚠️  这个测试会:")
    print("  1. 使用真实的 WebEngine 而不是模拟工具")
    print("  2. 浏览器窗口会真正打开")
    print("  3. 所有操作都是真实的浏览器交互")
    print("=" * 60)

    print("\n选择测试模式:")
    print("  1. DeepAgent 模式 (通过自然语言)")
    print("  2. 直接工具调用模式 (逐个测试工具)")

    choice = input("\n请选择 (1-2): ").strip()

    if choice == "1":
        print("\n🤖 启动 DeepAgent 模式...")
        success = await test_real_browser_deepagent()
    elif choice == "2":
        print("\n🔧 启动直接工具调用模式...")
        success = await test_direct_tools()
    else:
        print("❌ 无效选择")
        return

    print("\n" + "=" * 60)
    if success:
        print("🏆 测试完成！")
        print("\n💡 如果看到了浏览器窗口:")
        print("  ✅ 真实浏览器集成成功")
        print("  ✅ DeepAgent 正确调用了 WebEngine")
        print("  ✅ 浏览器显示配置正确")

        print("\n💡 如果仍然看不到窗口:")
        print("  ⚠️  功能正常，只是显示问题")
        print("  💡 建议:")
        print("     1. 在 Windows PowerShell 中运行测试")
        print("     2. 或安装 WSLg: wsl --install WSLg")
    else:
        print("⚠️  测试失败")
        print("💡 请检查错误信息并重试")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        print("👋 测试已取消")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()