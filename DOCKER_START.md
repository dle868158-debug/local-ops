# Docker 部署说明

本项目已完整容器化，支持通过Docker快速部署。

## 📦 镜像信息

- **镜像名称**: `local-console:latest`
- **基础镜像**: Python 3.12-slim
- **镜像大小**: ~224MB
- **默认端口**: 9600

## 🚀 快速启动

### Windows（双击运行）

1. 安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
2. 双击 `docker-start.bat` 脚本
3. 等待容器启动完成（约 10-15 秒）
4. 自动打开 http://localhost:9600

### macOS / Linux

```bash
# 给脚本执行权限
chmod +x docker-start.sh

# 运行脚本
./docker-start.sh
```

### 手动启动（所有平台）

```bash
# 1. 构建镜像
docker build -t local-console:latest .

# 2. 用 docker-compose 启动（推荐）
docker compose up -d --build

# 3. 或直接用 docker run 启动
docker run -d \
  --name local-console \
  -p 127.0.0.1:9600:9600 \
  -v console-data:/app/data \
  -v console-logs:/app/logs \
  --restart unless-stopped \
  local-console:latest
```

## 📂 Docker Compose 配置

已包含 `docker-compose.yml`，包含以下功能：
- 自动卷管理
- 健康检查
- 自动重启策略
- 日志持久化

## 💾 数据持久化

应用数据存储在 Docker 卷中，即使删除容器也会保留：

```bash
# 查看卷列表
docker volume ls | grep console

# 检查卷内容
docker inspect console-data
```

**数据目录位置**：
- `/app/data` - 配置文件、图标、应用数据
- `/app/logs` - 运行日志

## 🛑 停止服务

```bash
# 使用 docker-compose
docker compose down

# 或直接停止容器
docker stop local-console
docker rm local-console
```

## 🔄 常用操作

### 查看容器状态
```bash
docker ps | grep local-console
```

### 查看实时日志
```bash
docker logs -f local-console
# 或使用 docker-compose
docker compose logs -f
```

### 进入容器
```bash
docker exec -it local-console bash
```

### 重启容器
```bash
docker restart local-console
# 或
docker compose restart
```

## 📊 健康检查

容器集成了健康检查，每 10 秒检查一次：

```bash
# 查看健康状态
docker inspect local-console | grep -A 5 '"Health"'
```

健康检查调用 `/api/health` 端点验证服务可用性。

## 🎯 自定义配置

### 修改端口

**使用 docker-compose**：编辑 `docker-compose.yml`

```yaml
ports:
  - "8080:9600"  # 改为 8080:9600
```

**使用 docker run**：

```bash
docker run -p 8080:9600 local-console:latest
```

### 自定义数据目录

```bash
docker run -d \
  -v ~/my-console-data:/app/data \
  -v ~/my-console-logs:/app/logs \
  local-console:latest
```

### 环境变量

```bash
docker run -d \
  -e CONSOLE_DATA_DIR=/app/data \
  -e CONSOLE_LOG_DIR=/app/logs \
  -e CONTAINER_ENV=1 \
  local-console:latest
```

## 🔧 构建镜像

### 从源代码构建

```bash
docker build -t local-console:v1.0 .
```

### 不使用缓存构建

```bash
docker build --no-cache -t local-console:latest .
```

### 查看构建历史

```bash
docker history local-console:latest
```

## 📋 文件说明

| 文件 | 说明 |
|------|------|
| `Dockerfile` | 容器镜像构建配置 |
| `docker-compose.yml` | Docker Compose 编排配置 |
| `.dockerignore` | Docker 构建时忽略的文件 |
| `docker-start.bat` | Windows 快速启动脚本 |
| `docker-start.sh` | macOS/Linux 快速启动脚本 |
| `DOCKER.md` | 详细的 Docker 使用文档 |

## ⚠️ 故障排查

### 镜像构建失败

```bash
# 查看完整构建日志
docker build -t local-console:latest . --no-cache -v
```

### 容器启动失败

```bash
# 查看错误日志
docker logs local-console

# 以交互模式运行查看错误
docker run -it --rm local-console:latest
```

### 端口已被占用

```bash
# 使用其他端口
docker run -p 8080:9600 local-console:latest

# 或查看谁占用了该端口
netstat -ano | findstr 9600  # Windows
lsof -i :9600  # macOS/Linux
```

### 权限问题

```bash
# 使用 root 用户运行
docker run --user root local-console:latest

# 或检查卷权限
docker exec local-console ls -la /app/data
```

## 🔐 安全建议

1. **仅限本机访问**：官方 Compose 只发布到宿主机 `127.0.0.1:9600`
2. **容器能力边界**：容器只能看到容器内进程，管理 Windows 宿主服务请使用原生版
2. **备份配置**：定期备份 `/app/data` 目录
3. **不要使用 root**：使用标准用户运行容器
4. **避免敏感信息**：命令行中不要包含密码或密钥

## 📈 性能优化

1. **使用本地卷**：在高速存储上挂载数据卷
2. **内存限制**：根据系统资源分配

```bash
docker run \
  -m 2g \
  --memory-swap 2g \
  local-console:latest
```

3. **CPU 限制**：

```bash
docker run \
  --cpus="1.5" \
  local-console:latest
```

## 🔄 升级镜像

```bash
# 停止旧容器
docker compose down

# 构建新镜像
docker build -t local-console:latest --no-cache .

# 启动新容器
docker compose up -d --build
```

## 📞 获取帮助

1. 查看 `DOCKER.md` 获取详细文档
2. 查看 `docker logs local-console` 查看错误
3. 查看项目 README.md 了解应用功能

## 📝 许可证

同主项目，采用 MIT 许可证。详见项目根目录的 `LICENSE` 文件。
