"""
测试真实的Smart Agent对话功能
"""
import asyncio
from aat.agent.simple_supervisor import create_supervisor_from_config

async def test_real_conversation():
    """测试真实的对话功能"""
    try:
        print("🤖 创建Smart Agent...")
        supervisor = await create_supervisor_from_config()

        print("✅ Smart Agent创建成功!")

        # 测试几个对话轮次
        test_conversations = [
            "你好，请介绍一下AWT测试框架",
            "如何测试登录功能？",
            "能帮我生成测试计划吗？"
        ]

        for i, message in enumerate(test_conversations, 1):
            print(f"\n{'='*50}")
            print(f"👤 用户 (轮次 {i}/{len(test_conversations)}): {message}")

            response = await supervisor.chat(message)
            print(f"🤖 Smart Agent: {response}")

            # 短暂延迟避免请求过快
            await asyncio.sleep(1)

        print(f"\n{'='*50}")
        print("✅ 对话测试完成!")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_real_conversation())