# AWT Docker 使用指南

## 快速开始

### 1. 构建镜像（使用国内镜像源加速）

```bash
docker build -t ai-watch-tester:latest .
```

或使用 Makefile：
```bash
make -f Makefile.docker docker-build
```

### 2. 运行容器

#### 交互式运行（推荐用于开发调试）

**使用智谱AI：**
```bash
# 设置环境变量
export ZHIPUAI_API_KEY=your_zhipuai_key

# 启动容器
docker run -it --rm \
  --name aat \
  --network host \
  -v $(pwd)/scenarios:/app/scenarios \
  -v $(pwd)/.aat:/app/.aat \
  -e ZHIPUAI_API_KEY \
  ai-watch-tester:latest bash

# 或使用快速启动脚本
./docker-run-zhipuai.sh bash
```

**使用其他AI提供商：**
```bash
docker run -it --rm \
  --name aat \
  --network host \
  -v $(pwd)/scenarios:/app/scenarios \
  -v $(pwd)/.aat:/app/.aat \
  -e ANTHROPIC_API_KEY=your_key_here \
  -e OPENAI_API_KEY=your_key_here \
  ai-watch-tester:latest bash
```

#### 运行测试命令（使用智谱AI）
```bash
# 使用智谱AI运行测试
docker run -it --rm \
  --name aat \
  --network host \
  -v $(pwd)/scenarios:/app/scenarios \
  -v $(pwd)/.aat:/app/.aat \
  -e ZHIPUAI_API_KEY=your_zhipuai_key \
  ai-watch-tester:latest aat run scenarios/

# 或使用快速启动脚本
./docker-run-zhipuai.sh aat run scenarios/
```

#### 启动 Web Dashboard
```bash
docker run -d --name aat-web \
  --network host \
  -v $(pwd)/scenarios:/app/scenarios \
  -v $(pwd)/.aat:/app/.aat \
  -p 8000:8000 \
  ai-watch-tester:latest aat dashboard --host 0.0.0.0 --port 8000
```

### 3. 使用 Docker Compose（推荐）

```bash
# 构建并启动服务
docker compose up -d

# 查看日志
docker compose logs -f

# 进入容器
docker compose exec aat bash

# 停止服务
docker compose down
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 示例 | 必需 |
|--------|------|------|------|
| `ZHIPUAI_API_KEY` | 智谱AI API密钥 | `your_zhipuai_key` | 是* |
| `ZHIPUAI_MODEL` | 智谱AI模型 | `glm-4-flash` | 否 |
| `ANTHROPIC_API_KEY` | Claude API密钥 | `sk-ant-xxx` | 否 |
| `OPENAI_API_KEY` | OpenAI API密钥 | `sk-xxx` | 否 |
| `OLLAMA_BASE_URL` | Ollama服务地址 | `http://host.docker.internal:11434` | 否 |
| `DISPLAY` | X11显示（Linux GUI） | `:0` | 否 |

*至少需要配置一个AI提供商的API密钥

### 智谱AI配置（推荐）

如果你有智谱AI的API密钥，这是最简单的配置方式：

```bash
# 1. 设置环境变量
export ZHIPUAI_API_KEY=your_zhipuai_api_key

# 2. 可选：指定模型（默认：glm-4-flash）
export ZHIPUAI_MODEL=glm-4-flash

# 3. 启动容器
docker compose run --rm aat bash
```

或在 `.env` 文件中配置：
```bash
cp .env.zhipuai.example .env
# 编辑 .env 填入 ZHIPUAI_API_KEY
docker compose run --rm aat bash
```

### 智谱AI模型选择

- `glm-4-flash` - 推荐！性价比高，速度快（默认）
- `glm-4` - 标准模型，平衡性能和成本
- `glm-4-plus` - 增强版模型，性能更强
- `glm-4-0520` - 特定版本
- `glm-4.7` - GLM-4.7最新版本
- `glm-5.1` - GLM-5.1高性能版本

查看[智谱AI文档](https://open.bigmodel.cn/dev/api)了解更多。

### 卷挂载

- `./scenarios:/app/scenarios` - 测试场景目录
- `./.aat:/app/.aat` - 测试结果和基线目录
- `/tmp/.X11-unix:/tmp/.X11-unix` - X11显示（Linux）

### 网络模式

- `--network host` - 使用宿主机网络（推荐，可访问localhost）
- `-p 8000:8000` - 端口映射（如果不使用host网络）

### AWT配置文件（~/.aat/config.yaml）

创建配置文件指定使用智谱AI：

```yaml
ai:
  provider: zhipuai
  api_key: ${ZHIPUAI_API_KEY}
  model: glm-4-flash
  base_url: https://open.bigmodel.cn/api/paas/v4/

engine:
  type: web
  headless: true
  screenshot_dir: .aat/screenshots
  viewport:
    width: 1280
    height: 720
```

或在命令行中指定：
```bash
# 在容器内
aat config set ai.provider zhipuai
aat config set ai.model glm-4-flash
aat config set ai.api_key your_zhipuai_key
```

## 常用命令

### 容器内命令

```bash
# 显示帮助
aat --help

# 验证场景
aat validate scenarios/

# 运行测试
aat run scenarios/test.yaml

# 启动Web Dashboard
aat dashboard

# DevQA循环
aat loop scenarios/
```

### Makefile命令

```bash
# 构建镜像
make -f Makefile.docker docker-build

# 运行容器（交互式）
make -f Makefile.docker docker-run

# 进入容器Shell
make -f Makefile.docker docker-shell

# 启动Web Dashboard
make -f Makefile.docker docker-dashboard

# 运行测试
make -f Makefile.docker docker-run-test

# 查看日志
make -f Makefile.docker docker-logs

# 清理容器和镜像
make -f Makefile.docker docker-clean
```

## 镜像信息

- **基础镜像**: `python:3.12-slim`
- **大小**: 约 1-2 GB（包含Chromium浏览器）
- **包含组件**:
  - Python 3.12
  - Playwright + Chromium
  - Tesseract OCR (支持英文/韩文)
  - OpenCV、PyAutoGUI
  - FastAPI + Uvicorn (Web Dashboard)

## 国内镜像源配置

镜像已预配置国内镜像源，加速构建：
- **apt** → 阿里云镜像
- **pip** → 清华大学镜像

## 故障排查

### 1. 构建超时
```bash
# 使用国内镜像源重新构建
docker build --no-cache -t ai-watch-tester:latest .
```

### 2. Chromium下载失败
```bash
# 容器内手动安装
docker exec -it aat playwright install chromium
```

### 3. X11显示问题（Linux）
```bash
# 允许X11连接
xhost +local:docker

# 运行容器
docker run -it --rm \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -e DISPLAY=$DISPLAY \
  ai-watch-tester:latest
```

### 4. 权限问题
```bash
# 确保目录可写
chmod -R 755 scenarios/ .aat/
```

## 性能优化

### 1. 使用多阶段构建
镜像已采用分层构建，充分利用Docker缓存。

### 2. 减小镜像体积
```bash
# 清理构建缓存
docker system prune -a

# 使用.dockerignore
# 已配置，排除不必要的文件
```

### 3. 并发运行
```bash
# 并行运行多个测试
docker run -it --rm ai-watch-tester:latest aat run scenarios/ --workers 4
```

## 生产部署

### 1. 推送到镜像仓库
```bash
# 标记镜像
docker tag ai-watch-tester:latest your-registry/ai-watch-tester:1.6.2

# 推送
docker push your-registry/ai-watch-tester:1.6.2
```

### 2. 使用Docker Compose生产配置
```yaml
services:
  aat:
    image: your-registry/ai-watch-tester:1.6.2
    restart: always
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./scenarios:/app/scenarios
      - ./data:/app/.aat
    ports:
      - "8000:8000"
```

## 参考资源

- [项目README](README.md)
- [开发文档](CLAUDE.md)
- [Dockerfile](Dockerfile)
- [docker-compose.yml](docker-compose.yml)
