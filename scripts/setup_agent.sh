#!/bin/bash

# AWT Smart Agent 环境设置脚本

echo "🚀 AWT Smart Agent 环境设置"
echo "============================"
echo ""

# 检查 Python 版本
echo "📋 检查 Python 版本..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "当前 Python 版本: $python_version"

# 检查是否为虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  警告: 建议在虚拟环境中运行"
    echo "创建虚拟环境: python -m venv .venv"
    echo "激活虚拟环境: source .venv/bin/activate"
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 安装依赖
echo ""
echo "📦 安装 AWT Smart Agent 依赖..."
pip install -r src/aat/agent/requirements.txt

# 验证安装
echo ""
echo "🔍 验证安装..."
python -c "import langchain; print(f'✅ LangChain {langchain.__version__}')" || echo "❌ LangChain 安装失败"
python -c "import langgraph; print(f'✅ LangGraph {langgraph.__version__}')" || echo "❌ LangGraph 安装失败"

# 运行概念验证测试
echo ""
echo "🧪 运行概念验证测试..."
python tests/agent/concept_test.py

echo ""
echo "🎉 设置完成！"
echo ""
echo "📖 快速开始:"
echo "   python examples/agent/quickstart.py"
echo ""
echo "🧪 运行测试:"
echo "   pytest tests/agent/concept_test.py -v"
echo ""
echo "📚 查看文档:"
echo "   docs/agent/README.md"
echo "   docs/agent/DEEPAGENTS_IMPLEMENTATION.md"
echo ""