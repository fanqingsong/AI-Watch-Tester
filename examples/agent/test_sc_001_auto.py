"""
自动化测试脚本 - SC-001 用户登录场景（简化版）

这个脚本会自动运行 SC-001 测试，无需用户交互。
适合用于 CI/CD 或批量测试。

支持浏览器显示模式选项。
"""

import asyncio
import sys
import argparse
from aat.agent import create_supervisor_from_config


async def run_sc_001_test_auto(browser_display=False, test_url="http://localhost:5173/"):
    """
    自动化执行 SC-001 测试

    基于场景文件: SC-001_successful_user_login.yaml

    Args:
        browser_display: 是否启用浏览器显示模式
        test_url: 测试服务器 URL
    """

    print("🚀 AWT DeepAgent 自动化测试 - SC-001: 成功用户登录")
    print("=" * 60)
    print("测试场景: 验证用户可以使用正确凭据登录")
    print(f"测试环境: {test_url}")
    print(f"浏览器模式: {'🌐 显示模式' if browser_display else '🔇 后台模式'}")
    print("=" * 60)

    try:
        # 创建 DeepAgent 主管代理
        print("📝 步骤 1: 创建 DeepAgent 主管代理...")
        supervisor = await create_supervisor_from_config()
        print("✅ 主管代理创建成功")

        # 定义测试任务（基于 YAML 配置）
        test_request = f"""
        测试 SC-001: 成功用户登录

        请按以下步骤执行测试（{"启用浏览器显示模式，让我能看到操作过程" if browser_display else "演示环境，请说明测试计划"}）：

        步骤 1: 导航到登录页面 {test_url}
        步骤 2: 在邮箱输入框输入: admin@example.com
        步骤 3: 在密码输入框输入: changethis
        步骤 4: 点击提交按钮 (Submit)
        步骤 5: 等待 2 秒让页面导航
        步骤 6: 验证页面显示 "User" 文本，确认登录成功

        测试目标：
        - 验证用户认证流程正常工作
        - 确认登录后正确重定向到仪表板
        - 检查用户界面元素正常显示

        {"重要：必须启用浏览器显示模式（headless=false），让我能够看到操作过程。" if browser_display else "如果遇到问题，请分析原因并提供修复建议。"}
        """

        # 执行测试
        print("\n📝 步骤 2: 执行测试任务...")
        print("模式: autonomous（自主执行，无需人工确认）")
        print("-" * 60)

        result = await supervisor.test_from_natural_language(
            user_request=test_request,
            start_url=test_url,
            mode="autonomous"
        )

        # 分析结果
        print("\n" + "=" * 60)
        print("📊 测试结果分析")
        print("=" * 60)

        print(f"测试状态: {'✅ 成功' if result.success else '❌ 失败'}")
        print(f"完成步骤: {result.steps_completed}")
        print(f"失败数量: {len(result.failures)}")
        print(f"截图数量: {len(result.screenshots)}")

        print(f"\n📋 测试摘要:")
        print("-" * 60)
        print(result.summary[:500])  # 显示前500字符
        if len(result.summary) > 500:
            print("...")
        print("-" * 60)

        # 对应 YAML 步骤对比
        print(f"\n📋 与 YAML 场景 (SC-001) 的对应:")
        print("-" * 60)
        yaml_mapping = [
            "YAML步骤1 (navigate) → DeepAgent自动导航",
            "YAML步骤2 (find_and_type) → DeepAgent智能输入邮箱",
            "YAML步骤3 (find_and_type) → DeepAgent智能输入密码",
            "YAML步骤4 (find_and_click) → DeepAgent智能点击提交",
            "YAML步骤5 (wait) → DeepAgent智能等待",
            "YAML预期 (text_visible) → DeepAgent智能验证"
        ]

        for mapping in yaml_mapping:
            print(f"  {mapping}")

        # 退出码
        if result.success:
            print("\n🏆 SC-001 测试成功！")
            return 0
        else:
            print("\n⚠️  SC-001 测试失败")
            if result.failures:
                print("失败原因:")
                for failure in result.failures:
                    print(f"  - {failure}")
            return 1

    except Exception as e:
        print(f"\n❌ 测试执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return 2


async def test_multiple_modes():
    """
    测试多种运行模式
    """
    print("\n🎯 测试多种运行模式")
    print("=" * 60)

    supervisor = await create_supervisor_from_config()

    test_request = "测试用户登录功能：http://localhost:5173/ 使用 admin@example.com / changethis"

    modes = ["autonomous", "interactive", "conservative"]
    results = {}

    for mode in modes:
        print(f"\n测试 {mode} 模式...")
        try:
            result = await supervisor.test_from_natural_language(
                user_request=test_request,
                start_url="http://localhost:5173/",
                mode=mode
            )
            results[mode] = result.success
            print(f"{mode} 模式: {'✅ 成功' if result.success else '❌ 失败'}")
        except Exception as e:
            results[mode] = False
            print(f"{mode} 模式: ❌ 错误 - {str(e)[:50]}...")

    print("\n模式测试结果汇总:")
    for mode, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {mode}")

    return all(results.values())


async def main():
    """主函数"""
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description='AWT DeepAgent 自动化测试 - SC-001')
    parser.add_argument('--browser', '-b', action='store_true',
                       help='启用浏览器显示模式')
    parser.add_argument('--url', '-u', default='http://127.0.0.1:8899/',
                       help='测试服务器 URL (默认: http://127.0.0.1:8899/)')

    args = parser.parse_args()

    print("🎯 AWT DeepAgent 自动化测试套件")
    print("=" * 60)
    print("基于场景: SC-001_successful_user_login.yaml")
    print(f"浏览器模式: {'🌐 显示模式' if args.browser else '🔇 后台模式'}")
    print(f"测试服务器: {args.url}")
    print("=" * 60)

    # 运行主测试
    exit_code = await run_sc_001_test_auto(
        browser_display=args.browser,
        test_url=args.url
    )

    # 可选：运行多模式测试
    if exit_code == 0:
        print("\n" + "=" * 60)
        user_input = input("是否运行多模式测试？(y/n): ").strip().lower()
        if user_input == 'y':
            multi_success = await test_multiple_modes()
            exit_code = 0 if multi_success else 1

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(130)  # 130 是 SIGINT 的标准退出码
    except Exception as e:
        print(f"\n❌ 未预期的错误: {str(e)}")
        sys.exit(1)