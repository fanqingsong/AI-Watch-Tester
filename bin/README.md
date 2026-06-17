# AI-Watch-Tester Docker Compose 服务管理脚本

这些脚本提供便捷的方式来管理AI-Watch-Tester的Docker服务，支持热加载和用户友好的操作体验。

## 📁 脚本列表

- **`start.sh`** - 启动AI-Watch-Tester服务
- **`stop.sh`** - 停止服务（可选清理数据）
- **`status.sh`** - 查看服务状态和健康信息
- **`logs.sh`** - 查看和管理日志
- **`restart.sh`** - 重启服务
- **`utils.sh`** - 工具函数库（被其他脚本调用）

## 🚀 快速开始

### 启动服务

```bash
# 默认启动（后台运行）
./bin/start.sh

# 开发模式启动（支持代码热加载）
./bin/start.sh --dev

# 重新构建并启动
./bin/start.sh --rebuild
```

### 查看状态

```bash
# 基本状态
./bin/status.sh

# 详细状态（包括卷挂载、环境配置）
./bin/status.sh --detailed
```

### 查看日志

```bash
# 查看最近100行日志
./bin/logs.sh

# 实时跟踪日志
./bin/logs.sh -f

# 仅查看错误日志
./bin/logs.sh -e

# 导出日志到文件
./bin/logs.sh --export my-logs.txt
```

### 停止服务

```bash
# 正常停止（保留数据）
./bin/stop.sh

# 停止并删除所有数据
./bin/stop.sh --volumes

# 强制停止（不确认）
./bin/stop.sh --force
```

### 重启服务

```bash
# 优雅重启（停止->启动）
./bin/restart.sh

# 快速重启（直接重启容器）
./bin/restart.sh --quick
```

## 🌡️ 热加载支持

项目已配置完善的代码热加载功能：

### 工作原理

通过Docker volume挂载实现：
- `.:/app` - 代码变更实时同步到容器
- `./scenarios:/app/scenarios` - 测试场景文件热加载
- `./.aat:/app/.aat` - 测试数据持久化

### 使用方法

1. **启动服务**：
   ```bash
   ./bin/start.sh
   ```

2. **修改代码**：
   ```bash
   # 编辑本地代码文件
   vim src/aat/dashboard/app.py
   ```

3. **立即生效**：
   - 容器内自动检测文件变化
   - 无需重启容器即可看到更改

### Python代码自动重载

对于需要Python进程重启的代码修改：
```bash
./bin/start.sh --dev  # 启用auto-reload模式
```

## 🔧 环境配置

### 环境变量

创建 `.env` 文件配置API密钥：

```bash
# AI Provider Configuration
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
ZHIPUAI_API_KEY=your_zhipuai_key_here
ZHIPUAI_MODEL=glm-4-flash

# Ollama Configuration
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Service Configuration
SERVICE_PORT=9500
```

### 热加载验证

1. 启动服务：
   ```bash
   ./bin/start.sh
   ```

2. 修改代码文件：
   ```bash
   echo "// TEST" >> src/aat/dashboard/app.py
   ```

3. 在容器内验证：
   ```bash
   docker exec -it ai-watch-tester tail -5 /app/src/aat/dashboard/app.py
   ```

4. 确认修改已同步（应看到新添加的 `// TEST`）

## 📊 服务状态信息

脚本提供的服务状态包括：

- **容器状态**：运行中/已停止/未创建
- **健康检查**：healthy/unhealthy/unknown
- **运行时间**：X天/X小时/X分钟/X秒
- **资源使用**：CPU和内存使用情况
- **访问地址**：http://localhost:9500
- **端口映射**：0.0.0.0:9500->9500/tcp

## 🔍 故障排除

### 端口被占用

```bash
# 查看占用端口的进程
lsof -i :9500

# 停止占用端口的进程
kill -9 <PID>
```

### Docker未运行

```bash
# 启动Docker服务（Linux）
sudo systemctl start docker

# 启动Docker Desktop（macOS/Windows）
# 在应用程序中启动Docker
```

### 服务启动失败

```bash
# 查看详细日志
./bin/logs.sh -f

# 重新构建镜像
./bin/start.sh --rebuild
```

### 容器异常

```bash
# 查看容器状态
docker ps -a

# 查看容器日志
docker logs ai-watch-tester

# 强制删除容器
docker rm -f ai-watch-tester
```

## 🎯 最佳实践

### 开发流程

1. **启动服务**：
   ```bash
   ./bin/start.sh --dev
   ```

2. **修改代码**：
   - 直接编辑本地文件
   - 变更自动同步到容器

3. **验证更改**：
   - 访问 http://localhost:9500
   - 查看日志确认无错误

4. **停止服务**：
   ```bash
   ./bin/stop.sh
   ```

### 生产部署

```bash
# 1. 构建生产镜像
docker compose build

# 2. 启动服务
./bin/start.sh

# 3. 验证状态
./bin/status.sh

# 4. 查看日志
./bin/logs.sh
```

## 📝 脚本特性

- ✅ **统一的错误处理**：清晰的错误提示和解决方案
- ✅ **彩色输出**：直观的状态显示（成功/警告/错误）
- ✅ **交互式确认**：危险操作前的确认提示
- ✅ **进度显示**：长时间操作的进度反馈
- ✅ **健康检查**：自动等待服务启动完成
- ✅ **状态验证**：操作后自动验证服务状态
- ✅ **使用帮助**：每个脚本都支持 `--help` 参数

## 🔄 向后兼容

现有的启动脚本仍然可用，但会显示弃用警告：

```bash
⚠️  建议使用: bin/start.sh
   此脚本将被弃用，请迁移到新的bin目录脚本
```

建议迁移到新的 `bin/` 目录脚本以获得更好的功能和体验。

## 📚 相关文档

- [Docker Compose 官方文档](https://docs.docker.com/compose/)
- [项目主文档](../README.md)
- [Docker使用指南](../DOCKER_GUIDE.md)