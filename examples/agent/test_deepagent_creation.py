"""
测试 DeepAgent 的实际创建和调用
"""

import asyncio
from aat.agent import DeepAgentSupervisor, AgentConfig


async def test_deepagent_creation():
    """测试 DeepAgent 的创建"""
    print("🧪 测试 DeepAgent 创建和基本调用")
    print("=" * 60)

    try:
        # 创建配置
        config = AgentConfig(
            ai_model="anthropic:claude-sonnet-4-6",
            default_mode="autonomous",
        )

        # 创建主管代理
        supervisor = DeepAgentSupervisor(config)
        print("✅ DeepAgentSupervisor 创建成功")

        # 初始化
        await supervisor.initialize()
        print("✅ 主管代理初始化成功")

        # 测试 DeepAgent 创建
        print("测试 DeepAgent 创建...")
        agent = await supervisor._create_deepagent("autonomous")
        print("✅ DeepAgent 创建成功")

        # 验证代理属性
        assert agent is not None
        print("✅ 代理实例验证通过")

        # 测试简单调用
        print("测试简单的代理调用...")
        from langchain_core.messages import HumanMessage

        test_message = """
        你是一个测试助手。请分析以下情况：

        测试需求：验证页面导航功能
        目标URL：https://example.com
        预期结果：能够成功加载页面

        请简要说明你会如何执行这个测试。
        """

        result = await agent.ainvoke({"messages": [HumanMessage(content=test_message)]})
        print("✅ 代理调用成功")

        # 检查结果
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, 'content'):
                print(f"✅ 代理响应内容: {last_message.content[:200]}...")
            else:
                print(f"✅ 代理响应: {str(last_message)[:200]}...")

        print("\n🎉 DeepAgent 创建和调用测试完全成功！")
        return True

    except Exception as e:
        print(f"❌ DeepAgent 创建测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_different_modes():
    """测试不同的运行模式"""
    print("\n🧪 测试不同运行模式")
    print("=" * 60)

    try:
        supervisor = DeepAgentSupervisor(AgentConfig())
        await supervisor.initialize()

        modes = ["interactive", "autonomous", "conservative", "aggressive"]

        for mode in modes:
            print(f"测试 {mode} 模式...")
            agent = await supervisor._create_deepagent(mode)
            assert agent is not None
            print(f"✅ {mode} 模式创建成功")

        print("✅ 所有模式测试通过")
        return True

    except Exception as e:
        print(f"❌ 模式测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行测试"""
    print("🚀 DeepAgent 创建和功能测试")
    print("=" * 60)

    tests = [
        ("DeepAgent 创建测试", test_deepagent_creation),
        ("不同模式测试", test_different_modes),
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
        print("\n🎉 DeepAgent 完全正常工作！迁移成功！")
        return True
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)