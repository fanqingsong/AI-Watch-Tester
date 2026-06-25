"""
AWT Simple Tools - 简化的工具集实现

这是一个简化但功能完整的工具实现，专注于核心功能。
随着发展，可以集成真实的浏览器操作和元素定位。
"""

from langchain_core.tools import tool
from typing import Dict, Any, Optional
import asyncio
import json


# ==================== 导航工具 ====================

@tool
async def simple_navigate(
    url: str,
    wait_for_load: bool = True,
    timeout: int = 30000
) -> Dict[str, Any]:
    """
    简化的导航工具

    Args:
        url: 目标URL
        wait_for_load: 是否等待页面加载
        timeout: 超时时间

    Returns:
        导航结果
    """
    await asyncio.sleep(0.5)  # 模拟导航时间

    print(f"    📍 导航到: {url}")

    return {
        "success": True,
        "url": url,
        "message": f"成功导航到 {url}",
        "page_info": {
            "title": f"页面标题 - {url}",
            "url": url
        }
    }


@tool
async def simple_click(
    target: str,
    humanize: bool = True,
    timeout: int = 10000
) -> Dict[str, Any]:
    """
    简化的点击工具

    Args:
        target: 目标元素描述
        humanize: 是否模拟真人操作
        timeout: 超时时间

    Returns:
        点击结果
    """
    await asyncio.sleep(0.3)  # 模拟点击操作

    print(f"    🖱️  点击: {target}")

    return {
        "success": True,
        "message": f"成功点击: {target}",
        "element": target,
        "action": "click"
    }


@tool
async def simple_type(
    target: str,
    text: str,
    clear_first: bool = True,
    humanize: bool = True
) -> Dict[str, Any]:
    """
    简化的输入工具

    Args:
        target: 目标元素描述
        text: 输入文本
        clear_first: 是否先清空
        humanize: 是否模拟真人输入

    Returns:
        输入结果
    """
    await asyncio.sleep(0.4)  # 模拟输入时间

    print(f"    ⌨️  输入: {text} 到 {target}")

    return {
        "success": True,
        "message": f"成功输入 '{text}' 到 {target}",
        "element": target,
        "text": text,
        "action": "type"
    }


@tool
async def simple_verify(
    target: str,
    expected_value: Optional[str] = None,
    timeout: int = 5000
) -> Dict[str, Any]:
    """
    简化的验证工具

    Args:
        target: 验证目标
        expected_value: 期望值
        timeout: 超时时间

    Returns:
        验证结果
    """
    await asyncio.sleep(0.2)  # 模拟验证时间

    print(f"    🔍 验证: {target}")

    # 简化的验证逻辑
    if "错误" in target.lower():
        # 模拟一些验证失败
        import random
        if random.random() < 0.3:  # 30% 失败率
            return {
                "success": False,
                "error": f"验证失败: 未找到期望的 '{expected_value}'",
                "target": target,
                "expected": expected_value
            }

    return {
        "success": True,
        "message": f"验证成功: 找到 {target}",
        "target": target,
        "expected": expected_value,
        "action": "verify"
    }


@tool
async def simple_analyze(
    analysis_depth: str = "basic"
) -> Dict[str, Any]:
    """
    简化的页面分析工具

    Args:
        analysis_depth: 分析深度

    Returns:
        页面分析结果
    """
    await asyncio.sleep(1)  # 模拟分析时间

    print(f"    🔬 分析页面结构")

    # 模拟分析结果
    return {
        "success": True,
        "analysis": {
            "page_title": "示例页面",
            "interactive_elements": [
                {"type": "button", "text": "提交", "id": "submit-btn"},
                {"type": "input", "placeholder": "用户名", "id": "username"},
                {"type": "input", "placeholder": "密码", "id": "password", "type": "password"}
            ],
            "navigation": [
                {"text": "首页", "url": "/home"},
                {"text": "关于", "url": "/about"},
                {"text": "联系", "url": "/contact"}
            ],
            "forms": [
                {"id": "login-form", "fields": ["username", "password"]}
            ]
        },
        "message": "页面分析完成"
    }


@tool
async def simple_screenshot(
    filename: Optional[str] = None,
    full_page: bool = False
) -> Dict[str, Any]:
    """
    简化的截图工具

    Args:
        filename: 文件名
        full_page: 是否全页面截图

    Returns:
        截图结果
    """
    await asyncio.sleep(0.1)  # 模拟截图时间

    if not filename:
        from datetime import datetime
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    print(f"    📸 截图: {filename}")

    return {
        "success": True,
        "message": f"截图保存成功: {filename}",
        "filename": filename,
        "path": f"/screenshots/{filename}"
    }


@tool
async def simple_wait(
    element: str,
    timeout: int = 10000,
    state: str = "visible"
) -> Dict[str, Any]:
    """
    简化的等待工具

    Args:
        element: 等待的元素
        timeout: 超时时间
        state: 等待状态

    Returns:
        等待结果
    """
    wait_time = min(timeout / 1000, 2)  # 最多等待2秒
    await asyncio.sleep(wait_time)

    print(f"    ⏱️  等待元素: {element}")

    return {
        "success": True,
        "message": f"元素 {element} 已出现",
        "element": element,
        "wait_time": wait_time
    }


@tool
async def simple_select(
    target: str,
    value: str
) -> Dict[str, Any]:
    """
    简化的选择工具

    Args:
        target: 下拉框描述
        value: 选择的值

    Returns:
        选择结果
    """
    await asyncio.sleep(0.3)

    print(f"    🎯 选择: {value} 从 {target}")

    return {
        "success": True,
        "message": f"成功选择 '{value}' 从 {target}",
        "element": target,
        "value": value,
        "action": "select"
    }


@tool
async def simple_console_check(
    level: str = "error"
) -> Dict[str, Any]:
    """
    简化的控制台检查工具

    Args:
        level: 检查级别

    Returns:
        控制台检查结果
    """
    await asyncio.sleep(0.1)

    print(f"    🔧 检查控制台 ({level})")

    # 模拟检查结果
    return {
        "success": True,
        "console_info": {
            "errors": [],
            "warnings": [],
            "info": ["页面加载完成", "资源加载成功"]
        },
        "message": "控制台检查完成"
    }


def get_simple_tools() -> list:
    """
    获取简化的工具集

    Returns:
        工具列表
    """
    return [
        simple_navigate,
        simple_click,
        simple_type,
        simple_verify,
        simple_analyze,
        simple_screenshot,
        simple_wait,
        simple_select,
        simple_console_check
    ]


def get_tool_by_name(tool_name: str):
    """
    根据名称获取工具

    Args:
        tool_name: 工具名称

    Returns:
        工具函数
    """
    tools = get_simple_tools()
    for tool in tools:
        if tool.name == tool_name:
            return tool
    return None


# 工具使用统计
class ToolUsageTracker:
    """工具使用跟踪器"""

    def __init__(self):
        self.usage_stats = {}
        self.call_history = []

    def record_usage(self, tool_name: str, success: bool, execution_time: float):
        """记录工具使用"""
        if tool_name not in self.usage_stats:
            self.usage_stats[tool_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_time": 0,
                "avg_time": 0
            }

        stats = self.usage_stats[tool_name]
        stats["total_calls"] += 1
        if success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1

        stats["total_time"] += execution_time
        stats["avg_time"] = stats["total_time"] / stats["total_calls"]

        self.call_history.append({
            "tool": tool_name,
            "success": success,
            "time": execution_time,
            "timestamp": asyncio.get_event_loop().time()
        })

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.usage_stats

    def get_most_used_tools(self, limit: int = 5) -> list:
        """获取最常用的工具"""
        sorted_tools = sorted(
            self.usage_stats.items(),
            key=lambda x: x[1]["total_calls"],
            reverse=True
        )
        return sorted_tools[:limit]


# 全局工具跟踪器
tool_tracker = ToolUsageTracker()


async def execute_tool_with_tracking(
    tool_name: str,
    *args,
    **kwargs
) -> Dict[str, Any]:
    """
    执行工具并跟踪使用情况

    Args:
        tool_name: 工具名称
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        工具执行结果
    """
    tool = get_tool_by_name(tool_name)
    if not tool:
        return {
            "success": False,
            "error": f"工具不存在: {tool_name}"
        }

    import time
    start_time = time.time()

    try:
        result = await tool.func(*args, **kwargs)
        execution_time = time.time() - start_time

        tool_tracker.record_usage(
            tool_name,
            result.get("success", True),
            execution_time
        )

        return result

    except Exception as e:
        execution_time = time.time() - start_time
        tool_tracker.record_usage(tool_name, False, execution_time)

        return {
            "success": False,
            "error": str(e)
        }