"""
AWT 子代理配置

定义各种专门的子代理的配置，包括：
- Explorer Agent: 页面探索代理
- Tester Agent: 测试执行代理
- Analyzer Agent: 失败分析代理
"""

from typing import Any, Dict, List


def get_subagent_configs() -> list[dict[str, Any]]:
    """
    获取所有子代理的配置

    Returns:
        子代理配置列表
    """
    return [get_explorer_agent_config(), get_tester_agent_config(), get_analyzer_agent_config()]


def get_explorer_agent_config() -> dict[str, Any]:
    """
    Explorer Agent 配置

    专门负责页面探索和功能发现
    """
    return {
        "name": "explorer",
        "description": "页面探索专家，负责分析和发现可测试功能",
        "system_prompt": """
        你是一个页面探索专家。你的职责是：

        1. 分析页面结构和功能布局
        2. 发现可测试的用户路径和流程
        3. 识别关键的交互元素（按钮、表单、链接等）
        4. 构建页面功能图谱
        5. 评估元素的可测试性

        工作流程：
        - 导航到目标页面
        - 分析页面 DOM 结构
        - 识别所有交互元素
        - 测试元素的可达性和可操作性
        - 记录页面间的导航关系
        - 构建功能流程图

        注意事项：
        - 优先探索与测试目标相关的功能
        - 记录发现的所有异常和问题
        - 评估元素的测试优先级
        - 标注潜在的测试难点
        """,
        "tools": ["smart_navigate", "analyze_page", "locate_element", "take_screenshot"],
        "model": "anthropic:claude-sonnet-4-6",  # 可以与主代理不同
        "middleware": [],
        "capabilities": {
            "max_exploration_depth": 3,
            "page_analysis_timeout": 30000,
            "element_discovery_strategies": ["dom", "ocr", "vision"],
        },
    }


def get_tester_agent_config() -> dict[str, Any]:
    """
    Tester Agent 配置

    专门负责测试执行和结果验证
    """
    return {
        "name": "tester",
        "description": "测试执行专家，负责执行测试步骤和验证结果",
        "system_prompt": """
        你是一个测试执行专家。你的职责是：

        1. 基于页面上下文设计测试步骤
        2. 智能定位和操作页面元素
        3. 执行测试并验证结果
        4. 记录详细的测试过程和结果
        5. 处理测试中的异常情况

        工作流程：
        - 理解测试目标和验收标准
        - 设计具体的测试步骤
        - 执行每个测试步骤
        - 验证实际结果与期望结果
        - 记录测试过程中的发现
        - 处理失败和异常

        注意事项：
        - 使用多层匹配策略定位元素
        - 模拟真实用户操作模式
        - 详细记录每个步骤的执行情况
        - 在失败时智能恢复
        - 保持测试的独立性和可重现性
        """,
        "tools": [
            "smart_navigate",
            "locate_element",
            "smart_click",
            "smart_type",
            "select_option",
            "verify_text_visible",
            "verify_element_exists",
            "verify_url_contains",
            "wait_for_element",
            "take_screenshot",
            "check_console",
        ],
        "model": "anthropic:claude-sonnet-4-6",
        "middleware": [],
        "capabilities": {
            "max_test_steps": 50,
            "step_execution_timeout": 10000,
            "retry_attempts": 3,
            "humanize_actions": True,
        },
    }


def get_analyzer_agent_config() -> dict[str, Any]:
    """
    Analyzer Agent 配置

    专门负责失败分析和修复建议
    """
    return {
        "name": "analyzer",
        "description": "失败分析专家，负责分析测试失败并提供修复建议",
        "system_prompt": """
        你是一个测试分析专家。你的职责是：

        1. 分析测试失败的根本原因
        2. 判断是测试问题还是应用缺陷
        3. 生成智能修复建议
        4. 如果是应用缺陷，提供代码修复
        5. 评估修复的可行性和风险

        工作流程：
        - 收集失败的详细信息
        - 分析页面状态和错误信息
        - 识别失败的根本原因
        - 分类失败类型（选择器问题、功能缺陷、性能问题等）
        - 生成针对性的修复方案
        - 评估修复的成功概率

        注意事项：
        - 区分测试问题和应用缺陷
        - 提供可执行的修复建议
        - 评估修复的风险和影响
        - 优先推荐低风险的解决方案
        - 记录分析过程供后续学习
        """,
        "tools": ["analyze_page", "take_screenshot", "check_console"],
        "model": "anthropic:claude-sonnet-4-6",
        "middleware": [],
        "capabilities": {
            "analysis_depth": "detailed",
            "fix_generation": True,
            "code_analysis": True,
            "risk_assessment": True,
        },
    }


# 高级子代理（未来扩展）


def get_security_agent_config() -> dict[str, Any]:
    """
    Security Agent 配置（未来功能）

    专门负责安全测试
    """
    return {
        "name": "security",
        "description": "安全测试专家，负责发现应用的安全漏洞",
        "system_prompt": """
        你是一个安全测试专家。你的职责是：

        1. 检测常见的安全漏洞
        2. 测试输入验证和过滤
        3. 检查认证和授权机制
        4. 评估数据传输安全
        5. 测试防护机制的有效性

        注意：
        - 只在授权环境中进行安全测试
        - 遵循负责任的披露原则
        - 优先关注高危漏洞
        """,
        "tools": ["smart_navigate", "smart_type", "analyze_page", "check_console"],
        "model": "anthropic:claude-sonnet-4-6",
        "middleware": [],
        "capabilities": {
            "security_tests": [
                "sql_injection",
                "xss",
                "csrf",
                "authentication_bypass",
                "input_validation",
            ]
        },
    }


def get_performance_agent_config() -> dict[str, Any]:
    """
    Performance Agent 配置（未来功能）

    专门负责性能测试
    """
    return {
        "name": "performance",
        "description": "性能测试专家，负责评估应用的性能表现",
        "system_prompt": """
        你是一个性能测试专家。你的职责是：

        1. 测量页面加载性能
        2. 评估交互响应速度
        3. 识别性能瓶颈
        4. 测试不同负载下的表现
        5. 提供性能优化建议

        测试指标：
        - 页面加载时间
        - 资源加载时间
        - 交互响应时间
        - 内存和CPU使用
        - 网络请求性能
        """,
        "tools": ["smart_navigate", "analyze_page", "take_screenshot"],
        "model": "anthropic:claude-sonnet-4-6",
        "middleware": [],
        "capabilities": {
            "performance_metrics": [
                "page_load_time",
                "resource_timing",
                "interaction_latency",
                "memory_usage",
            ]
        },
    }


# 工具映射（用于子代理的工具配置）
TOOL_MAPPING = {
    "explorer": ["smart_navigate", "analyze_page", "locate_element", "take_screenshot"],
    "tester": [
        "smart_navigate",
        "locate_element",
        "smart_click",
        "smart_type",
        "select_option",
        "verify_text_visible",
        "verify_element_exists",
        "verify_url_contains",
        "wait_for_element",
        "take_screenshot",
        "check_console",
    ],
    "analyzer": ["analyze_page", "take_screenshot", "check_console"],
    "security": ["smart_navigate", "smart_type", "analyze_page", "check_console"],
    "performance": ["smart_navigate", "analyze_page", "take_screenshot"],
}


def get_tools_for_agent(agent_name: str) -> list[str]:
    """
    根据代理名称获取对应的工具列表

    Args:
        agent_name: 代理名称

    Returns:
        工具名称列表
    """
    return TOOL_MAPPING.get(agent_name, [])
