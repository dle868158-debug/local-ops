# 总控台（Local Ops Console）

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?logo=windows11&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-可选-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

总控台是一款面向个人开发者和本地工作站的服务启动、进程监控与任务管理工具。它把常用项目、长期服务、一次性任务和网址入口集中到一个中文网页中，支持查看端口、进程、运行时长、日志和配置健康状态。

本分支重点适配 **Windows 10/11**，同时保留 macOS 源码运行能力，并提供 Docker 部署示例。后端以 Python 标准库为主，前端使用原生 HTML、CSS 和 JavaScript，无需 Node.js、前端框架、CDN 或构建工具。

> [!IMPORTANT]
> 总控台会以当前用户权限执行你保存的命令。它是本机个人工具，不是带有身份认证的公网运维面板。原生模式默认只监听 `127.0.0.1`，请勿通过端口映射、反向代理或隧道直接暴露到不受信任的网络。

## 主要功能

- **启动台**：保存和管理长期服务、批处理任务与网址卡片，一键启动、停止、重启、运行或打开。
- **服务监控**：每 2 秒发现当前用户的本地监听端口，展示 PID、工作目录、内存、运行时长和启动来源。
- **安全认领进程**：通过运行令牌、进程树、当前用户和工作目录识别受控进程，不会仅凭端口结束其他程序。
- **项目自动识别**：只读分析项目根目录，为 Node.js、Python、Docker、Go、Rust、静态站点等项目推荐启动命令。
- **配置与运行诊断**：在启动前检查工作目录、脚本、运行时和端口占用，并提供可执行的修复建议。
- **任务状态记录**：区分成功、失败、取消和总控台中止，记录退出码、完成时间及耗时。
- **日志中心**：集中查看应用日志和总控台自身日志，大文件自动轮转。
- **技能工作台**：扫描 `~/.agents/skills`、`~/.claude/skills` 和 `~/.codex/skills`，合并去重并提供中文分类、搜索与详情。
- **中文 Ops 界面**：支持浅色、深色和跟随系统，包含导航轨、KPI 概览、实时动态和响应式布局。

## 界面预览

以下截图使用脱敏演示数据，不包含真实用户名、目录、命令或服务信息。

| 启动台 | 服务监控 |
| --- | --- |
| ![总控台启动台](docs/screenshots/ops-launchpad.jpg) | ![总控台服务监控](docs/screenshots/ops-services.jpg) |

## 技术架构

| 层级 | 实现 |
| --- | --- |
| 后端 | Python 3.12+ 标准库，单文件 `server.py` |
| 前端 | 原生 HTML、CSS、JavaScript ES Modules，无构建流程 |
| 通信 | 本地 HTTP JSON API，原生模式仅绑定回环地址 |
| Windows 进程管理 | `netstat`、PowerShell CIM、`taskkill`、PPID 后代树与锚点进程 |
| macOS 进程管理 | `lsof`、`ps`、进程组与信号 |
| 配置存储 | 本地 JSON，线程锁保护，临时文件写入后原子替换，保留 `.bak` |
| Windows 桌面壳 | PySide6 WebEngine，可打包为单文件 EXE |
| Docker | `python:3.12-slim`、Docker Compose、命名卷持久化 |

## 环境要求

### 原生运行

| 项目 | 最低要求 | 说明 |
| --- | --- | --- |
| 操作系统 | Windows 10/11 64 位 | 推荐 Windows 11；macOS 可通过源码运行 |
| Python | 3.12 或更高版本 | 启动 Web 服务无需安装第三方 Python 包 |
| PowerShell | Windows PowerShell 5.1 或 PowerShell 7 | 用于读取 Windows 进程信息 |
| 系统工具 | `netstat`、`taskkill` | Windows 系统自带 |
| 浏览器 | Edge、Chrome、Firefox、Safari 等现代浏览器 | 需要支持 ES Modules |
| 网络 | 仅本机访问即可 | 原生模式默认监听 `127.0.0.1` |

### Windows EXE 打包

除上述环境外，还需要联网安装以下构建依赖：

- PyInstaller
- PySide6
- Pillow

`build.bat` 会优先创建隔离的 `.buildenv` 虚拟环境并自动检查、安装这些依赖。它们只用于打包，不是运行 `server.py` 的必需依赖。

### Docker 运行

- Docker Desktop，或可用的 Docker Engine
- Docker Compose v2（推荐使用 `docker compose`）
- 至少 500 MB 可用磁盘空间

## 快速开始

### 方式一：Windows 源码运行（推荐）

1. 安装 [Python 3.12 或更高版本](https://www.python.org/downloads/)，安装时建议勾选“Add Python to PATH”。
2. 克隆 `windows-support` 分支：

   ```powershell
   git clone --branch windows-support --single-branch https://github.com/dle868158-debug/local-ops.git
   Set-Location .\local-ops
   ```

3. 检查 Python：

   ```powershell
   py -3 --version
   ```

4. 启动总控台：

   ```powershell
   .\start.bat
   ```

   也可以直接运行：

   ```powershell
   py -3 server.py
   ```

启动后会自动打开浏览器。默认地址为 <http://127.0.0.1:9600>；如果 9600 已被占用，程序会依次尝试 9601—9609。

常用启动参数：

```powershell
py -3 server.py --no-browser
py -3 server.py --preferred-port 9603
```

- `--no-browser`：只启动服务，不自动打开浏览器。
- `--preferred-port`：在 9600—9609 范围内指定优先端口。

### 方式二：构建 Windows EXE

在项目根目录运行：

```powershell
.\build.bat
```

构建脚本会完成以下操作：

1. 创建或复用 `.buildenv` 隔离环境。
2. 安装 PyInstaller、PySide6 和 Pillow。
3. 生成 Windows 图标及版本资源。
4. 根据 `总控台.spec` 构建单文件程序。
5. 输出 `dist\总控台.exe`。

双击 EXE 即可运行，正常情况下不会显示控制台窗口。单文件程序首次启动需要释放运行资源，可能等待数秒；当前构建未进行商业代码签名，Windows SmartScreen 可能显示安全提示。

> `.buildenv`、`build` 和 `dist` 都是本地构建产物，不应提交到 Git。

### 方式三：macOS 源码运行

当前 `windows-support` 分支不提供 `.app` 双击启动包，但共享后端仍可通过源码运行：

```bash
python3 --version
python3 server.py
```

建议使用 Python 3.12 或更高版本。macOS 运行依赖系统自带的 `ps`、`lsof` 和 `osascript`。

## Docker 部署

> [!WARNING]
> Docker 容器默认只能看到容器内部的进程和端口，不能完整监控或控制 Windows/macOS 宿主机上的本地服务。若需要总控台的完整进程管理能力，请使用 Windows 原生方式运行。Docker 更适合体验界面、验证部署或管理同一容器内的任务。

### Docker Compose

```powershell
docker compose up -d --build
docker compose ps
docker compose logs -f
```

访问 <http://localhost:9600>。

停止并删除容器：

```powershell
docker compose down
```

配置和日志分别保存在 `console-data`、`console-logs` 命名卷中，普通 `docker compose down` 不会删除它们。只有在确认不再需要数据时才使用 `docker compose down -v`。

当前 `docker-compose.yml` 使用 `9600:9600` 发布端口，可能监听宿主机所有网络接口。仅在可信网络中使用；如只允许本机访问，请将端口映射改为：

```yaml
ports:
  - "127.0.0.1:9600:9600"
```

### 直接使用 Docker

```powershell
docker build -t local-console:latest .
docker run -d --name local-console `
  -p 127.0.0.1:9600:9600 `
  -v local-console-data:/app/data `
  -v local-console-logs:/app/logs `
  local-console:latest
```

健康检查：

```powershell
docker inspect --format "{{json .State.Health}}" local-console
```

更多说明见 [`QUICK_DOCKER.md`](QUICK_DOCKER.md)、[`DOCKER.md`](DOCKER.md) 和 [`DOCKER_START.md`](DOCKER_START.md)。

## 数据目录与环境变量

### 默认数据位置

| 平台 | 配置和图标 | 日志 |
| --- | --- | --- |
| Windows | `%APPDATA%\总控台` | `%LOCALAPPDATA%\总控台\Logs` |
| macOS | `~/Library/Application Support/总控台` | `~/Library/Logs/总控台` |
| Docker | `/app/data` | `/app/logs` |

主要文件：

- `config.json`：应用、任务、网址、命令、目录、端口和界面配置。
- `config.json.bak`：上一次已知良好的配置。
- `icons/`：用户上传图标和抓取的站点图标。
- `{appId}.log`：各应用运行日志。
- `console.log`：总控台自身日志。

配置中可能包含个人目录和完整命令，日志也可能包含敏感输出。请勿将这些运行数据、日志或未经脱敏的截图提交到 GitHub。

### 可配置环境变量

| 变量 | 作用 | 示例 |
| --- | --- | --- |
| `CONSOLE_DATA_DIR` | 覆盖配置和图标目录 | `D:\LocalOps\data` |
| `CONSOLE_LOG_DIR` | 覆盖日志目录 | `D:\LocalOps\logs` |

Windows PowerShell 示例：

```powershell
$env:CONSOLE_DATA_DIR = "D:\LocalOps\data"
$env:CONSOLE_LOG_DIR = "D:\LocalOps\logs"
py -3 server.py
```

自定义路径必须是非空绝对路径，并指向总控台专用目录。不要使用磁盘根目录、用户主目录或项目根目录。

## 基本使用

### 添加服务、任务或网址

1. 在“启动台”点击“添加服务”。
2. 选择类型：
   - `service`：长期运行的本地服务，具有端口语义。
   - `task`：执行后会结束的批处理任务，不使用端口。
   - `link`：网址入口，只打开浏览器，不执行命令。
3. 选择项目目录，让总控台只读识别候选命令，或手动填写命令。
4. 保存后使用卡片启动、运行或打开。

### 任务退出状态

| 退出方式 | 显示状态 |
| --- | --- |
| 退出码 `0` | 成功 |
| 退出码 `130` | 已取消 |
| 其他非零退出码 | 失败 |
| 点击总控台“中止” | 已中止 |

### 新端口发现

服务监控只提醒当前页面会话中新增、尚未管理的本地端口。首次打开、断线恢复或后台恢复时只建立静默基线，不会把所有已有端口重复提示。

## 项目结构

```text
local-ops/
├─ server.py                 # Python 标准库后端与跨平台适配
├─ console_gui.py            # Windows PySide6 桌面壳入口
├─ start.bat                 # Windows 源码启动器
├─ build.bat                 # Windows 单文件 EXE 构建脚本
├─ 总控台.spec               # PyInstaller 构建配置
├─ Dockerfile                # Docker 镜像定义
├─ docker-compose.yml        # Compose 服务与数据卷
├─ static/                   # 原生前端、主题、字体、图标和品牌资源
├─ tests/                    # 后端、前端契约、安全和平台测试
├─ tools/                    # 检查、资源生成和 Windows 辅助工具
├─ docs/screenshots/         # README 界面截图
├─ VERSION                   # 唯一版本号来源
└─ LICENSE                   # MIT 许可证
```

## 开发与测试

直接运行总控台不需要安装 `requirements-dev.txt`。开发依赖仅用于重新生成图片资源：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Windows 上执行完整项目检查：

```powershell
py -3 tools\check_project.py
```

只检查语法和项目结构：

```powershell
py -3 tools\check_project.py --skip-tests
```

只运行 Python 测试：

```powershell
py -3 -m unittest discover -s tests -p "test_*.py" -v
```

在提供 `make` 的 macOS/Linux 环境中，也可以使用：

```bash
make check
make test
make release-check
```

发布前请同时阅读 [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)。

## 安全与隐私

- 原生服务默认只绑定 `127.0.0.1`，不要改成公网监听地址。
- 只添加你已经检查并信任的命令、脚本和工作目录。
- 结束进程、批量停止和删除应用均属于高风险操作，请确认目标后再执行。
- 总控台只允许结束当前用户拥有的进程，但它仍继承当前用户的文件和程序权限。
- 不要公开 `config.json`、应用日志、个人路径、访问令牌、密钥或未经脱敏的截图。
- Docker 端口映射应优先绑定 `127.0.0.1`。
- 发现安全问题时，请按 [`SECURITY.md`](SECURITY.md) 中的方式报告，不要在公开 Issue 中披露敏感细节。

## 常见问题

### 启动后无法访问 9600

9600 可能已被其他程序占用。查看终端输出中的实际地址，或依次尝试 `http://127.0.0.1:9601` 至 `http://127.0.0.1:9609`。

轻量健康检查地址：

```text
http://127.0.0.1:9600/api/health
```

### Windows 双击后没有界面

1. 在 PowerShell 中运行 `py -3 --version`。
2. 执行 `py -3 server.py` 查看明确错误。
3. 检查 Windows 防火墙或安全软件是否拦截本地 Python。
4. 如果使用 EXE，首次启动请等待单文件资源释放完成。

### 应用无法启动

- 打开卡片的“配置与运行诊断”和日志。
- 确认工作目录、脚本和运行时仍然存在。
- 确认配置端口没有被其他进程占用。
- 将在普通 PowerShell 中可正常运行的命令原样填入总控台。

### 配置损坏或丢失

停止总控台，备份当前数据目录，然后检查同目录的 `config.json.bak`。程序在主配置不可读时会尝试读取备份；两份都不可用时会进入只读保护，避免用空配置覆盖原文件。

### Docker 中看不到宿主机服务

这是容器隔离的正常结果，不是端口扫描故障。请改用 Windows 原生运行方式管理宿主机进程。

## 相关文档

- [`CHANGELOG.md`](CHANGELOG.md)：版本变化记录
- [`DOCKER.md`](DOCKER.md)：Docker 完整说明
- [`DEPLOYMENT_REPORT.md`](DEPLOYMENT_REPORT.md)：部署验证记录
- [`CONTRIBUTING.md`](CONTRIBUTING.md)：贡献指南
- [`SECURITY.md`](SECURITY.md)：安全报告规范
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)：第三方组件说明
- [`ASSET_PROVENANCE.md`](ASSET_PROVENANCE.md)：素材来源与许可记录

## 项目来源与许可

本仓库基于 [laogou717/local-ops](https://github.com/laogou717/local-ops) 继续开发，并在其基础上增强 Windows 支持、桌面 EXE 打包、Docker 部署和技能工作台。感谢原项目作者及所有贡献者。

项目自有代码和文档采用 [`MIT License`](LICENSE)。Lucide、Geist Mono 及其他第三方素材适用各自许可证，详见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) 和 [`ASSET_PROVENANCE.md`](ASSET_PROVENANCE.md)。
