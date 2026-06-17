#!/bin/bash
# AI-Watch-Tester Docker Compose 状态查询脚本
# 提供容器状态、资源使用、服务访问性等信息

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 切换到项目根目录
cd "$PROJECT_ROOT" || exit 1

# 加载工具函数库
# shellcheck source=bin/utils.sh
source "$SCRIPT_DIR/utils.sh"

# 默认参数
SHOW_DETAILED=false
CHECK_ACCESSIBILITY=true

# 显示帮助信息
show_help() {
    cat << EOF
AI-Watch-Tester Docker Compose 状态查询脚本

用法: $0 [选项]

选项:
  -d, --detailed    显示详细信息
  --no-access      不检查服务访问性
  -h, --help       显示此帮助信息

示例:
  $0              # 基本状态
  $0 --detailed   # 详细状态

EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--detailed)
                SHOW_DETAILED=true
                shift
                ;;
            --no-access)
                CHECK_ACCESSIBILITY=false
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 显示容器基本信息
show_container_info() {
    local compose_cmd=$(get_compose_cmd)
    local container_name=$($compose_cmd ps -q aat 2>/dev/null)

    if [[ -z "$container_name" ]]; then
        # Try direct container name lookup as fallback
        container_name=$(docker ps -q -f name=ai-watch-tester 2>/dev/null)
        if [[ -z "$container_name" ]]; then
            echo -e "📊 容器状态:    ${COLOR_RED}未创建${COLOR_RESET}"
            return 1
        fi
    fi

    local container_status=$(get_container_status)
    local service_health=$(check_service_health)
    local uptime=$(get_container_uptime)

    echo -e "📊 容器状态:    ${COLOR_GREEN}${container_status}${COLOR_RESET}"
    echo -e "🏥 健康检查:    ${COLOR_GREEN}${service_health}${COLOR_RESET}"
    echo -e "⏰ 运行时间:    ${COLOR_WHITE}${uptime}${COLOR_RESET}"
}

# 显示资源使用情况
show_resource_usage() {
    local resources=$(get_container_resources)
    echo -e "💻 资源使用:    ${COLOR_WHITE}${resources}${COLOR_RESET}"
}

# 显示网络信息
show_network_info() {
    local compose_cmd=$(get_compose_cmd)
    local port_info=$($compose_cmd ps aat 2>/dev/null | grep "0.0.0.0:9500")

    if [[ -n "$port_info" ]]; then
        echo -e "🌐 端口映射:    ${COLOR_GREEN}0.0.0.0:9500->9500/tcp${COLOR_RESET}"
        echo -e "🔗 访问地址:    ${COLOR_CYAN}http://localhost:9500${COLOR_RESET}"
    else
        echo -e "🌐 端口映射:    ${COLOR_RED}未映射${COLOR_RESET}"
    fi
}

# 检查服务访问性
check_service_accessibility() {
    if [[ "$CHECK_ACCESSIBILITY" == "false" ]]; then
        return 0
    fi

    local start_time=$(date +%s)
    if curl -s -f -o /dev/null -w "%{http_code}" http://localhost:9500 >/dev/null 2>&1; then
        local end_time=$(date +%s)
        local response_time=$((end_time - start_time))
        echo -e "✅ 服务状态:    ${COLOR_GREEN}可访问${COLOR_RESET} (${response_time}s)"
    else
        echo -e "❌ 服务状态:    ${COLOR_RED}不可访问${COLOR_RESET}"
    fi
}

# 显示Docker信息
show_docker_info() {
    echo ""
    echo "🐋 Docker信息:"
    echo -e "   版本:        ${COLOR_WHITE}$(docker --version | cut -d' ' -f3)${COLOR_RESET}"
    echo -e "   Compose:     ${COLOR_WHITE}$($(get_compose_cmd) version --short)${COLOR_RESET}"

    local compose_cmd=$(get_compose_cmd)
    local container_name=$($compose_cmd ps -q ai-watch-tester 2>/dev/null)
    if [[ -n "$container_name" ]]; then
        local image=$(docker inspect -f '{{.Config.Image}}' $container_name 2>/dev/null)
        echo -e "   镜像:        ${COLOR_WHITE}${image}${COLOR_RESET}"
    fi
}

# 显示环境配置
show_env_config() {
    echo ""
    echo "⚙️  环境配置:"

    if [[ -n "${ZHIPUAI_API_KEY:-}" ]]; then
        echo -e "   ${COLOR_GREEN}✓${COLOR_RESET} ZHIPUAI_API_KEY    (智谱AI)"
    fi
    if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
        echo -e "   ${COLOR_GREEN}✓${COLOR_RESET} ANTHROPIC_API_KEY  (Claude)"
    fi
    if [[ -n "${OPENAI_API_KEY:-}" ]]; then
        echo -e "   ${COLOR_GREEN}✓${COLOR_RESET} OPENAI_API_KEY     (GPT)"
    fi
    if [[ -n "${OLLAMA_BASE_URL:-}" ]]; then
        echo -e "   ${COLOR_GREEN}✓${COLOR_RESET} OLLAMA_BASE_URL     (本地LLM)"
    fi
}

# 显示主状态
show_main_status() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "           🤖 AI-Watch-Tester 服务状态"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    # 容器信息
    if ! show_container_info; then
        echo ""
        echo "───────────────────────────────────────────────────────────────"
        echo "💡 提示:"
        echo "  服务未启动，使用 bin/start.sh 启动服务"
        echo "───────────────────────────────────────────────────────────────"
        echo ""
        return 1
    fi

    echo ""

    # 资源使用
    show_resource_usage
    echo ""

    # 网络信息
    show_network_info
    echo ""

    # 服务访问性
    check_service_accessibility

    # 详细信息
    if [[ "$SHOW_DETAILED" == "true" ]]; then
        show_docker_info
        show_env_config
    fi

    echo ""
    echo "───────────────────────────────────────────────────────────────"
    echo "💡 常用命令:"
    echo "  启动服务:   bin/start.sh"
    echo "  停止服务:   bin/stop.sh"
    echo "  查看日志:   bin/logs.sh"
    echo "  重启服务:   bin/restart.sh"
    echo "───────────────────────────────────────────────────────────────"
    echo ""
}

# 主函数
main() {
    # 解析参数
    parse_args "$@"

    # 显示状态
    show_main_status
}

# 执行主函数
main "$@"