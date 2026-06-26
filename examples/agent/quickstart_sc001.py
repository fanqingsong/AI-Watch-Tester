"""
🚀 SC-001 快速开始指南

这是一个最简单的示例，展示如何使用 DeepAgent 执行 SC-001 测试。
只需 3 步即可运行第一个测试！
"""

import asyncio
from aat.agent import create_supervisor_from_config


async def quick_start(browser_display=False, test_url="http://localhost:5173/"):
    """快速开始 - 3 行代码运行测试

    Args:
        browser_display: 是否启用浏览器显示模式
        test_url: 测试服务器 URL
    """

    print("🎯 AWT DeepAgent 快速开始 - SC-001 测试")
    print("=" * 60)
    print(f"测试服务器: {test_url}")
    print(f"浏览器模式: {'🌐 显示模式' if browser_display else '🔇 后台模式'}")
    print("=" * 60)

    # 步骤 1: 创建主管代理
    print("步骤 1: 创建 DeepAgent 主管代理...")
    supervisor = await create_supervisor_from_config()
    print("✅ 代理创建成功")

    # 步骤 2: 定义测试请求
    test_request = f"""
    测试用户登录功能：
    1. 打开 {test_url}
    2. 输入邮箱：admin@example.com
    3. 输入密码：changethis
    4. 点击登录按钮
    5. 验证登录成功（显示 "User" 文本）

    {"请启用浏览器显示模式，让我看到操作过程。" if browser_display else ""}
    """

    # 步骤 3: 执行测试
    print("步骤 2: 执行测试...")
    print("=" * 60)

    result = await supervisor.test_from_natural_language(
        user_request=test_request,
        start_url=test_url,
        mode="autonomous"
    )

    # 显示结果
    print("=" * 60)
    print(f"测试结果: {'✅ 成功' if result.success else '❌ 失败'}")
    print(f"\n摘要:\n{result.summary}")

    return result.success


if __name__ == "__main__":
    print("💡 快速开始指南")
    print("-" * 60)
    print("这个脚本展示了如何用 3 步完成第一个 DeepAgent 测试")
    print("1. 创建主管代理")
    print("2. 定义测试请求（自然语言）")
    print("3. 执行测试并查看结果")
    print("-" * 60)

    try:
        success = asyncio.run(quick_start(browser_display=True, test_url="http://localhost:5173/"))

        if success:
            print("\n🎉 恭喜！你的第一个 DeepAgent 测试成功运行！")
            print("下一步，尝试:")
            print("  - 修改测试请求来测试其他功能")
            print("  - 查看 test_sc_001_login.py 了解更多功能")
            print("  - 阅读 README_SC001.md 了解详细用法")
        else:
            print("\n⚠️  测试失败，但不用担心！")
            print("这可能是正常的，因为:")
            print("  - 测试服务器可能未运行")
            print("  - 测试环境可能与预期不同")
            print("DeepAgent 仍然成功执行了测试流程")

    except Exception as e:
        print(f"\n❌ 执行出错: {str(e)}")
        print("请检查:")
        print("  1. Python 环境是否正确")
        print("  2. 依赖是否安装 (pip install -e .)")
        print("  3. AI 配置是否正确")