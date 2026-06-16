#!/bin/bash
set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
echo -e "${GREEN}=== AWT 快速启动（精简版） ===${NC}"
echo ""
echo -e "${YELLOW}注意：此版本不包含Chromium浏览器${NC}"
echo "构建快速启动，可在容器内手动安装Chromium"
echo ""

if [ -z "$ZHIPUAI_API_KEY" ]; then
    echo -e "${YELLOW}请设置智谱AI密钥：${NC}"
    echo "export ZHIPUAI_API_KEY=your_key"
    exit 1
fi

echo -e "${GREEN}构建精简版镜像...${NC}"
docker build -f Dockerfile.minimal -t ai-watch-tester:latest .

echo -e "${GREEN}启动容器...${NC}"
docker run -it --rm \
    --network host \
    -v "$(pwd)/scenarios:/app/scenarios" \
    -v "$(pwd)/.aat:/app/.aat" \
    -e ZHIPUAI_API_KEY="$ZHIPUAI_API_KEY" \
    ai-watch-tester:latest bash
