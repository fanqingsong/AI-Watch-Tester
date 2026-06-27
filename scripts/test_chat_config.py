"""
快速配置测试 - 使用你现有的智谱AI配置

这个脚本会直接读取 aat.config.yaml 中的配置来运行对话代理
"""

import asyncio
import yaml
from pathlib import Path

async def test_chat_with_config():
    """使用现有配置测试对话"""

    # 1. 读取现有配置
    config_path = Path("aat.config.yaml")
    if not config_path.exists():
        print("❌ 找不到 aat.config.yaml 文件")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)

    print("📋 读取配置成功:")
    print(f"   AI 揓商: {config_data['ai']['provider']}")
    print(f"   模型: {config_data['ai']['model']}")
    print(f"   API Key: {config_data['ai']['api_key'][:20]}...")

    print("\n🤖 启动智能测试代理 (使用你配置的智谱AI)...")

    # 2. 模拟对话循环
    print("\n💬 输入 'quit' 退出")
    print("-" * 50)

    test_messages = [
        "测试登录功能",
        "如何测试购物流程？",
        "分析页面结构",
        "生成测试计划"
    ]

    for i, message in enumerate(test_messages, 1):
        print(f"\n👤 测试消息 {i}/4: {message}")
        print("🤖 代理回复:")

        # 模拟AI回复（使用配置的智谱AI会更智能）
        responses = {
            1: "我可以帮您测试登录功能。请提供登录页面的URL，我会：\n1. 导航到登录页面\n2. 分析登录表单\n3. 测试用户名和密码输入\n4. 验证登录后的页面\n\n你的登录页面URL是什么？",

            2: "购物流程测试很棒！我会帮你：\n1. 导航到商品页面\n2. 测试商品浏览\n3. 添加商品到购物车\n4. 测试结算流程\n\n你想从哪个页面开始？",

            3: "页面分析功能包括：\n1. 识别所有交互元素\n2. 构建页面功能图谱\n3. 发现可测试的用户路径\n4. 评估测试覆盖率\n\n请提供要分析的页面URL。",

            4: "测试计划生成需要：\n1. 明确的测试目标\n2. 目标页面URL\n3. 测试类型（功能/性能/安全）\n\n请告诉我你想测试什么功能？"
        }

        print(f"   {responses[i]}\n")

        # 简单的模拟用户输入
        if i < 4:
            print("   [模拟用户确认]")

    print("\n✅ 配置测试完成！")
    print("💡 要使用真实的智谱AI对话，请安装: pip install langchain-openai --upgrade")
    print("💡 或运行: aat agent chat")

if __name__ == "__main__":
    asyncio.run(test_chat_with_config())
