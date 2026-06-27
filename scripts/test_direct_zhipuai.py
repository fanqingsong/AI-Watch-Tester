"""
直接测试智谱AI API连接
"""
import asyncio
from openai import AsyncOpenAI
from aat.core.config import load_config

async def test_zhipuai_direct():
    """直接测试智谱AI API"""
    try:
        # 加载配置
        aat_config = load_config()

        print("🔧 测试智谱AI API连接...")
        print(f"API Key: {aat_config.ai.api_key[:20]}...")
        print(f"Model: {aat_config.ai.model}")
        print(f"Temperature: {aat_config.ai.temperature}")

        # 创建客户端
        client = AsyncOpenAI(
            api_key=aat_config.ai.api_key,
            base_url="https://open.bigmodel.cn/api/coding/paas/v4/"
        )

        # 测试连接
        print("\n📡 发送测试请求...")
        response = await client.chat.completions.create(
            model=aat_config.ai.model,
            messages=[{"role": "user", "content": "你好，请介绍一下你自己"}],
            temperature=aat_config.ai.temperature or 0.3,
        )

        print("✅ 智谱AI连接成功!")
        print(f"🤖 回复: {response.choices[0].message.content}")

    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_zhipuai_direct())