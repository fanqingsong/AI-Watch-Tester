"""
AWT Smart Agent 快速开始示例

演示如何使用 AWT 智能测试代理进行自然语言测试
"""

import asyncio
from aat.agent.supervisor import AWTSupervisorAgent, create_supervisor
from aat.agent.config import AgentConfig


async def example_1_basic_test():
    """示例 1: 基础测试"""
    print("\n" + "="*60)
    print("示例 1: 基础测试 - 测试登录功能")
    print("="*60)

    # 创建代理
    config = AgentConfig(
        ai_model="anthropic:claude-sonnet-4-6",
        default_mode="interactive"
    )

    supervisor = await create_supervisor(config)

    # 执行测试
    result = await supervisor.test_from_natural_language(
        user_request="测试用户登录功能，包括验证错误处理",
        start_url="http://localhost:3000/login",
        mode="interactive"
    )

    print("\n📊 测试结果:")
    print(result.get("summary", "测试完成"))


async def example_2_multi_step_test():
    """示例 2: 多步骤测试"""
    print("\n" + "="*60)
    print("示例 2: 多步骤测试 - 购物流程")
    print("="*60)

    config = AgentConfig(
        ai_model="anthropic:claude-sonnet-4-6",
        default_mode="autonomous"
    )

    supervisor = await create_supervisor(config)

    result = await supervisor.test_from_natural_language(
        user_request="测试完整的购物流程：浏览商品、添加到购物车、结账",
        start_url="http://localhost:3000",
        mode="autonomous"
    )

    print("\n📊 测试结果:")
    print(result.get("summary", "测试完成"))


async def example_3_interactive_test():
    """示例 3: 交互式测试"""
    print("\n" + "="*60)
    print("示例 3: 交互式测试 - 表单验证")
    print("="*60)

    config = AgentConfig(
        ai_model="anthropic:claude-sonnet-4-6",
        default_mode="conservative"
    )

    supervisor = await create_supervisor(config)

    result = await supervisor.test_from_natural_language(
        user_request="测试用户注册表单的验证功能",
        start_url="http://localhost:3000/register",
        mode="conservative"
    )

    print("\n📊 测试结果:")
    print(result.get("summary", "测试完成"))


async def example_4_chat_interface():
    """示例 4: 对话式界面"""
    print("\n" + "="*60)
    print("示例 4: 对话式界面")
    print("="*60)

    config = AgentConfig()
    supervisor = await create_supervisor(config)

    # 模拟对话
    conversations = [
        "我想测试登录功能",
        "重点关注错误处理",
        "还要测试密码找回"
    ]

    for message in conversations:
        print(f"\n👤 用户: {message}")
        response = await supervisor.chat(message)
        print(f"🤖 代理: {response}")


async def main():
    """运行所有示例"""
    print("🚀 AWT Smart Agent 示例程序")

    # 注意：这些是演示示例，实际运行需要：
    # 1. 配置 AI API 密钥
    # 2. 有可测试的网站
    # 3. 安装所有依赖

    print("\n⚠️  注意事项:")
    print("- 这些示例使用模拟的工具和响应")
    print("- 实际使用需要配置 AI API 密钥")
    print("- 需要有可访问的测试网站")
    print("- 需要安装 deepagents 和相关依赖")

    # 取消注释以运行具体示例：
    # await example_1_basic_test()
    # await example_2_multi_step_test()
    # await example_3_interactive_test()
    # await example_4_chat_interface()

    print("\n✅ 示例程序准备完成")
    print("📖 查看代码了解如何使用 AWT Smart Agent")


if __name__ == "__main__":
    asyncio.run(main())