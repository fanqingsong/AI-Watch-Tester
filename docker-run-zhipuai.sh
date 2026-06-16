#!/bin/bash
# 智谱AI专用快速启动脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查API密钥
if [ -z "$ZHIPUAI_API_KEY" ]; then
    print_error "ZHIPUAI_API_KEY 环境变量未设置"
    echo ""
    echo "请设置智谱AI API密钥："
    echo "  export ZHIPUAI_API_KEY=your_api_key_here"
    echo ""
    echo "或者创建 .env 文件："
    echo "  cp .env.zhipuai.example .env"
    echo "  # 编辑 .env 填入你的密钥"
    echo "  source .env"
    exit 1
fi

print_info "使用智谱AI (模型: ${ZHIPUAI_MODEL:-glm-4-flash})"

# 启动容器
docker run -it --rm \
    --name aat-zhipuai \
    --network host \
    -v "$(pwd)/scenarios:/app/scenarios" \
    -v "$(pwd)/.aat:/app/.aat" \
    -e ZHIPUAI_API_KEY="$ZHIPUAI_API_KEY" \
    -e ZHIPUAI_MODEL="${ZHIPUAI_MODEL:-glm-4-flash}" \
    ai-watch-tester:latest "$@"
