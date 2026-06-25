"""
调试Smart Agent配置加载
"""
import asyncio
from aat.agent.simple_supervisor import SimpleSupervisorAgent

async def debug_config():
    """调试配置加载"""
    try:
        print("🔍 调试Smart Agent配置加载...")

        # 创建代理实例
        agent = SimpleSupervisorAgent()

        print(f"📋 配置对象: {agent.config}")
        print(f"🤖 AI模型: {agent.config.ai_model}")
        print(f"🔧 默认模式: {agent.config.default_mode}")

        # 检查provider识别逻辑
        ai_model = agent.config.ai_model
        provider = ai_model.split(":")[0] if ":" in ai_model else "anthropic"
        print(f"🏷️  识别的provider: {provider}")

        # 尝试初始化
        print("\n📡 尝试初始化LLM...")
        await agent.initialize()

        if agent.llm:
            print("✅ LLM初始化成功!")
            print(f"🔧 LLM类型: {type(agent.llm)}")
            print(f"🌐 Base URL: {getattr(agent.llm, 'base_url', 'N/A')}")
            print(f"🤖 Model: {getattr(agent.llm, 'model_name', 'N/A')}")
        else:
            print("⚠️  LLM未初始化")

    except Exception as e:
        print(f"❌ 调试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_config())