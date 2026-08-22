# 本地服务指挥台 - Docker 部署指南

这个项目已被容器化，可以通过Docker运行。

## 快速启动

### 方式1: Docker Compose（推荐）

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f console
```

访问：http://localhost:9600

### 方式2: Docker Run

```bash
# 创建数据卷
docker volume create console-data
docker volume create console-logs

# 运行容器
docker run -d \
  --name local-console \
  -p 9600:9600 \
  -v console-data:/app/data \
  -v console-logs:/app/logs \
  --restart unless-stopped \
  local-console:latest

# 查看状态
docker ps | grep local-console

# 查看日志
docker logs -f local-console
```

访问：http://localhost:9600

### 方式3: 自定义端口和路径

```bash
docker run -d \
  --name local-console \
  -p 8080:9600 \
  -v ~/console-data:/app/data \
  -v ~/console-logs:/app/logs \
  -e CONSOLE_DATA_DIR=/app/data \
  -e CONSOLE_LOG_DIR=/app/logs \
  --restart unless-stopped \
  local-console:latest
```

访问：http://localhost:8080

## 镜像信息

- **基础镜像**: python:3.12-slim
- **镜像大小**: ~224MB
- **默认端口**: 9600
- **数据存储**: `/app/data`（可挂载卷）
- **日志位置**: `/app/logs`（可挂载卷）

## 关键特性

- ✅ 完整Python 3.12运行环境
- ✅ 自动绑定到0.0.0.0（Docker容器友好）
- ✅ 数据卷持久化
- ✅ 健康检查集成
- ✅ 自动重启策略

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| CONTAINER_ENV | 1 | 容器环境标志 |
| CONSOLE_DATA_DIR | /app/data | 数据目录 |
| CONSOLE_LOG_DIR | /app/logs | 日志目录 |

## 常见操作

### 查看容器状态
```bash
docker ps -a | grep local-console
```

### 进入容器
```bash
docker exec -it local-console bash
```

### 重启容器
```bash
docker restart local-console
```

### 查看实时日志
```bash
docker logs -f local-console
```

### 停止并删除容器
```bash
docker stop local-console
docker rm local-console
```

### 清理卷数据
```bash
docker volume rm console-data console-logs
```

## 健康检查

容器内置健康检查，每10秒检测一次服务可用性：
```bash
docker inspect local-console | grep -A 5 Health
```

## 持久化数据

应用数据存储在Docker卷中，即使容器停止也会保留：
- `console-data`: 配置文件、图标
- `console-logs`: 应用日志

## 构建自定义镜像

```bash
# 使用Dockerfile构建
docker build -t my-console:v1.0 .

# 或编辑Dockerfile后构建
docker build -t my-console:latest --no-cache .
```

## Docker Compose 完整示例

见 `docker-compose.yml`

## 故障排查

### 端口已占用
```bash
# 使用其他端口
docker run -p 8080:9600 local-console:latest
```

### 查看错误日志
```bash
docker logs local-console
```

### 容器启动失败
```bash
# 交互模式运行以查看错误
docker run -it --rm local-console:latest
```

### 权限问题
```bash
# 使用root用户运行
docker run --user root local-console:latest
```

## 性能建议

1. 挂载数据卷到本地高速存储
2. 根据系统资源分配适当的内存限制
3. 启用自动重启策略（unless-stopped）

## 安全提示

- 仅在本地信任网络中使用
- 定期备份 `/app/data` 目录中的配置
- 不要将敏感信息写入命令行可见的命令

## 更新镜像

```bash
# 重新构建最新镜像
docker build -t local-console:latest .

# 重启容器使用新镜像
docker-compose up -d --force-recreate
# 或
docker stop local-console
docker rm local-console
docker run ... local-console:latest
```
