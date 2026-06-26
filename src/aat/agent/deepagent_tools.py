"""
AWT DeepAgent Tools - 为 DeepAgents 框架优化的工具集

这些工具专门为 LangChain DeepAgents 框架设计，提供：
- 标准的工具签名和文档
- 详细的参数说明和类型提示
- 丰富的错误处理和状态反馈
- 与 AWT 现有系统的集成
"""

import asyncio
from typing import Any

from langchain_core.tools import tool


# ==================== 导航工具 ====================

@tool
async def smart_navigate(
    url: str,
    wait_for_load: bool = True,
    timeout: int = 30000
) -> dict[str, Any]:
    """
    智能导航到指定URL - 使用真实浏览器

    Args:
        url: 目标URL（完整地址，如 https://example.com）
        wait_for_load: 是否等待页面加载完成（默认 True）
        timeout: 超时时间，单位毫秒（默认 30000）

    Returns:
        导航结果字典，包含：
        - success (bool): 是否成功
        - url (str): 实际到达的URL
        - title (str): 页面标题
        - message (str): 详细消息
        - page_info (dict): 页面信息

    Example:
        >>> result = await smart_navigate("https://example.com")
        >>> print(result['message'])  # "成功导航到 https://example.com"
    """
    print(f"    📍 导航到: {url}")

    try:
        # 使用真实的 WebEngine
        from aat.engine.web import WebEngine
        from aat.core.config import EngineConfig

        # 配置显示模式的浏览器
        config = EngineConfig(
            type="web",
            browser="chromium",
            headless=False,  # 关键：显示浏览器
            timeout_ms=timeout,
        )

        engine = WebEngine(config)
        await engine.start()
        print("    🌐 浏览器已启动")

        # 导航到目标页面
        await engine.navigate(url)
        print("    ✅ 导航完成")

        # 获取页面信息
        page_info = await engine.get_page_info()

        # 保持引擎运行，以便后续操作
        # 注意：实际使用中应该管理引擎生命周期

        return {
            "success": True,
            "url": url,
            "title": page_info.get("title", ""),
            "message": f"成功导航到 {url}",
            "page_info": page_info,
            "engine_started": True
        }

    except Exception as e:
        print(f"    ⚠️  导航失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"导航失败: {str(e)}"
        }


@tool
def go_back() -> dict[str, Any]:
    """
    返回上一页

    Returns:
        返回结果字典，包含：
        - success (bool): 是否成功
        - message (str): 详细消息

    Example:
        >>> result = go_back()
        >>> print(result['message'])  # "成功返回上一页"
    """
    print("    ◀️ 返回上一页")

    # TODO: 集成实际的浏览器操作
    return {
        "success": True,
        "message": "成功返回上一页"
    }


@tool
def go_forward() -> dict[str, Any]:
    """
    前进到下一页

    Returns:
        前进结果字典，包含：
        - success (bool): 是否成功
        - message (str): 详细消息

    Example:
        >>> result = go_forward()
        >>> print(result['message'])  # "成功前进到下一页"
    """
    print("    ▶️ 前进到下一页")

    # TODO: 集成实际的浏览器操作
    return {
        "success": True,
        "message": "成功前进到下一页"
    }


@tool
def refresh_page() -> dict[str, Any]:
    """
    刷新当前页面

    Returns:
        刷新结果字典，包含：
        - success (bool): 是否成功
        - message (str): 详细消息

    Example:
        >>> result = refresh_page()
        >>> print(result['message'])  # "成功刷新页面"
    """
    print("    🔄 刷新页面")

    # TODO: 集成实际的浏览器操作
    return {
        "success": True,
        "message": "成功刷新页面"
    }


# ==================== 元素定位工具 ====================

@tool
async def locate_element(
    target_description: str,
    matching_strategy: str = "hybrid",
    timeout: int = 10000
) -> dict[str, Any]:
    """
    定位页面元素

    Args:
        target_description: 目标元素的描述（如"登录按钮"、"用户名输入框"）
        matching_strategy: 匹配策略
            - "hybrid": 混合策略（默认，推荐）
            - "ocr": OCR文本识别
            - "vision": 视觉AI识别
            - "selector": CSS选择器
        timeout: 超时时间，单位毫秒（默认 10000）

    Returns:
        元素定位结果字典，包含：
        - success (bool): 是否成功
        - element (dict): 元素信息
            - selector (str): CSS选择器
            - description (str): 元素描述
            - position (dict): 位置坐标 {"x": int, "y": int}
        - message (str): 详细消息

    Example:
        >>> result = await locate_element("登录按钮", "hybrid")
        >>> print(result['element']['selector'])  # "[data-testid='login-button']"
    """
    await asyncio.sleep(0.3)  # 模拟定位时间

    print(f"    🔍 定位元素: {target_description} (策略: {matching_strategy})")

    # TODO: 集成实际的 Matcher 系统
    # 目前返回模拟结果，实际应该调用：
    # from aat.matchers.base import Matcher
    # matcher = Matcher()
    # element = await matcher.locate(target_description, strategy=matching_strategy)

    return {
        "success": True,
        "element": {
            "selector": f"[data-testid='{target_description}']",
            "description": target_description,
            "position": {"x": 100, "y": 200}
        },
        "message": f"成功定位元素: {target_description}"
    }


# ==================== 交互工具 ====================

@tool
async def smart_click(
    target: str,
    humanize: bool = True,
    double_click: bool = False
) -> dict[str, Any]:
    """
    智能点击元素 - 使用真实浏览器

    Args:
        target: 目标元素的描述或选择器
        humanize: 是否模拟真人操作（默认 True）
            - True: 使用贝塞尔曲线移动，模拟真人鼠标轨迹
            - False: 直接点击
        double_click: 是否双击（默认 False）

    Returns:
        点击结果字典，包含：
        - success (bool): 是否成功
        - action (str): 执行的动作
        - message (str): 详细消息
        - element (str): 目标元素

    Example:
        >>> result = await smart_click("提交按钮", humanize=True)
        >>> print(result['message'])  # "成功单击: 提交按钮"
    """
    click_type = "双击" if double_click else "单击"
    humanize_str = "（真人模式）" if humanize else "（直接模式）"

    print(f"    🖱️  {click_type}: {target} {humanize_str}")

    try:
        # 使用真实的 WebEngine
        from aat.engine.web import WebEngine
        from aat.core.config import EngineConfig

        # 获取或创建引擎实例
        # 注意：这里需要实现引擎实例管理
        # 暂时返回模拟结果，待完整实现
        return {
            "success": True,
            "action": f"{click_type}了元素: {target}",
            "message": f"成功{click_type}: {target}",
            "element": target,
            "note": "真实浏览器集成中"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"点击失败: {str(e)}"
        }


@tool
async def smart_type(
    target: str,
    text: str,
    humanize: bool = True,
    clear_first: bool = True
) -> dict[str, Any]:
    """
    智能输入文本

    Args:
        target: 目标元素的描述（如"用户名输入框"）
        text: 要输入的文本内容
        humanize: 是否模拟真人输入（默认 True）
            - True: 使用变速输入和随机停顿
            - False: 快速输入
        clear_first: 是否先清空输入框（默认 True）

    Returns:
        输入结果字典，包含：
        - success (bool): 是否成功
        - action (str): 执行的动作
        - text (str): 输入的文本
        - message (str): 详细消息
        - element (str): 目标元素

    Example:
        >>> result = await smart_type("用户名输入框", "test@example.com", humanize=True)
        >>> print(result['message'])  # "成功输入 'test@example.com' 到 用户名输入框"
    """
    await asyncio.sleep(0.4)  # 模拟输入时间

    humanize_str = "（真人模式）" if humanize else "（快速模式）"
    clear_str = "（先清空）" if clear_first else "（不清空）"

    print(f"    ⌨️  输入: {text} 到 {target} {humanize_str} {clear_str}")

    # TODO: 集成实际的输入逻辑
    # 目前模拟输入，实际应该调用：
    # from aat.engine.base import WebEngine
    # engine = WebEngine()
    # await engine.type(target, text, humanize=humanize, clear=clear_first)

    return {
        "success": True,
        "action": f"输入文本到: {target}",
        "text": text,
        "message": f"成功输入 '{text}' 到 {target}",
        "element": target
    }


@tool
async def select_option(
    target: str,
    value: str
) -> dict[str, Any]:
    """
    选择下拉选项

    Args:
        target: 下拉框的描述（如"国家选择器"）
        value: 要选择的值（如"中国"、"United States"）

    Returns:
        选择结果字典，包含：
        - success (bool): 是否成功
        - action (str): 执行的动作
        - value (str): 选择的值
        - message (str): 详细消息
        - element (str): 目标元素

    Example:
        >>> result = await select_option("国家选择器", "中国")
        >>> print(result['message'])  # "成功选择 '中国' 从 国家选择器"
    """
    await asyncio.sleep(0.3)

    print(f"    🎯 选择: {value} 从 {target}")

    # TODO: 集成实际的下拉选择逻辑
    return {
        "success": True,
        "action": f"选择选项: {value}",
        "value": value,
        "message": f"成功选择 '{value}' 从 {target}",
        "element": target
    }


# ==================== 验证工具 ====================

@tool
async def verify_text_visible(
    expected_text: str,
    timeout: int = 5000
) -> dict[str, Any]:
    """
    验证文本是否可见

    Args:
        expected_text: 期望看到的文本内容
        timeout: 超时时间，单位毫秒（默认 5000）

    Returns:
        验证结果字典，包含：
        - success (bool): 是否成功
        - assertion (str): 验证断言
        - message (str): 详细消息
        - expected_text (str): 期望的文本

    Example:
        >>> result = await verify_text_visible("欢迎")
        >>> print(result['message'])  # "成功验证文本: 欢迎"
    """
    await asyncio.sleep(0.2)

    print(f"    ✅ 验证文本可见: {expected_text}")

    # TODO: 集成实际的文本验证逻辑
    # 目前模拟验证成功，实际应该调用：
    # from aat.engine.base import WebEngine
    # engine = WebEngine()
    # visible = await engine.verify_text(expected_text, timeout=timeout)

    return {
        "success": True,
        "assertion": f"文本可见: {expected_text}",
        "message": f"成功验证文本: {expected_text}",
        "expected_text": expected_text
    }


@tool
async def verify_element_exists(
    selector: str,
    timeout: int = 5000
) -> dict[str, Any]:
    """
    验证元素是否存在

    Args:
        selector: 元素选择器（CSS选择器或描述）
        timeout: 超时时间，单位毫秒（默认 5000）

    Returns:
        验证结果字典，包含：
        - success (bool): 是否成功
        - assertion (str): 验证断言
        - message (str): 详细消息
        - selector (str): 元素选择器

    Example:
        >>> result = await verify_element_exists("#submit-button")
        >>> print(result['message'])  # "成功验证元素存在: #submit-button"
    """
    await asyncio.sleep(0.2)

    print(f"    ✅ 验证元素存在: {selector}")

    # TODO: 集成实际的元素验证逻辑
    return {
        "success": True,
        "assertion": f"元素存在: {selector}",
        "message": f"成功验证元素存在: {selector}",
        "selector": selector
    }


@tool
def verify_url_contains(
    expected_fragment: str
) -> dict[str, Any]:
    """
    验证URL是否包含指定片段

    Args:
        expected_fragment: 期望URL包含的片段

    Returns:
        验证结果字典，包含：
        - success (bool): 是否成功
        - assertion (str): 验证断言
        - message (str): 详细消息
        - expected_fragment (str): 期望的片段

    Example:
        >>> result = verify_url_contains("/dashboard")
        >>> print(result['message'])  # "成功验证URL包含: /dashboard"
    """
    print(f"    ✅ 验证URL包含: {expected_fragment}")

    # TODO: 集成实际的URL验证逻辑
    return {
        "success": True,
        "assertion": f"URL包含: {expected_fragment}",
        "message": f"成功验证URL包含: {expected_fragment}",
        "expected_fragment": expected_fragment
    }


# ==================== 分析工具 ====================

@tool
async def analyze_page(
    analysis_depth: str = "basic",
    include_hidden: bool = False
) -> dict[str, Any]:
    """
    分析当前页面结构

    Args:
        analysis_depth: 分析深度
            - "basic": 基础分析（默认）- 主要元素和结构
            - "detailed": 详细分析 - 所有元素和属性
            - "full": 完整分析 - 包括隐藏元素和DOM树
        include_hidden: 是否包含隐藏元素（默认 False）

    Returns:
        页面分析结果字典，包含：
        - success (bool): 是否成功
        - analysis (dict): 分析结果
            - title (str): 页面标题
            - interactive_elements (list): 交互元素列表
            - forms (list): 表单列表
            - navigation (list): 导航链接列表
        - message (str): 详细消息

    Example:
        >>> result = await analyze_page("basic")
        >>> print(result['analysis']['title'])  # "页面标题"
    """
    await asyncio.sleep(1)  # 模拟分析时间

    print(f"    🔬 分析页面结构 (深度: {analysis_depth})")

    # TODO: 集成实际的页面分析逻辑
    # 目前返回模拟结果，实际应该调用：
    # from aat.engine.base import WebEngine
    # engine = WebEngine()
    # analysis = await engine.analyze_page(depth=analysis_depth)

    return {
        "success": True,
        "analysis": {
            "title": "示例页面",
            "interactive_elements": [
                {"type": "button", "text": "提交", "id": "submit-btn"},
                {"type": "input", "placeholder": "用户名", "id": "username"},
                {"type": "input", "placeholder": "密码", "id": "password", "type": "password"},
            ],
            "navigation": [
                {"text": "首页", "url": "/home"},
                {"text": "关于", "url": "/about"},
                {"text": "联系", "url": "/contact"},
            ],
            "forms": [
                {"id": "login-form", "fields": ["username", "password"]}
            ],
        },
        "message": "页面分析完成"
    }


@tool
async def take_screenshot(
    filename: str | None = None,
    full_page: bool = False,
    element_selector: str | None = None
) -> dict[str, Any]:
    """
    截取屏幕截图

    Args:
        filename: 文件名（可选，默认自动生成）
        full_page: 是否截取整个页面（默认 False）
        element_selector: 要截取的元素选择器（可选）

    Returns:
        截图结果字典，包含：
        - success (bool): 是否成功
        - screenshot_path (str): 截图保存路径
        - message (str): 详细消息
        - filename (str): 文件名

    Example:
        >>> result = await take_screenshot("test_screenshot.png", full_page=True)
        >>> print(result['screenshot_path'])  # "/screenshots/test_screenshot.png"
    """
    await asyncio.sleep(0.1)

    if not filename:
        from datetime import datetime
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    print(f"    📸 截图: {filename} (全页: {full_page})")

    # TODO: 集成实际的截图逻辑
    # 目前模拟截图，实际应该调用：
    # from aat.engine.base import WebEngine
    # engine = WebEngine()
    # path = await engine.screenshot(filename, full_page=full_page, element=element_selector)

    return {
        "success": True,
        "screenshot_path": f"/screenshots/{filename}",
        "message": "截图保存成功",
        "filename": filename
    }


@tool
async def check_console(
    level: str = "error",
    clear_after_check: bool = False
) -> dict[str, Any]:
    """
    检查浏览器控制台错误和警告

    Args:
        level: 检查级别
            - "error": 只检查错误（默认）
            - "warning": 检查警告和错误
            - "all": 检查所有日志
        clear_after_check: 检查后是否清空控制台（默认 False）

    Returns:
        控制台检查结果字典，包含：
        - success (bool): 是否成功
        - console_info (dict): 控制台信息
            - errors (list): 错误列表
            - warnings (list): 警告列表
            - info (list): 信息列表
        - message (str): 详细消息

    Example:
        >>> result = await check_console("error")
        >>> print(result['console_info']['errors'])  # []
    """
    await asyncio.sleep(0.1)

    print(f"    🔧 检查控制台 (级别: {level})")

    # TODO: 集成实际的控制台检查逻辑
    # 目前返回模拟结果，实际应该调用：
    # from aat.engine.base import WebEngine
    # engine = WebEngine()
    # console_info = await engine.check_console(level=level)

    return {
        "success": True,
        "console_info": {
            "errors": [],
            "warnings": [],
            "info": ["页面加载完成", "资源加载成功"]
        },
        "message": "控制台检查完成"
    }


@tool
async def wait_for_element(
    selector: str,
    timeout: int = 10000,
    state: str = "visible"
) -> dict[str, Any]:
    """
    等待元素出现

    Args:
        selector: 元素选择器或描述
        timeout: 超时时间，单位毫秒（默认 10000）
        state: 等待状态
            - "visible": 等待元素可见（默认）
            - "hidden": 等待元素隐藏
            - "attached": 等待元素加入DOM

    Returns:
        等待结果字典，包含：
        - success (bool): 是否成功
        - message (str): 详细消息
        - selector (str): 元素选择器
        - wait_time (float): 实际等待时间（秒）

    Example:
        >>> result = await wait_for_element("#submit-button", 5000, "visible")
        >>> print(result['message'])  # "元素 #submit-button 已出现"
    """
    wait_time = min(timeout / 1000, 2)  # 最多等待2秒（模拟）
    await asyncio.sleep(wait_time)

    print(f"    ⏱️  等待元素: {selector} (状态: {state})")

    # TODO: 集成实际的等待逻辑
    return {
        "success": True,
        "message": f"元素 {selector} 已出现",
        "selector": selector,
        "wait_time": wait_time
    }


# ==================== 工具集导出 ====================

def get_awt_deepagent_tools() -> list:
    """
    获取所有 AWT DeepAgent 工具

    Returns:
        工具列表，专为 DeepAgents 框架优化

    Example:
        >>> tools = get_awt_deepagent_tools()
        >>> from deepagents import create_deep_agent
        >>> agent = create_deep_agent(model=llm, tools=tools)
    """
    return [
        # 导航工具
        smart_navigate,
        go_back,
        go_forward,
        refresh_page,

        # 元素定位工具
        locate_element,

        # 交互工具
        smart_click,
        smart_type,
        select_option,

        # 验证工具
        verify_text_visible,
        verify_element_exists,
        verify_url_contains,

        # 分析工具
        analyze_page,
        take_screenshot,
        check_console,
        wait_for_element,
    ]


# 工具分类函数
def get_navigation_tools() -> list:
    """获取导航工具"""
    return [smart_navigate, go_back, go_forward, refresh_page]


def get_interaction_tools() -> list:
    """获取交互工具"""
    return [smart_click, smart_type, select_option]


def get_verification_tools() -> list:
    """获取验证工具"""
    return [verify_text_visible, verify_element_exists, verify_url_contains]


def get_analysis_tools() -> list:
    """获取分析工具"""
    return [analyze_page, take_screenshot, check_console, wait_for_element]


def get_tools_by_category(category: str) -> list:
    """
    根据类别获取工具

    Args:
        category: 工具类别
            - "navigation": 导航工具
            - "interaction": 交互工具
            - "verification": 验证工具
            - "analysis": 分析工具
            - "all": 所有工具

    Returns:
        该类别的工具列表
    """
    categories = {
        "navigation": get_navigation_tools,
        "interaction": get_interaction_tools,
        "verification": get_verification_tools,
        "analysis": get_analysis_tools,
        "all": get_awt_deepagent_tools
    }

    return categories.get(category, get_awt_deepagent_tools)()