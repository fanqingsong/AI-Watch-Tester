"""
简单的 DeepAgent 测试脚本 - 自动化运行
"""

import asyncio
from aat.agent import (
    create_supervisor_from_config,
    get_awt_deepagent_tools,
    AgentConfig,
    DeepAgentSupervisor
)


async def test_basic_functionality():
    """测试基本功能"""
    print("🧪 测试 1: 基本功能测试")
    print("=" * 60)

    try:
        # 创建主管代理
        supervisor = await create_supervisor_from_config()
        print("✅ 主管代理创建成功")

        # 测试工具加载
        tools = get_awt_deepagent_tools()
        print(f"✅ 工具加载成功，共 {len(tools)} 个工具")

        # 显示工具列表
        print("\n可用工具:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")

        return True

    except Exception as e:
        print(f"❌ 基本功能测试失败: {str(e)}")
        return False


async def test_tool_execution():
    """测试工具执行"""
    print("\n🧪 测试 2: 工具执行测试")
    print("=" * 60)

    try:
        from aat.agent.deepagent_tools import (
            smart_navigate,
            smart_click,
            verify_text_visible
        )

        # 测试导航工具
        print("测试导航工具...")
        nav_result = await smart_navigate.ainvoke({
            "url": "https://example.com",
            "wait_for_load": True,
            "timeout": 30000
        })
        assert nav_result["success"] == True
        print(f"✅ 导航工具测试通过: {nav_result['message']}")

        # 测试点击工具
        print("测试点击工具...")
        click_result = await smart_click.ainvoke({
            "target": "测试按钮",
            "humanize": True,
            "double_click": False
        })
        assert click_result["success"] == True
        print(f"✅ 点击工具测试通过: {click_result['message']}")

        # 测试验证工具
        print("测试验证工具...")
        verify_result = await verify_text_visible.ainvoke({
            "expected_text": "测试文本",
            "timeout": 5000
        })
        assert verify_result["success"] == True
        print(f"✅ 验证工具测试通过: {verify_result['message']}")

        return True

    except Exception as e:
        print(f"❌ 工具执行测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_supervisor_creation():
    """测试主管代理创建"""
    print("\n🧪 测试 3: 主管代理创建测试")
    print("=" * 60)

    try:
        # 测试自定义配置
        config = AgentConfig(
            ai_model="anthropic:claude-sonnet-4-6",
            default_mode="autonomous",
            max_exploration_depth=3,
        )

        supervisor = DeepAgentSupervisor(config)
        print("✅ 使用自定义配置创建主管代理成功")

        # 测试初始化
        await supervisor.initialize()
        print("✅ 主管代理初始化成功")

        # 验证LLM创建
        assert supervisor.llm is not None
        print("✅ LLM 创建成功")

        return True

    except Exception as e:
        print(f"❌ 主管代理创建测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_natural_language_processing():
    """测试自然语言处理"""
    print("\n🧪 测试 4: 自然语言处理测试")
    print("=" * 60)

    try:
        supervisor = await create_supervisor_from_config()

        # 测试意图理解
        test_cases = [
            "测试登录功能",
            "验证用户注册流程",
            "测试购物车功能",
        ]

        for test_request in test_cases:
            print(f"分析请求: {test_request}")
            intent = await supervisor._understand_intent(test_request)
            print(f"  - 类型: {intent.test_type}")
            print(f"  - 功能: {intent.target_features}")
            print(f"  - 风险: {intent.risk_level}")

        print("✅ 自然语言处理测试通过")
        return True

    except Exception as e:
        print(f"❌ 自然语言处理测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """运行所有测试"""
    print("🚀 开始运行 DeepAgent 自动化测试")
    print("=" * 60)

    tests = [
        ("基本功能测试", test_basic_functionality),
        ("工具执行测试", test_tool_execution),
        ("主管代理创建测试", test_supervisor_creation),
        ("自然语言处理测试", test_natural_language_processing),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 '{test_name}' 执行出错: {str(e)}")
            results.append((test_name, False))

    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！DeepAgent 迁移成功！")
        return True
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)