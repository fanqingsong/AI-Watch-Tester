# 智谱AI 快速开始指南

本指南帮助你使用智谱AI API 运行 AI Watch Tester。

## 前提条件

1. 获取智谱AI API密钥
   - 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
   - 注册账号并获取API密钥
   - 新用户通常有免费额度

2. Docker镜像已构建完成

## 快速开始（3步）

### 步骤1：设置API密钥

```bash
# 方式1：直接设置环境变量
export ZHIPUAI_API_KEY=your_zhipuai_api_key_here

# 方式2：使用.env文件
cp .env.zhipuai.example .env
# 编辑.env文件，填入你的API密钥
source .env
```

### 步骤2：启动容器

```bash
# 方式1：使用快速启动脚本（推荐）
./docker-run-zhipuai.sh bash

# 方式2：使用Docker命令
docker run -it --rm \
  --name aat-zhipuai \
  --network host \
  -v $(pwd)/scenarios:/app/scenarios \
  -v $(pwd)/.aat:/app/.aat \
  -e ZHIPUAI_API_KEY=$ZHIPUAI_API_KEY \
  ai-watch-tester:latest bash

# 方式3：使用Docker Compose
docker compose run --rm aat bash
```

### 步骤3：配置AWT使用智谱AI

进入容器后，运行：

```bash
# 设置AI提供商为智谱AI
aat config set ai.provider zhipuai

# 设置模型（可选，默认glm-4-flash）
aat config set ai.model glm-4-flash

# 验证配置
aat config get ai.provider
```

## 使用示例

### 示例1：分析文档并生成测试

```bash
# 在容器内
aat analyze docs/requirements.md
aat generate scenarios/ --from-analysis
```

### 示例2：运行测试并自动修复

```bash
# 运行测试
aat run scenarios/

# 如果失败，启动DevQA循环自动修复
aat loop scenarios/ --provider zhipuai
```

### 示例3：启动Web Dashboard

```bash
# 在宿主机
docker run -d --name aat-web \
  --network host \
  -v $(pwd)/scenarios:/app/scenarios \
  -v $(pwd)/.aat:/app/.aat \
  -p 8000:8000 \
  -e ZHIPUAI_API_KEY=$ZHIPUAI_API_KEY \
  ai-watch-tester:latest aat dashboard

# 访问 http://localhost:8000
```

## 模型选择

智谱AI提供多个模型，按需选择：

| 模型 | 特点 | 推荐用途 | 价格 |
|------|------|----------|------|
| `glm-4-flash` | 速度快，性价比高 | 日常测试、DevQA循环 | 💰 低 |
| `glm-4` | 标准模型，平衡性能 | 一般场景 | 💰💰 中 |
| `glm-4-plus` | 增强版，性能强 | 复杂场景、高质量输出 | 💰💰💰 高 |
| `glm-4-0520` | 特定版本 | 兼容性需求 | 💰💰 中 |
| `glm-4.7` | GLM-4.7模型 | 最新GLM-4.x版本 | 💰💰 中 |
| `glm-5.1` | GLM-5.1模型 | 最新GLM-5.x高性能版本 | 💰💰💰 高 |

### 设置模型

```bash
# 环境变量方式
export ZHIPUAI_MODEL=glm-4-plus

# 配置文件方式
aat config set ai.model glm-4-plus

# 命令行方式
aat generate --model glm-4-plus scenarios/
```

## 常见问题

### Q1: 提示"API密钥无效"

**解决：** 检查API密钥是否正确设置
```bash
echo $ZHIPUAI_API_KEY  # 应该显示你的密钥
docker inspect aat-zhipuai | grep -i zhipuai  # 检查容器环境变量
```

### Q2: 提示"模型不支持"

**解决：** 确保使用支持的模型名称
```bash
# 查看可用模型
aat config list-models --provider zhipuai

# 设置正确模型
aat config set ai.model glm-4-flash
```

### Q3: 响应速度慢

**解决：** 使用 `glm-4-flash` 模型
```bash
export ZHIPUAI_MODEL=glm-4-flash
```

### Q4: 想要更好的质量

**解决：** 升级到 `glm-4-plus`
```bash
export ZHIPUAI_MODEL=glm-4-plus
```

## 配置文件示例

创建 `~/.aat/config.yaml`：

```yaml
ai:
  provider: zhipuai
  api_key: ${ZHIPUAI_API_KEY}
  model: glm-4-flash
  base_url: https://open.bigmodel.cn/api/coding/paas/v4/
  max_tokens: 4096
  temperature: 0.7

engine:
  type: web
  headless: true
  screenshot_dir: .aat/screenshots
  
matchers:
  - method: template
    threshold: 0.8
  - method: ocr
    language: eng
```

## 成本估算

智谱AI定价（参考，实际以官方为准）：

- `glm-4-flash`: ¥0.001/千tokens
- `glm-4`: ¥0.05/千tokens
- `glm-4-plus`: ¥0.15/千tokens
- `glm-4.7`: 按官方定价
- `glm-5.1`: 按官方定价

**单次DevQA循环成本估算：**
- 输入：~5K tokens
- 输出：~2K tokens
- 总计：~7K tokens

使用 `glm-4-flash` 每次约 ¥0.007，非常经济！

## 下一步

1. 阅读完整文档：[DOCKER_GUIDE.md](DOCKER_GUIDE.md)
2. 查看项目README：[README.md](README.md)
3. 了解更多功能：`aat --help`

## 技术支持

- 智谱AI文档：https://open.bigmodel.cn/dev/api
- AWT项目：https://github.com/ksgisang/AI-Watch-Tester
- 问题反馈：提交Issue到GitHub仓库
