"""
统一浏览器显示启动器

这个脚本可以为任何 DeepAgent 测试启用浏览器显示模式。
"""

import asyncio
import sys
import argparse
import importlib.util
import os
from pathlib import Path


async def run_test_with_browser(script_name: str, test_url: str = "http://127.0.0.1:8899/"):
    """
    使用浏览器显示模式运行指定的测试脚本

    Args:
        script_name: 测试脚本名称
        test_url: 测试服务器 URL
    """

    print(f"🌐 浏览器显示模式启动器")
    print("=" * 60)
    print(f"测试脚本: {script_name}")
    print(f"测试服务器: {test_url}")
    print(f"浏览器模式: 🌐 显示模式")
    print("=" * 60)

    try:
        # 获取当前脚本目录
        current_dir = Path(__file__).parent

        # 根据脚本名称导入相应的模块
        if "sc_001_auto" in script_name or "auto" in script_name:
            module_path = current_dir / "test_sc_001_auto.py"
            spec = importlib.util.spec_from_file_location("test_sc_001_auto", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            success = await module.run_sc_001_test_auto(browser_display=True, test_url=test_url)

        elif "sc_001_login" in script_name or "login" in script_name:
            module_path = current_dir / "test_sc_001_login.py"
            spec = importlib.util.spec_from_file_location("test_sc_001_login", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            success = await module.test_sc_001_successful_login(browser_display=True, test_url=test_url)

        elif "quickstart" in script_name or "quick" in script_name:
            module_path = current_dir / "quickstart_sc001.py"
            spec = importlib.util.spec_from_file_location("quickstart_sc001", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            success = await module.quick_start(browser_display=True, test_url=test_url)

        elif "basic" in script_name:
            module_path = current_dir / "deepagent_example.py"
            spec = importlib.util.spec_from_file_location("deepagent_example", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            success = await module.basic_test_example(browser_display=True, test_url=test_url)

        else:
            # 默认使用快速开始
            print("使用默认快速开始测试...")
            module_path = current_dir / "quickstart_sc001.py"
            spec = importlib.util.spec_from_file_location("quickstart_sc001", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            success = await module.quick_start(browser_display=True, test_url=test_url)

        return success

    except Exception as e:
        print(f"❌ 测试执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='AWT DeepAgent 浏览器显示模式统一启动器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 使用默认配置运行 SC-001 自动化测试
  python browser_launcher.py --test auto

  # 使用指定 URL 运行快速开始测试
  python browser_launcher.py --test quickstart --url http://127.0.0.1:8899/

  # 运行完整登录测试
  python browser_launcher.py --test login --url http://localhost:5173/
        """
    )

    parser.add_argument(
        '--test', '-t',
        choices=['auto', 'login', 'quickstart', 'basic'],
        default='quickstart',
        help='选择测试类型 (默认: quickstart)'
    )

    parser.add_argument(
        '--url', '-u',
        default='http://127.0.0.1:8899/',
        help='测试服务器 URL (默认: http://127.0.0.1:8899/)'
    )

    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='列出所有可用的测试'
    )

    args = parser.parse_args()

    if args.list:
        print("📋 可用的测试类型:")
        print("=" * 60)
        print("auto       - 自动化测试 (test_sc_001_auto.py)")
        print("login      - 完整登录测试 (test_sc_001_login.py)")
        print("quickstart - 快速开始测试 (quickstart_sc001.py)")
        print("basic      - 基础测试 (deepagent_example.py)")
        print("=" * 60)
        return 0

    print("🎯 AWT DeepAgent 统一浏览器启动器")
    print("=" * 60)
    print("📋 测试配置:")
    print(f"  测试类型: {args.test}")
    print(f"  测试服务器: {args.url}")
    print(f"  浏览器模式: 🌐 显示模式")
    print("=" * 60)

    print("💡 提示: 浏览器窗口将会自动打开")
    print("💡 提示: 你可以实时观察测试执行过程")
    print("💡 提示: 测试过程中请勿关闭浏览器窗口")
    print("-" * 60)

    try:
        success = asyncio.run(run_test_with_browser(args.test, args.url))

        if success:
            print("\n🏆 测试成功完成！")
            print("你应该已经看到浏览器执行了测试步骤")
            return 0
        else:
            print("\n⚠️  测试遇到问题")
            print("请检查:")
            print("  1. 测试服务器是否运行")
            print("  2. 浏览器驱动是否正确安装")
            print("  3. 网络连接是否正常")
            return 1

    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())