#!/bin/bash
# AI-Watch-Tester Docker Compose 管理工具函数库
# 提供通用的日志输出、状态检查、环境验证等功能

# 颜色定义
readonly COLOR_RED='\033[0;31m'
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_YELLOW='\033[1;33m'
readonly COLOR_BLUE='\033[0;34m'
readonly COLOR_PURPLE='\033[0;35m'
readonly COLOR_CYAN='\033[0;36m'
readonly COLOR_WHITE='\033[1;37m'
readonly COLOR_RESET='\033[0m'

# 日志输出函数
log_info() {
    echo -e "${COLOR_CYAN}ℹ${COLOR_RESET} $*"
}

log_success() {
    echo -e "${COLOR_GREEN}✅${COLOR_RESET} $*"
}

log_warn() {
    echo -e "${COLOR_YELLOW}⚠️${COLOR_RESET} $*"
}

log_error() {
    echo -e "${COLOR_RED}❌${COLOR_RESET} $*"
}

log_debug() {
    if [[ "${DEBUG:-0}" == "1" ]]; then
        echo -e "${COLOR_PURPLE}🔍${COLOR_RESET} $*"
    fi
}

# 检查Docker是否运行
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        return 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker未运行，请启动Docker服务"
        return 1
    fi

    return 0
}

# 获取Docker Compose命令
get_compose_cmd() {
    if docker compose version &> /dev/null 2>&1; then
        echo "docker compose"
    else
        echo "docker-compose"
    fi
}

# 检查端口是否可用
check_port() {
    local port=${1:-9500}
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1
    fi
    return 0
}

# 获取占用端口的进程信息
get_port_process() {
    local port=${1:-9500}
    lsof -Pi :$port -sTCP:LISTEN 2>/dev/null | tail -n +2
}

# 检查容器状态
get_container_status() {
    local compose_cmd=$(get_compose_cmd)
    local container_name=$($compose_cmd ps -q aat 2>/dev/null)

    if [[ -z "$container_name" ]]; then
        # Try direct container name lookup
        container_name=$(docker ps -q -f name=ai-watch-tester 2>/dev/null)
        if [[ -z "$container_name" ]]; then
            echo "not_created"
            return 0
        fi
    fi

    local status=$(docker inspect -f '{{.State.Status}}' $container_name 2>/dev/null)
    echo "$status"
}

# 等待服务启动
wait_for_service() {
    local max_wait=${1:-60}
    local check_interval=${2:-2}
    local elapsed=0

    log_info "等待服务启动..."

    while [[ $elapsed -lt $max_wait ]]; do
        if curl -s -f http://localhost:9500 >/dev/null 2>&1; then
            log_success "服务启动成功"
            return 0
        fi

        echo -n "."
        sleep $check_interval
        elapsed=$((elapsed + check_interval))
    done

    echo ""
    log_error "服务启动超时"
    return 1
}

# 检查服务健康状态
check_service_health() {
    local compose_cmd=$(get_compose_cmd)
    local container_name=$($compose_cmd ps -q aat 2>/dev/null)

    if [[ -z "$container_name" ]]; then
        # Try direct container name lookup
        container_name=$(docker ps -q -f name=ai-watch-tester 2>/dev/null)
        if [[ -z "$container_name" ]]; then
            echo "unknown"
            return 0
        fi
    fi

    local health=$(docker inspect -f '{{.State.Health.Status}}' $container_name 2>/dev/null)

    if [[ -z "$health" ]]; then
        # 容器没有健康检查
        local running=$(docker inspect -f '{{.State.Running}}' $container_name 2>/dev/null)
        if [[ "$running" == "true" ]]; then
            echo "healthy"
        else
            echo "unhealthy"
        fi
    else
        echo "$health"
    fi
}

# 获取容器运行时间
get_container_uptime() {
    local compose_cmd=$(get_compose_cmd)
    local container_name=$($compose_cmd ps -q aat 2>/dev/null)

    if [[ -z "$container_name" ]]; then
        # Try direct container name lookup
        container_name=$(docker ps -q -f name=ai-watch-tester 2>/dev/null)
        if [[ -z "$container_name" ]]; then
            echo "N/A"
            return 0
        fi
    fi

    local started=$(docker inspect -f '{{.State.StartedAt}}' $container_name 2>/dev/null)
    if [[ -n "$started" ]]; then
        local now=$(date -u +"%Y-%m-%dT%H:%M:%S")
        local uptime=$(( $(date -d "$now" +%s) - $(date -d "$started" +%s) ))

        if [[ $uptime -gt 86400 ]]; then
            echo "$((uptime / 86400))天"
        elif [[ $uptime -gt 3600 ]]; then
            echo "$((uptime / 3600))小时"
        elif [[ $uptime -gt 60 ]]; then
            echo "$((uptime / 60))分钟"
        else
            echo "${uptime}秒"
        fi
    else
        echo "N/A"
    fi
}

# 获取容器资源使用情况
get_container_resources() {
    local compose_cmd=$(get_compose_cmd)
    local container_name=$($compose_cmd ps -q aat 2>/dev/null)

    if [[ -z "$container_name" ]]; then
        # Try direct container name lookup
        container_name=$(docker ps -q -f name=ai-watch-tester 2>/dev/null)
        if [[ -z "$container_name" ]]; then
            echo "CPU: N/A | 内存: N/A"
            return 0
        fi
    fi

    local stats=$(docker stats --no-stream --format "CPU: {{.CPUPerc}} | 内存: {{.MemUsage}}" $container_name 2>/dev/null)
    echo "${stats:-CPU: N/A | 内存: N/A}"
}

# 检查环境变量
check_env_vars() {
    # 检查可选的AI API密钥
    if [[ -z "${ANTHROPIC_API_KEY:-}" && -z "${OPENAI_API_KEY:-}" && -z "${ZHIPUAI_API_KEY:-}" ]]; then
        log_warn "未设置AI API密钥 (ANTHROPIC_API_KEY, OPENAI_API_KEY, 或 ZHIPUAI_API_KEY)"
        log_warn "AI功能将不可用"
    fi

    return 0
}

# 加载.env文件
load_env_file() {
    if [[ -f ".env" ]]; then
        log_debug "加载.env文件"
        set -a
        source .env
        set +a
    fi
}

# 确认提示
confirm_action() {
    local message=$1
    local default=${2:-n}

    if [[ "$default" == "y" ]]; then
        local prompt="[Y/n]"
    else
        local prompt="[y/N]"
    fi

    read -p "$message $prompt " -n 1 -r response
    echo

    if [[ -z "$response" ]]; then
        response=$default
    fi

    if [[ "$response" =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}