"""
智谱AI (ZhipuAI) LangChain 集成

提供智谱AI的 LangChain ChatModel 实现，用于与 Deep Agents 集成。
"""

from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from zhipuai import ZhipuAI


class ChatZhipuAI(BaseChatModel):
    """
    智谱AI ChatModel 实现

    这个类将智谱AI集成到 LangChain 框架中，使其可以与 Deep Agents 一起使用。
    """

    client: ZhipuAI
    model: str = "glm-4.7"
    temperature: float = 0.7
    max_tokens: int = 4096
    api_key: str

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, api_key: str, model: str = "glm-4.7", **kwargs):
        """
        初始化智谱AI ChatModel

        Args:
            api_key: 智谱AI API密钥
            model: 模型名称 (默认: glm-4.7)
            **kwargs: 其他参数
        """
        super().__init__(
            client=ZhipuAI(api_key=api_key),
            model=model,
            api_key=api_key,
            **kwargs
        )

    def _generate(
        self,
        messages: List[BaseMessage],
        **kwargs: Any,
    ) -> ChatResult:
        """
        生成聊天回复

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            ChatResult: 聊天结果

        Raises:
            Exception: 当API调用失败时，提供清晰的错误信息
        """
        # 转换消息格式
        zhipu_messages = []
        for message in messages:
            if isinstance(message, HumanMessage):
                zhipu_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                zhipu_messages.append({"role": "assistant", "content": message.content})
            elif isinstance(message, SystemMessage):
                zhipu_messages.append({"role": "system", "content": message.content})

        try:
            # 调用智谱AI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=zhipu_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # 提取回复内容
            content = response.choices[0].message.content

            # 创建 ChatGeneration
            generation = ChatGeneration(
                message=AIMessage(content=content),
            )

            return ChatResult(generations=[generation])

        except Exception as e:
            # 提供清晰的错误信息
            error_str = str(e)
            if "余额不足" in error_str or "1113" in error_str:
                raise Exception(
                    "智谱AI账户余额不足，请充值后再试。你可以:\n"
                    "1. 在智谱AI平台充值: https://open.bigmodel.cn/\n"
                    "2. 或者在 aat.config.yaml 中切换到其他AI提供商 (anthropic, openai)"
                ) from e
            elif "Invalid API key" in error_str:
                raise Exception(
                    "智谱AI API密钥无效，请检查 aat.config.yaml 中的 api_key 配置"
                ) from e
            else:
                raise Exception(f"智谱AI调用失败: {error_str}") from e

    @property
    def _llm_type(self) -> str:
        """返回LLM类型标识"""
        return "zhipuai"


def create_zhipuai_model(api_key: str, model: str = "glm-4.7", **kwargs) -> ChatZhipuAI:
    """
    创建智谱AI ChatModel 实例

    Args:
        api_key: 智谱AI API密钥
        model: 模型名称
        **kwargs: 其他参数

    Returns:
        ChatZhipuAI: 智谱AI ChatModel 实例
    """
    return ChatZhipuAI(api_key=api_key, model=model, **kwargs)
