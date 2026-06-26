"""
AWT DeepAgent 真实浏览器工具集

这些工具使用真实的 WebEngine 来执行浏览器操作，会真正打开浏览器窗口。
"""

import asyncio
from typing import Any
from langchain_core.tools import tool

# 全局 WebEngine 实例
_web_engine = None


async def get_web_engine():
    """获取或创建 WebEngine 实例"""
    global _web_engine
    if _web_engine is None:
        from aat.engine.web import WebEngine
        from aat.core import EngineConfig

        config = EngineConfig(
            type="web",
            browser="chromium",
            headless=False,  # 重要：设置为 False 以显示浏览器
            timeout_ms=30000,
        )

        _web_engine = WebEngine(config)
        await _web_engine.start()
        print("🌐 浏览器已启动 (显示模式)")

    return _web_engine


async def close_web_engine():
    """关闭 WebEngine"""
    global _web_engine
    if _web_engine:
        await _web_engine.stop()
        _web_engine = None
        print("🌐 浏览器已关闭")


# ==================== 导航工具 ====================

@tool
async def real_navigate(
    url: str,
    wait_for_load: bool = True,
    timeout: int = 30000
) -> dict[str, Any]:
    """
    真实浏览器导航到指定URL

    Args:
        url: 目标URL（完整地址）
        wait_for_load: 是否等待页面加载完成（默认 True）
        timeout: 超时时间，单位毫秒（默认 30000）

    Returns:
        导航结果字典
    """
    engine = await get_web_engine()

    print(f"    📍 导航到: {url}")

    try:
        await engine.navigate(url)

        # 获取页面信息
        current_url = await engine.get_url()
        page_text = await engine.get_page_text()

        return {
            "success": True,
            "url": current_url,
            "title": page_text[:100] if page_text else "",  # 使用页面文本的前100字符作为标题预览
            "message": f"成功导航到 {url}",
            "page_info": {
                "url": current_url,
                "text_preview": page_text[:100] if page_text else ""
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"导航失败: {str(e)}"
        }


@tool
def go_back() -> dict[str, Any]:
    """返回上一页"""
    print("    ◀️ 返回上一页")
    return {"success": True, "message": "成功返回上一页"}


@tool
def go_forward() -> dict[str, Any]:
    """前进到下一页"""
    print("    ▶️ 前进到下一页")
    return {"success": True, "message": "成功前进到下一页"}


@tool
def refresh_page() -> dict[str, Any]:
    """刷新当前页面"""
    print("    🔄 刷新页面")
    return {"success": True, "message": "成功刷新页面"}


# ==================== 交互工具 ====================

@tool
async def real_click(
    target: str,
    humanize: bool = True,
    double_click: bool = False
) -> dict[str, Any]:
    """
    真实浏览器点击元素

    Args:
        target: 目标元素的描述
        humanize: 是否模拟真人操作
        double_click: 是否双击

    Returns:
        点击结果字典
    """
    engine = await get_web_engine()

    click_type = "双击" if double_click else "单击"
    humanize_str = "（真人模式）" if humanize else "（直接模式）"

    print(f"    🖱️  {click_type}: {target} {humanize_str}")

    try:
        # 查找文本位置
        position = await engine.find_text_position(target)
        if position:
            x, y = position

            if double_click:
                await engine.double_click(x, y)
            else:
                await engine.click(x, y)

            return {
                "success": True,
                "action": f"{click_type}了元素: {target}",
                "message": f"成功{click_type}: {target}",
                "element": target,
                "position": {"x": x, "y": y}
            }
        else:
            return {
                "success": False,
                "error": f"找不到元素: {target}",
                "message": f"点击失败: 找不到元素 '{target}'"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"点击失败: {str(e)}"
        }


@tool
async def real_type(
    target: str,
    text: str,
    humanize: bool = True,
    clear_first: bool = True
) -> dict[str, Any]:
    """
    真实浏览器输入文本

    Args:
        target: 目标元素的描述
        text: 要输入的文本
        humanize: 是否模拟真人输入
        clear_first: 是否先清空

    Returns:
        输入结果字典
    """
    engine = await get_web_engine()

    humanize_str = "（真人模式）" if humanize else "（快速模式）"
    clear_str = "（先清空）" if clear_first else "（不清空）"

    print(f"    ⌨️  输入: {text} 到 {target} {humanize_str} {clear_str}")

    try:
        # 查找目标元素位置
        position = await engine.find_text_position(target)
        if position:
            x, y = position

            # 点击目标位置以获得焦点
            await engine.click(x, y)

            # 如果需要先清空，发送 Ctrl+A 然后删除
            if clear_first:
                await engine.key_combo("ctrl+a")
                await engine.press_key("delete")

            # 输入文本
            await engine.type_text(text, humanize=humanize)

            return {
                "success": True,
                "action": f"输入文本到: {target}",
                "text": text,
                "message": f"成功输入 '{text}' 到 {target}",
                "element": target,
                "position": {"x": x, "y": y}
            }
        else:
            return {
                "success": False,
                "error": f"找不到输入框: {target}",
                "message": f"输入失败: 找不到输入框 '{target}'"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"输入失败: {str(e)}"
        }


# ==================== 验证工具 ====================

@tool
async def verify_text_visible(
    expected_text: str,
    timeout: int = 5000
) -> dict[str, Any]:
    """
    真实浏览器验证文本可见

    Args:
        expected_text: 期望看到的文本
        timeout: 超时时间

    Returns:
        验证结果字典
    """
    engine = await get_web_engine()

    print(f"    ✅ 验证文本可见: {expected_text}")

    try:
        # 检查文本是否在页面上可见
        position = await engine.find_text_position(expected_text)
        page_text = await engine.get_page_text()

        is_visible = position is not None and expected_text in page_text

        return {
            "success": is_visible,
            "assertion": f"文本{'可见' if is_visible else '不可见'}: {expected_text}",
            "message": f"{'成功验证' if is_visible else '验证失败'}文本: {expected_text}",
            "expected_text": expected_text,
            "found": is_visible,
            "position": {"x": position[0], "y": position[1]} if position else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"验证失败: {str(e)}"
        }


# ==================== 工具集导出 ====================

def get_real_browser_tools() -> list:
    """
    获取真实浏览器工具集

    Returns:
        工具列表
    """
    return [
        # 导航工具
        real_navigate,
        go_back,
        go_forward,
        refresh_page,

        # 交互工具
        real_click,
        real_type,

        # 验证工具
        verify_text_visible,
    ]


async def cleanup_browser():
    """清理浏览器资源"""
    await close_web_engine()