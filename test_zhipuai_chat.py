"""
测试智谱AI集成的直接脚本
"""
import asyncio
import sys
from aat.agent.simple_supervisor import create_supervisor_from_config

async def test_chat():
    """测试对话功能"""
    try:
        print("🤖 创建智能代理 (使用现有配置)...")

        # 使用现有配置创建代理
        supervisor = await create_supervisor_from_config()

        print("✅ 代理创建成功!")

        # 测试对话
        test_message = "你好，请介绍一下你的功能"
        print(f"\n👤 用户: {test_message}")

        response = await supervisor.chat(test_message)
        print(f"🤖 代理: {response}")

        print("\n✅ 智谱AI集成测试成功!")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_chat())