#!/bin/bash
# AI-Watch-Tester Docker Compose 日志查看脚本
# 提供实时日志跟踪、历史查询、错误过滤等功能

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 切换到项目根目录
cd "$PROJECT_ROOT" || exit 1

# 加载工具函数库
# shellcheck source=bin/utils.sh
source "$SCRIPT_DIR/utils.sh"

# 默认参数
FOLLOW=false
TAIL_LINES=100
FILTER_ERRORS=false
EXPORT=false

# 显示帮助信息
show_help() {
    cat << EOF
AI-Watch-Tester Docker Compose 日志查看脚本

用法: $0 [选项]

选项:
  -f, --follow     实时跟踪日志（类似tail -f）
  -n, --tail N     显示最后N行日志（默认: 100）
  -e, --errors      仅显示错误日志
  --export FILE     将日志导出到文件
  -h, --help       显示此帮助信息

示例:
  $0              # 查看最近100行日志
  $0 -f           # 实时跟踪日志
  $0 -n 50        # 查看最近50行日志
  $0 -e           # 仅显示错误日志
  $0 --export log.txt  # 导出日志到文件

EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--follow)
                FOLLOW=true
                shift
                ;;
            -n|--tail)
                TAIL_LINES="$2"
                shift 2
                ;;
            -e|--errors)
                FILTER_ERRORS=true
                shift
                ;;
            --export)
                EXPORT=true
                EXPORT_FILE="$2"
                shift 2
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
check_service() {
    local compose_cmd=$(get_compose_cmd)
    local container_name=$($compose_cmd ps -q aat 2>/dev/null)

    if [[ -z "$container_name" ]]; then
        log_error "服务未运行"
        log_info "使用 bin/start.sh 启动服务"
        exit 1
    fi
}

# 显示实时日志
show_follow_logs() {
    local compose_cmd=$(get_compose_cmd)

    log_info "实时跟踪日志（按Ctrl+C退出）..."
    echo ""

    if [[ "$FILTER_ERRORS" == "true" ]]; then
        $compose_cmd logs -f aat 2>&1 | grep -i --line-buffered "error\|exception\|fail"
    else
        $compose_cmd logs -f aat
    fi
}

# 显示历史日志
show_history_logs() {
    local compose_cmd=$(get_compose_cmd)

    log_info "查看最近 ${TAIL_LINES} 行日志..."
    echo ""

    if [[ "$FILTER_ERRORS" == "true" ]]; then
        $compose_cmd logs --tail=$TAIL_LINES aat 2>&1 | grep -i "error\|exception\|fail"
    else
        $compose_cmd logs --tail=$TAIL_LINES aat
    fi
}

# 导出日志
export_logs() {
    local compose_cmd=$(get_compose_cmd)
    local export_file="${EXPORT_FILE:-aat-logs-$(date +%Y%m%d-%H%M%S).txt}"

    log_info "导出日志到: $export_file"

    if [[ "$FILTER_ERRORS" == "true" ]]; then
        $compose_cmd logs aat 2>&1 | grep -i "error\|exception\|fail" > "$export_file"
    else
        $compose_cmd logs aat > "$export_file" 2>&1
    fi

    if [[ $? -eq 0 ]]; then
        local log_size=$(du -h "$export_file" | cut -f1)
        log_success "日志已导出: $export_file (${log_size})"
    else
        log_error "日志导出失败"
        exit 1
    fi
}

# 显示日志统计
show_log_stats() {
    local compose_cmd=$(get_compose_cmd)

    echo ""
    echo "📊 日志统计"
    echo "───────────────────────────────────────────────────────────────"

    # 获取日志
    local logs=$($compose_cmd logs --tail=1000 aat 2>/dev/null)

    if [[ -z "$logs" ]]; then
        echo "暂无日志"
        return
    fi

    # 统计信息
    local total_lines=$(echo "$logs" | wc -l)
    local error_lines=$(echo "$logs" | grep -ci "error\|exception\|fail")
    local warning_lines=$(echo "$logs" | grep -ci "warn")

    echo -e "总行数:        ${COLOR_WHITE}${total_lines}${COLOR_RESET}"
    echo -e "错误数:        ${COLOR_RED}${error_lines}${COLOR_RESET}"
    echo -e "警告数:        ${COLOR_YELLOW}${warning_lines}${COLOR_RESET}"

    # 最近错误
    local recent_errors=$(echo "$logs" | grep -i "error\|exception\|fail" | tail -5)
    if [[ -n "$recent_errors" ]]; then
        echo ""
        echo "最近的错误/失败:"
        echo "$recent_errors"
    fi

    echo "───────────────────────────────────────────────────────────────"
}

# 主函数
main() {
    # 解析参数
    parse_args "$@"

    # 显示日志查看信息
    echo ""
    echo "📋 AI-Watch-Tester 日志查看"
    echo ""

    # 检查服务状态
    check_service

    # 执行相应操作
    if [[ "$EXPORT" == "true" ]]; then
        export_logs
    elif [[ "$FOLLOW" == "true" ]]; then
        show_follow_logs
    else
        show_history_logs
        show_log_stats
    fi

    echo ""
    echo "───────────────────────────────────────────────────────────────"
    echo "💡 常用命令:"
    echo "  实时日志:   bin/logs.sh -f"
    echo "  查看状态:   bin/status.sh"
    echo "  停止服务:   bin/stop.sh"
    echo "───────────────────────────────────────────────────────────────"
    echo ""
}

# 执行主函数
main "$@"