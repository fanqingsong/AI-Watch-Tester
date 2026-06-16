#!/bin/bash
# AWT Docker 快速启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否运行
check_docker() {
    if ! docker ps &>/dev/null; then
        print_error "Docker未运行，请先启动Docker"
        exit 1
    fi
    print_info "Docker运行正常"
}

# 检查镜像是否存在
check_image() {
    if ! docker images | grep -q "ai-watch-tester"; then
        print_warn "镜像不存在，开始构建..."
        docker build -t ai-watch-tester:latest .
        print_info "镜像构建完成"
    else
        print_info "镜像已存在"
    fi
}

# 显示菜单
show_menu() {
    echo ""
    echo "=== AWT Docker 快速启动 ==="
    echo "1) 交互式运行容器 (开发调试)"
    echo "2) 运行测试命令"
    echo "3) 启动Web Dashboard"
    echo "4) 查看容器日志"
    echo "5) 停止并删除容器"
    echo "6) 重新构建镜像"
    echo "0) 退出"
    echo ""
}

# 交互式运行
run_interactive() {
    print_info "启动交互式容器..."
    docker run -it --rm \
        --name aat \
        --network host \
        -v "$(pwd)/scenarios:/app/scenarios" \
        -v "$(pwd)/.aat:/app/.aat" \
        -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
        -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
        ai-watch-tester:latest bash
}

# 运行测试
run_test() {
    if [ -z "$1" ]; then
        read -p "输入测试场景路径 (默认: scenarios/): " scenario
        scenario=${scenario:-scenarios/}
    else
        scenario=$1
    fi
    
    print_info "运行测试: $scenario"
    docker run -it --rm \
        --name aat \
        --network host \
        -v "$(pwd)/scenarios:/app/scenarios" \
        -v "$(pwd)/.aat:/app/.aat" \
        -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
        -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
        ai-watch-tester:latest aat run "$scenario"
}

# 启动Dashboard
start_dashboard() {
    print_info "启动Web Dashboard..."
    docker run -d --name aat-web \
        --network host \
        -v "$(pwd)/scenarios:/app/scenarios" \
        -v "$(pwd)/.aat:/app/.aat" \
        -p 8000:8000 \
        ai-watch-tester:latest aat dashboard --host 0.0.0.0 --port 8000
    
    sleep 2
    print_info "Dashboard已启动: http://localhost:8000"
    docker logs aat-web --tail 20
}

# 查看日志
view_logs() {
    if docker ps | grep -q "aat"; then
        print_info "查看容器日志..."
        docker logs -f aat
    else
        print_warn "没有运行中的容器"
    fi
}

# 停止容器
stop_container() {
    print_info "停止并删除容器..."
    docker stop aat aat-web 2>/dev/null || true
    docker rm aat aat-web 2>/dev/null || true
    print_info "容器已清理"
}

# 重新构建
rebuild_image() {
    print_info "重新构建镜像..."
    docker build --no-cache -t ai-watch-tester:latest .
    print_info "镜像构建完成"
}

# 主函数
main() {
    check_docker
    check_image
    
    while true; do
        show_menu
        read -p "请选择操作 [0-6]: " choice
        
        case $choice in
            1) run_interactive ;;
            2) run_test ;;
            3) start_dashboard ;;
            4) view_logs ;;
            5) stop_container ;;
            6) rebuild_image ;;
            0) print_info "退出"; exit 0 ;;
            *) print_error "无效选择" ;;
        esac
        
        read -p "按Enter继续..."
    done
}

# 运行主函数
main
