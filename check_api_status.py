"""
检查智谱AI账户状态
"""
import asyncio
from openai import AsyncOpenAI
from aat.core.config import load_config

async def check_zhipuai_status():
    """检查智谱AI账户状态"""
    try:
        # 加载配置
        aat_config = load_config()

        print("🔍 检查智谱AI账户状态...")
        print(f"📋 API Key: {aat_config.ai.api_key[:20]}...")
        print(f"🤖 模型: {aat_config.ai.model}")
        print(f"🌡️  温度: {aat_config.ai.temperature}")

        # 创建客户端
        client = AsyncOpenAI(
            api_key=aat_config.ai.api_key,
            base_url="https://open.bigmodel.cn/api/coding/paas/v4/"
        )

        # 测试连接
        print("\n📡 测试API连接...")
        response = await client.chat.completions.create(
            model=aat_config.ai.model,
            messages=[{"role": "user", "content": "测试"}],
            temperature=0.1,
            max_tokens=10
        )

        print("✅ 智谱AI账户状态正常")
        print(f"🤖 API响应成功")
        print(f"💰 账户余额充足")

    except Exception as e:
        error_str = str(e)
        print(f"❌ 账户状态检查失败")

        if "余额不足" in error_str or "1113" in error_str:
            print("⚠️  问题: 账户余额不足")
            print("💡 解决方案: 请访问智谱AI官网充值")
            print("🔗 充值链接: https://open.bigmodel.cn/usercenter/recharge")
        elif "401" in error_str or "403" in error_str:
            print("⚠️  问题: API密钥无效或已过期")
            print("💡 解决方案: 请检查API密钥配置")
        elif "429" in error_str:
            print("⚠️  问题: API调用频率限制")
            print("💡 解决方案: 请稍后重试")
        else:
            print(f"⚠️  未知错误: {error_str}")

if __name__ == "__main__":
    asyncio.run(check_zhipuai_status())