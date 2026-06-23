#!/bin/bash
set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
echo -e "${GREEN}=== AWT + 智谱AI 快速启动 ===${NC}"
echo ""
if [ -z "$ZHIPUAI_API_KEY" ]; then
    echo -e "${RED}错误：未设置智谱AI API密钥${NC}"
    echo "请设置：export ZHIPUAI_API_KEY=your_key"
    echo ""
    read -p "现在输入密钥？(y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        read -p "输入API密钥: " api_key
        export ZHIPUAI_API_KEY="$api_key"
    else
        exit 1
    fi
fi
echo -e "${GREEN}启动容器...${NC}"
docker run -it --rm \
    --network host \
    -v "$(pwd)/scenarios:/app/scenarios" \
    -v "$(pwd)/.aat:/app/.aat" \
    -e ZHIPUAI_API_KEY="$ZHIPUAI_API_KEY" \
    ai-watch-tester:minimal bash
