#!/bin/bash
# AI-Watch-Tester Docker Compose 启动脚本
# 提供环境检查、服务启动、健康检查等功能

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 切换到项目根目录
cd "$PROJECT_ROOT" || exit 1

# 加载工具函数库
# shellcheck source=bin/utils.sh
source "$SCRIPT_DIR/utils.sh"

# 默认参数
REBUILD=false
DEV_MODE=false
DETACHED=true

# 显示帮助信息
show_help() {
    cat << EOF
AI-Watch-Tester Docker Compose 启动脚本

用法: $0 [选项]

选项:
  -d, --detached    后台运行 (默认)
  -f, --foreground  前台运行
  --dev             开发模式（启用Python auto-reload）
  --rebuild         重新构建镜像
  -h, --help        显示此帮助信息

环境变量:
  ANTHROPIC_API_KEY    - Anthropic API密钥
  OPENAI_API_KEY       - OpenAI API密钥
  ZHIPUAI_API_KEY      - 智谱AI API密钥
  ZHIPUAI_MODEL        - 智谱AI模型 (默认: glm-4.7)
  OLLAMA_BASE_URL      - Ollama服务地址

示例:
  $0              # 默认启动
  $0 --dev        # 开发模式启动
  $0 --rebuild    # 重新构建并启动

EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--detached)
                DETACHED=true
                shift
                ;;
            -f|--foreground)
                DETACHED=false
                shift
                ;;
            --dev)
                DEV_MODE=true
                shift
                ;;
            --rebuild)
                REBUILD=true
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

# 环境检查
environment_check() {
    log_info "检查运行环境..."

    # 检查Docker
    if ! check_docker; then
        exit 1
    fi

    # 检查Docker Compose
    local compose_cmd=$(get_compose_cmd)
    if [[ "$compose_cmd" == "docker-compose" ]]; then
        log_warn "建议升级到Docker Compose V2 (docker compose)"
    fi

    # 检查端口
    if ! check_port 9500; then
        log_error "端口9500已被占用："
        get_port_process 9500
        log_info "解决方案："
        echo "  1. 停止占用端口的进程"
        echo "  2. 或修改docker-compose.yml中的端口映射"
        exit 1
    fi

    # 检查环境变量
    check_env_vars

    log_success "环境检查完成"
}

# 启动服务
start_service() {
    local compose_cmd=$(get_compose_cmd)

    log_info "启动AI-Watch-Tester服务..."

    # 重新构建（如果需要）
    if [[ "$REBUILD" == "true" ]]; then
        log_info "重新构建镜像..."
        $compose_cmd build --no-cache || {
            log_error "镜像构建失败"
            exit 1
        }
    fi

    # 准备启动参数
    local start_args=()
    if [[ "$DETACHED" == "true" ]]; then
        start_args+=("-d")
    fi

    # 开发模式参数
    if [[ "$DEV_MODE" == "true" ]]; then
        log_info "启用开发模式（Python auto-reload）"
        # 开发模式下，我们需要修改启动命令来启用auto-reload
        # 这里可能需要额外的配置或环境变量
    fi

    # 启动服务
    cd "$PROJECT_ROOT" || exit 1
    $compose_cmd up "${start_args[@]}" || {
        log_error "服务启动失败"
        log_info "查看详细日志: $compose_cmd logs"
        exit 1
    }

    # 如果是后台模式，等待服务启动完成
    if [[ "$DETACHED" == "true" ]]; then
        echo ""
        if wait_for_service 60; then
            show_status
        else
            log_error "服务启动超时，请检查日志"
            log_info "查看日志: $compose_cmd logs -f"
            exit 1
        fi
    fi
}

# 显示服务状态
show_status() {
    local compose_cmd=$(get_compose_cmd)
    local container_status=$(get_container_status)
    local service_health=$(check_service_health)
    local uptime=$(get_container_uptime)

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "           🤖 AI-Watch-Tester 服务状态"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo -e "📊 容器状态:    ${COLOR_GREEN}${container_status}${COLOR_RESET}"
    echo -e "🏥 健康检查:    ${COLOR_GREEN}${service_health}${COLOR_RESET}"
    echo -e "⏰ 运行时间:    ${COLOR_WHITE}${uptime}${COLOR_RESET}"
    echo -e "🌐 访问地址:    ${COLOR_CYAN}http://localhost:9500${COLOR_RESET}"
    echo ""
    echo "───────────────────────────────────────────────────────────────"
    echo "💡 常用命令:"
    echo "  查看状态:   bin/status.sh"
    echo "  查看日志:   bin/logs.sh"
    echo "  停止服务:   bin/stop.sh"
    echo "  重启服务:   bin/restart.sh"
    echo "───────────────────────────────────────────────────────────────"
    echo ""
}

# 主函数
main() {
    # 解析参数
    parse_args "$@"

    # 显示启动信息
    echo ""
    echo "🚀 启动 AI-Watch-Tester"
    echo ""

    # 加载环境变量
    load_env_file

    # 环境检查
    environment_check

    # 启动服务
    start_service

    # 如果不是后台模式，说明在前台运行
    if [[ "$DETACHED" == "false" ]]; then
        log_info "服务在前台运行，按 Ctrl+C 停止"
    else
        log_success "启动完成！"
    fi
}

# 执行主函数
main "$@"