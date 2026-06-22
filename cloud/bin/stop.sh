#!/bin/bash
# AI-Watch-Tester Docker Compose 停止脚本
# 提供优雅停止、清理选项、状态确认等功能

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 切换到项目根目录
cd "$PROJECT_ROOT" || exit 1

# 加载工具函数库
# shellcheck source=bin/utils.sh
source "$SCRIPT_DIR/utils.sh"

# 默认参数
REMOVE_VOLUMES=false
FORCE=false
CONFIRM=true

# 显示帮助信息
show_help() {
    cat << EOF
AI-Watch-Tester Docker Compose 停止脚本

用法: $0 [选项]

选项:
  --volumes        同时删除数据卷（.aat目录）
  --force          强制停止，不进行确认
  -y, --yes        自动确认所有提示
  -h, --help       显示此帮助信息

说明:
  默认情况下，脚本会停止服务但保留数据卷。
  使用 --volumes 选项会删除所有数据，包括测试结果和学习数据。

示例:
  $0              # 正常停止（保留数据）
  $0 --volumes    # 停止并删除数据
  $0 --force      # 强制停止

EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --volumes)
                REMOVE_VOLUMES=true
                shift
                ;;
            --force)
                FORCE=true
                CONFIRM=false
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

# 检查服务状态
check_service_status() {
    local compose_cmd=$(get_compose_cmd)
    local status=$($compose_cmd ps -a aat 2>/dev/null | grep -q "Up" && echo "running" || echo "stopped")

    if [[ "$status" == "stopped" ]]; then
        log_warn "服务未运行"
        return 1
    fi

    return 0
}

# 显示当前状态
show_current_status() {
    local compose_cmd=$(get_compose_cmd)
    local container_status=$(get_container_status)
    local uptime=$(get_container_uptime)

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "           🤖 AI-Watch-Tester 当前状态"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo -e "📊 容器状态:    ${COLOR_YELLOW}${container_status}${COLOR_RESET}"
    echo -e "⏰ 运行时间:    ${COLOR_WHITE}${uptime}${COLOR_RESET}"
    echo ""
    echo "───────────────────────────────────────────────────────────────"
    echo ""
}

# 停止服务
stop_service() {
    local compose_cmd=$(get_compose_cmd)

    log_info "停止AI-Watch-Tester服务..."

    # 确认停止（除非强制模式）
    if [[ "$CONFIRM" == "true" ]]; then
        if ! confirm_action "确认停止服务？"; then
            log_info "取消停止操作"
            exit 0
        fi
    fi

    # 警告数据删除
    if [[ "$REMOVE_VOLUMES" == "true" ]] && [[ "$CONFIRM" == "true" ]]; then
        echo ""
        log_warn "⚠️  警告：此操作将删除所有数据，包括："
        echo "   • 测试结果 (.aat/)"
        echo "   • 学习数据"
        echo "   • 基线数据"
        echo ""
        if ! confirm_action "确认删除所有数据？此操作不可恢复！"; then
            log_info "取消停止操作"
            exit 0
        fi
    fi

    # 停止服务
    cd "$PROJECT_ROOT" || exit 1

    if [[ "$REMOVE_VOLUMES" == "true" ]]; then
        log_info "停止服务并删除数据..."
        $compose_cmd down -v || {
            log_error "停止服务失败"
            exit 1
        }
    else
        log_info "停止服务（保留数据）..."
        $compose_cmd stop || {
            log_error "停止服务失败"
            exit 1
        }
    fi

    log_success "服务已停止"
}

# 显示停止后状态
show_stopped_status() {
    local compose_cmd=$(get_compose_cmd)

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "           🤖 AI-Watch-Tester 已停止"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    # 检查容器状态
    local container_status=$($compose_cmd ps -a ai-watch-tester 2>/dev/null | grep -q "Exited" && echo "stopped" || echo "removed")

    if [[ "$REMOVE_VOLUMES" == "true" ]]; then
        echo -e "${COLOR_RED}🗑️  数据已删除${COLOR_RESET}"
        echo -e "   • 测试结果"
        echo -e "   • 学习数据"
        echo -e "   • 基线数据"
    else
        echo -e "${COLOR_GREEN}💾 数据已保留${COLOR_RESET}"
        echo -e "   • 测试结果"
        echo -e "   • 学习数据"
        echo -e "   • 基线数据"
    fi

    echo ""
    echo "───────────────────────────────────────────────────────────────"
    echo "💡 常用命令:"
    echo "  重新启动:   bin/start.sh"
    echo "  查看状态:   bin/status.sh"
    echo "  完全清理:   bin/stop.sh --volumes"
    echo "───────────────────────────────────────────────────────────────"
    echo ""
}

# 主函数
main() {
    # 解析参数
    parse_args "$@"

    # 显示停止信息
    echo ""
    echo "🛑 停止 AI-Watch-Tester"
    echo ""

    # 检查服务状态
    if ! check_service_status; then
        # 服务未运行，但可能需要清理
        local compose_cmd=$(get_compose_cmd)
        if $compose_cmd ps -a ai-watch-tester 2>/dev/null | grep -q "Exited"; then
            log_info "清理已停止的容器..."
            if [[ "$REMOVE_VOLUMES" == "true" ]]; then
                $compose_cmd down -v
            else
                $compose_cmd rm -f
            fi
            log_success "清理完成"
        fi
        exit 0
    fi

    # 显示当前状态
    show_current_status

    # 停止服务
    stop_service

    # 显示停止后状态
    show_stopped_status

    log_success "操作完成！"
}

# 执行主函数
main "$@"