# 🎉 AWT + 智谱AI Docker - 准备就绪！

## ✅ 验证成功

- **镜像**: ai-watch-tester:minimal (1.58GB)
- **AWT版本**: 1.5.5 ✅
- **智谱AI**: 已集成 ✅

## 🚀 立即启动（复制粘贴）

### 方式1：快速启动脚本
```bash
export ZHIPUAI_API_KEY=your_key
./start-zhipuai.sh
```

### 方式2：Docker命令
```bash
export ZHIPUAI_API_KEY=your_key
docker run -it --rm --network host \
  -v $(pwd)/scenarios:/app/scenarios \
  -v $(pwd)/.aat:/app/.aat \
  -e ZHIPUAI_API_KEY=$ZHIPUAI_API_KEY \
  ai-watch-tester:minimal bash
```

## 📝 容器内配置

进入容器后运行：
```bash
aat config set ai.provider zhipuai
aat config set ai.model glm-4-flash
aat --help
```

## 💰 成本参考

glm-4-flash: 每次DevQA循环约 ¥0.007
