#!/bin/bash
echo "=== AWT + 智谱AI 容器验证 ==="
echo ""

echo "构建信息："
docker images | grep ai-watch-tester

echo ""
echo "容器内命令测试："
docker run --rm ai-watch-tester:minimal aat --version

echo ""
echo "智谱AI配置示例（在容器内运行）："
echo "------------------------------------"
cat << 'INNER_EOF'
# 1. 设置AI提供商
aat config set ai.provider zhipuai

# 2. 设置模型
aat config set ai.model glm-4-flash

# 3. 验证配置
aat config get ai.provider
aat config get ai.model

# 4. 显示帮助
aat --help

# 5. 分析文档示例
# aat analyze docs/requirements.md

# 6. 生成测试场景
# aat generate scenarios/ --from-analysis
INNER_EOF

echo ""
echo "快速启动命令（在宿主机运行）："
echo "------------------------------------"
cat << 'CMD_EOF'
# 设置API密钥
export ZHIPUAI_API_KEY=your_real_key_here

# 启动容器
docker run -it --rm \
    --network host \
    -v $(pwd)/scenarios:/app/scenarios \
    -v $(pwd)/.aat:/app/.aat \
    -e ZHIPUAI_API_KEY=$ZHIPUAI_API_KEY \
    ai-watch-tester:minimal bash

# 或使用启动脚本
./start-zhipuai.sh
CMD_EOF
