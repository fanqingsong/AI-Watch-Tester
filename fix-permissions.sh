#!/bin/bash
# Fix .aat directory permissions

echo "=== 修复 AAT 目录权限 ==="

if [ -d ".aat" ]; then
    echo "正在修复 .aat 目录权限..."
    sudo chown -R $USER:$USER .aat/
    sudo chmod -R 755 .aat/
    echo "✅ 权限已修复"

    echo ""
    echo "验证权限:"
    ls -la .aat/
else
    echo ".aat 目录不存在，创建中..."
    mkdir -p .aat/screenshots .aat/sessions
fi
