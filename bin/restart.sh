#!/bin/bash
# AI-Watch-Tester Docker Compose 重启脚本
# 提供优雅重启、快速重启、状态验证等功能

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 切换到项目根目录
cd "$PROJECT_ROOT" || exit 1

# 加载工具函数库
# shellcheck source=bin/utils.sh
source "$SCRIPT_DIR/utils.sh"

# 默认参数
QUICK=false
CONFIRM=true

# 显示帮助信息
show_help() {
    cat << EOF
AI-Watch-Tester Docker Compose 重启脚本

用法: $0 [选项]

选项:
  --quick          快速重启（不重新构建）
  -y, --yes        自动确认所有提示
  -h, --help       显示此帮助信息

说明:
  默认使用优雅重启：停止服务 -> 启动服务 -> 验证状态
  快速重启：直接重启容器，最小化服务中断

示例:
  $0              # 优雅重启
  $0 --quick      # 快速重启

EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                QUICK=true
                shift
                ;;
            -y|--yes)
                CONFIRM=false
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

# 快速重启
quick_restart() {
    local compose_cmd=$(get_compose_cmd)

    log_info "执行快速重启..."

    # 确认重启
    if [[ "$CONFIRM" == "true" ]]; then
        if ! confirm_action "确认快速重启服务？"; then
            log_info "取消重启操作"
            exit 0
        fi
    fi

    # 记录重启前状态
    local before_status=$(get_container_status)
    local before_uptime=$(get_container_uptime)

    echo ""
    echo "重启前状态:"
    echo -e "  容器状态:    ${COLOR_YELLOW}${before_status}${COLOR_RESET}"
    echo -e "  运行时间:    ${COLOR_WHITE}${before_uptime}${COLOR_RESET}"
    echo ""

    # 执行快速重启
    cd "$PROJECT_ROOT" || exit 1
    $compose_cmd restart || {
        log_error "快速重启失败"
        exit 1
    }

    # 等待服务启动
    echo ""
    if wait_for_service 30; then
        show_restart_success
    else
        log_error "服务重启超时"
        log_info "查看日志: $compose_cmd logs -f"
        exit 1
    fi
}

# 优雅重启
graceful_restart() {
    log_info "执行优雅重启..."

    # 确认重启
    if [[ "$CONFIRM" == "true" ]]; then
        if ! confirm_action "确认重启服务？"; then
            log_info "取消重启操作"
            exit 0
        fi
    fi

    # 记录重启前状态
    local compose_cmd=$(get_compose_cmd)
    local before_status=$(get_container_status)
    local before_uptime=$(get_container_uptime)

    echo ""
    echo "重启前状态:"
    echo -e "  容器状态:    ${COLOR_YELLOW}${before_status}${COLOR_RESET}"
    echo -e "  运行时间:    ${COLOR_WHITE}${before_uptime}${COLOR_RESET}"
    echo ""

    # 停止服务
    log_info "停止服务..."
    "$SCRIPT_DIR/stop.sh" --yes || {
        log_error "停止服务失败"
        exit 1
    }

    # 等待停止完成
    sleep 2

    # 启动服务
    log_info "启动服务..."
    "$SCRIPT_DIR/start.sh" || {
        log_error "启动服务失败"
        exit 1
    }

    show_restart_success
}

# 显示重启成功信息
show_restart_success() {
    local compose_cmd=$(get_compose_cmd)
    local after_status=$(get_container_status)
    local after_uptime=$(get_container_uptime)
    local service_health=$(check_service_health)

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "           🤖 AI-Watch-Tester 重启成功"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo -e "📊 容器状态:    ${COLOR_GREEN}${after_status}${COLOR_RESET}"
    echo -e "🏥 健康检查:    ${COLOR_GREEN}${service_health}${COLOR_RESET}"
    echo -e "⏰ 运行时间:    ${COLOR_WHITE}${after_uptime}${COLOR_RESET}"
    echo -e "🌐 访问地址:    ${COLOR_CYAN}http://localhost:9500${COLOR_RESET}"
    echo ""
    echo "───────────────────────────────────────────────────────────────"
    echo "💡 常用命令:"
    echo "  查看状态:   bin/status.sh"
    echo "  查看日志:   bin/logs.sh"
    echo "  停止服务:   bin/stop.sh"
    echo "───────────────────────────────────────────────────────────────"
    echo ""
}

# 主函数
main() {
    # 解析参数
    parse_args "$@"

    # 显示重启信息
    echo ""
    echo "🔄 重启 AI-Watch-Tester"
    echo ""

    # 执行重启
    if [[ "$QUICK" == "true" ]]; then
        quick_restart
    else
        graceful_restart
    fi

    log_success "重启完成！"
}

# 执行主函数
main "$@"