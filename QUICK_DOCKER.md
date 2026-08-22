# 🐳 本地服务指挥台 - Docker 快速参考

## 📌 5 秒快速启动

### Windows
```
双击 docker-start.bat
```

### macOS / Linux
```bash
chmod +x docker-start.sh && ./docker-start.sh
```

## 🎯 基本命令

| 操作 | 命令 |
|------|------|
| 启动 | `docker compose up -d --build` |
| 停止 | `docker compose down` |
| 查看日志 | `docker logs -f local-console` |
| 进入容器 | `docker exec -it local-console bash` |
| 重启 | `docker restart local-console` |
| 状态 | `docker ps \| grep local-console` |

## 📍 访问地址

```
http://localhost:9600
```

## 📊 Docker 信息

- **镜像名**: `local-console:latest`
- **镜像大小**: 224MB
- **基础镜像**: Python 3.12-slim
- **容器端口**: 9600
- **数据卷**: console-data, console-logs

## 🔧 自定义端口

编辑 `docker-compose.yml`：
```yaml
ports:
  - "8080:9600"  # 改为 8080
```

然后重启：
```bash
docker compose up -d --build
```

## 🛠️ 文件说明

| 文件 | 用途 |
|------|------|
| Dockerfile | 镜像构建配置 |
| docker-compose.yml | 容器编排配置 |
| .dockerignore | 忽略文件列表 |
| docker-start.bat | Windows 启动脚本 |
| docker-start.sh | Unix 启动脚本 |
| DOCKER.md | 详细文档 |

## 📖 详细文档

- **快速入门**: 看本文件
- **完整指南**: 查看 `DOCKER_START.md`
- **高级用法**: 查看 `DOCKER.md`

## 🐛 常见问题

### 端口 9600 已被占用
```bash
# 查看谁占用了端口
netstat -ano | findstr 9600  # Windows
lsof -i :9600  # macOS/Linux

# 改用其他端口
docker run -p 8080:9600 local-console:latest
```

### 容器无法启动
```bash
# 查看错误日志
docker logs local-console

# 尝试手动运行查看完整错误
docker run -it --rm local-console:latest
```

### 数据丢失后恢复
```bash
# Docker 卷中的数据是持久的
docker volume ls
docker inspect console-data
```

## 🚀 生产部署

```bash
# 构建生产镜像
docker build -t local-console:v1.0 .

# 启动生产容器
docker run -d \
  --name local-console-prod \
  -p 127.0.0.1:9600:9600 \
  -v console-prod-data:/app/data \
  -v console-prod-logs:/app/logs \
  --restart always \
  --memory 2g \
  --cpus 1.5 \
  local-console:v1.0
```

## 💡 使用提示

1. ✅ 数据自动持久化到 Docker 卷
2. ✅ 容器停止时应用数据不丢失
3. ✅ 健康检查每 10 秒运行一次
4. ✅ 自动重启策略保证可用性
5. ✅ 原生 Python 环境，无额外依赖

## 📞 获取帮助

```bash
# 查看完整日志
docker logs -f local-console

# 查看镜像信息
docker inspect local-console:latest

# 测试 API
curl http://localhost:9600/api/health
```

---

**完成时间**: 构建成功 ✅  
**镜像**: local-console:latest (224MB)  
**状态**: 准备就绪
