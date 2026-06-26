"""
真实浏览器 DeepAgent 配置

这个配置让 DeepAgent 使用真实的 WebEngine 而不是模拟工具。
"""

from aat.agent.config import AgentConfig
from aat.agent.real_browser_tools import get_real_browser_tools


def create_deepagent_with_real_browser():
    """创建使用真实浏览器的 DeepAgent 配置"""
    return {
        "tools": get_real_browser_tools(),
        "system_prompt": """
        你是一个智能测试代理，使用真实的浏览器执行测试。

        重要：
        - 必须使用真实浏览器工具
        - 浏览器窗口会真正打开
        - 用户可以观察到操作过程
        - 每个操作都是真实的浏览器交互

        可用工具：
        - real_navigate: 真实浏览器导航
        - real_click: 真实浏览器点击
        - real_type: 真实浏览器输入
        - verify_text_visible: 验证页面文本
        """
    }


def get_real_browser_agent_config():
    """获取真实浏览器代理配置"""
    return {
        "tools": get_real_browser_tools(),
        "browser_mode": "visible",  # 显示模式
        "headless": False,
        "screenshot_on_each_step": True,
    }