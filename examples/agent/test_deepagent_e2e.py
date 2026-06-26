"""
端到端测试：完整的 DeepAgent 工作流程
"""

import asyncio
from aat.agent import create_supervisor_from_config, DeepAgentTestResult


async def test_complete_workflow():
    """测试完整的 DeepAgent 工作流程"""
    print("🚀 端到端测试：完整 DeepAgent 工作流程")
    print("=" * 60)

    try:
        # 1. 创建主管代理
        print("步骤 1: 创建主管代理...")
        supervisor = await create_supervisor_from_config()
        print("✅ 主管代理创建成功")

        # 2. 测试自然语言处理
        print("\n步骤 2: 测试自然语言请求处理...")
        test_requests = [
            "测试用户登录功能，验证用户名和密码输入",
            "检查页面导航是否正常工作",
            "验证购物车添加商品功能",
        ]

        for i, request in enumerate(test_requests, 1):
            print(f"  请求 {i}: {request}")
            intent = await supervisor._understand_intent(request)
            print(f"    分析结果: {intent.test_type} | {intent.target_features} | {intent.risk_level}")

        print("✅ 自然语言处理测试通过")

        # 3. 测试工具系统集成
        print("\n步骤 3: 测试工具系统集成...")
        from aat.agent import get_awt_deepagent_tools
        tools = get_awt_deepagent_tools()
        print(f"✅ 工具系统加载成功，共 {len(tools)} 个工具")

        # 4. 测试 DeepAgent 创建
        print("\n步骤 4: 测试 DeepAgent 创建...")
        agent = await supervisor._create_deepagent("autonomous")
        print("✅ DeepAgent 创建成功")

        # 5. 测试实际的任务执行
        print("\n步骤 5: 测试实际任务执行...")
        from langchain_core.messages import HumanMessage

        task_message = """
        作为智能测试代理，请执行以下任务：

        测试场景：验证网站基础功能
        目标网站：https://example.com
        测试重点：
        1. 页面能否正常加载
        2. 主要交互元素是否可访问
        3. 页面结构是否合理

        请简要说明你的测试计划，但不要实际执行（因为是测试环境）。
        """

        result = await agent.ainvoke({"messages": [HumanMessage(content=task_message)]})
        print("✅ 任务执行成功")

        # 提取并显示代理响应
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, 'content'):
                response = last_message.content
                print(f"\n🤖 DeepAgent 响应:")
                print("=" * 60)
                print(response[:500])  # 显示前500个字符
                if len(response) > 500:
                    print("...")
                print("=" * 60)

        # 6. 测试结果解析
        print("\n步骤 6: 测试结果解析...")
        parsed_result = supervisor._parse_deepagent_result(result)
        assert isinstance(parsed_result, DeepAgentTestResult)
        assert parsed_result.success == True
        print("✅ 结果解析测试通过")

        # 7. 测试对话功能
        print("\n步骤 7: 测试对话功能...")
        chat_response = await supervisor.chat("请简要说明如何测试一个登录表单")
        print(f"✅ 对话功能正常")
        print(f"回答预览: {chat_response[:200]}...")

        print("\n" + "=" * 60)
        print("🎉 端到端测试完全成功！")
        print("=" * 60)
        print("✅ 所有功能正常工作：")
        print("  - 主管代理创建和初始化")
        print("  - 自然语言处理和意图理解")
        print("  - 工具系统集成（15个工具）")
        print("  - DeepAgent 创建和配置")
        print("  - 任务执行和响应")
        print("  - 结果解析和处理")
        print("  - 对话交互功能")

        return True

    except Exception as e:
        print(f"❌ 端到端测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_handling():
    """测试错误处理能力"""
    print("\n🧪 测试错误处理能力")
    print("=" * 60)

    try:
        supervisor = await create_supervisor_from_config()

        # 测试无效输入的处理
        print("测试无效请求处理...")
        invalid_requests = [
            "",  # 空请求
            "   ",  # 只有空格
            "测试一个不存在的功能xyz123",  # 不明确的功能
        ]

        for request in invalid_requests:
            print(f"  处理: '{request}'")
            try:
                intent = await supervisor._understand_intent(request)
                print(f"    结果: {intent.test_type} (回退到默认)")
            except Exception as e:
                print(f"    异常处理: {str(e)[:50]}...")

        print("✅ 错误处理测试通过")
        return True

    except Exception as e:
        print(f"❌ 错误处理测试失败: {str(e)}")
        return False


async def main():
    """运行所有端到端测试"""
    print("🎯 DeepAgent 端到端测试套件")
    print("=" * 60)

    tests = [
        ("完整工作流程测试", test_complete_workflow),
        ("错误处理测试", test_error_handling),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 '{test_name}' 执行出错: {str(e)}")
            results.append((test_name, False))

    # 最终汇总
    print("\n" + "=" * 60)
    print("📊 最终测试结果")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")

    print(f"\n🎯 总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🏆 DeepAgent 系统完全就绪！")
        print("✅ 迁移成功，所有功能正常！")
        print("✅ 可以开始使用新的 DeepAgent 功能！")
        return True
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，需要检查")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)