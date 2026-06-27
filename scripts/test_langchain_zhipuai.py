"""
测试langchain-openai与智谱AI的集成
"""
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from aat.core.config import load_config

async def test_langchain_zhipuai():
    """测试langchain-openai与智谱AI集成"""
    try:
        # 加载配置
        aat_config = load_config()

        print("🔧 测试langchain-openai与智谱AI集成...")
        print(f"📋 API Key: {aat_config.ai.api_key[:20]}...")
        print(f"🤖 模型: {aat_config.ai.model}")
        print(f"🌡️  温度: {aat_config.ai.temperature}")

        # 尝试不同的配置方式
        configs = [
            {
                "name": "配置1: 标准base_url",
                "config": {
                    "base_url": "https://open.bigmodel.cn/api/coding/paas/v4/",
                    "api_key": aat_config.ai.api_key,
                    "model": aat_config.ai.model,
                    "temperature": aat_config.ai.temperature or 0.3,
                }
            },
            {
                "name": "配置2: 完整endpoint",
                "config": {
                    "base_url": "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions",
                    "api_key": aat_config.ai.api_key,
                    "model": aat_config.ai.model,
                    "temperature": aat_config.ai.temperature or 0.3,
                }
            }
        ]

        for config_test in configs:
            print(f"\n📡 测试 {config_test['name']}...")
            try:
                llm = ChatOpenAI(**config_test['config'])
                response = await llm.ainvoke([HumanMessage(content="你好")])
                print(f"✅ {config_test['name']} 成功!")
                print(f"🤖 回复: {response.content[:100]}...")
                return  # 成功就退出
            except Exception as e:
                print(f"❌ {config_test['name']} 失败: {str(e)[:100]}...")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_langchain_zhipuai())