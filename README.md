# MyProjectManager

一个基于 GitHub 仓库的“个人项目统一管理”Demo：
- 项目数据以 `JSON` 文件形式存储在仓库里（便于版本管理、审计、回滚）
- 提供 Python CLI 脚本做数据管理（可选）
- 提供 Flask 后端 API + 原生 Web 前端，实现项目的增删改查与统计展示

## 功能

- 项目列表展示：名称、状态、优先级、分类、进度、预算、标签
- 条件筛选：状态 / 优先级 / 分类
- CRUD：新增 / 编辑 / 删除项目
- 统计：按状态/优先级/分类聚合 + 财务汇总

## 目录结构

- `data/projects.json`：项目数据（你日常维护的核心）
- `data/schema.json`：数据结构 JSON Schema（用于约束字段含义/结构）
- `scripts/project_manager.py`：CLI 数据管理脚本（增删改查/统计）
- `server/api_server.py`：后端 API + 静态前端托管
- `web/index.html`：前端页面
- `web/css/style.css`：前端样式
- `web/js/app.js`：前端逻辑（调用 API）

## 环境要求

- Python 3.8+（必需，建议 3.10+）

说明：本项目依赖（`requirements.txt`）要求 Python 3.8+。Linux 服务器上推荐使用 `/usr/local/bin/python3` 指向 Python 3.8+，避免改动 `/usr/bin/python`（可能影响 yum / 系统脚本）。

## 快速开始（本地运行）

### 1) 安装依赖

在仓库根目录执行：

```bash
python -m pip install -r requirements.txt
```

### 2) 启动服务

方式 A（直接运行）：

```bash
python server/api_server.py
```

可选环境变量：

```bash
export PM_PORT=8689   # 端口，默认 8689
export PM_DEBUG=1     # 调试模式：1 开启，默认关闭
```

方式 B（Windows 脚本）：

```bat
start_server.bat
```

或 PowerShell：

```powershell
start_server.ps1
```

## 部署到云服务器（Linux）

本项目默认监听 `8689`。服务器部署场景使用 `deploy_pull_restart.sh` 一键拉取、安装依赖并重启服务。

仓库内已提供两条适合在服务器上执行的脚本：

1) 从 GitHub 拉取更新并部署、重启：`deploy_pull_restart.sh`
2) 将本地修改（默认仅数据）推送到 GitHub：`push_data_to_github.sh`

脚本说明见脚本文件头部注释。

### 1) 服务器初始化（一次性）

确保服务器已安装 Python 3.8+（例如已安装 `python3.8`），并按以下方式提供 `python3`：

```bash
ln -sf /usr/local/bin/python3.8 /usr/local/bin/python3
ln -sf /usr/local/bin/pip3.8 /usr/local/bin/pip3
python3 -V
```

注意：不要把 `/usr/bin/python` 指向 3.8（可能影响 yum / 系统脚本）。

### 2) 部署/更新（推荐运维方式）

在服务器仓库根目录执行：

```bash
./deploy_pull_restart.sh
```

脚本行为：
- `git pull --rebase` 拉取最新代码
- 使用 `${ROOT}/.venv` 创建虚拟环境并安装 `requirements.txt`
- 若存在 systemd：自动写入/启用 `/etc/systemd/system/myprojectmanager.service` 并重启
- 若无 systemd：使用 `nohup` 启动（日志写入 `server.log`，PID 写入 `.server.pid`）

### 3) 常用运维命令（systemd）

```bash
systemctl status myprojectmanager
systemctl restart myprojectmanager
journalctl -u myprojectmanager -f
```

### 3) 访问

- Web 界面：`http://<server-ip>:8689/`
- API 基地址：`http://<server-ip>:8689/api`
- 健康检查：`http://<server-ip>:8689/api/health`

本地默认端口为 `8689`（除非设置了 `PM_PORT`）。

## API 说明（简要）

- `GET /api/projects`：获取项目列表（支持 `status` / `priority` / `category` 查询参数）
- `GET /api/projects/{id}`：获取单个项目
- `POST /api/projects`：创建项目
- `PUT /api/projects/{id}`：更新项目
- `DELETE /api/projects/{id}`：删除项目
- `GET /api/stats`：统计信息

## CLI 脚本（可选）

列出项目：

```bash
python scripts/project_manager.py list
```

查看统计：

```bash
python scripts/project_manager.py stats
```

添加项目：

```bash
python scripts/project_manager.py add --name "示例项目" --status planning --priority medium --category "内容创作"
```

更新项目：

```bash
python scripts/project_manager.py update proj-001 --progress 50 --status in-progress
```

## 数据维护建议

- 你可以直接编辑 `data/projects.json`（JSON），并通过 Git 提交记录每次变更
- 如果多人协作：建议以 PR 的方式合并数据变更，避免冲突
