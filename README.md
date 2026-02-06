# PilotDeck
![PilotDeckIcon](docs/img/icon-black.png)

English README: [README.en.md](./README.en.md)

PilotDeck 是面向个人开发者与团队内部的 **ProjectOps × AgentOps 控制台**：以**项目推进**与**审计可追踪**为核心，提供可理解、可编辑、可审查的 Agent 协作与成本可观测能力，降低协作摩擦与进度漂移。

---

## 核心能力
- **项目推进**：以 `projects / runs / events / actions` 管理任务状态、进展与里程碑  
- **过程可审查**：Timeline（append-only）记录“谁在何时做了什么、为什么做、产生了什么影响”  
- **成本可观测**：上报 `usage` 并通过 `stats/tokens` 聚合查看 token/cost 趋势  
- **轻量自托管**：Flask + Vue3 + SQLite（单文件 DB，无需额外数据库）  
- **并发安全**：`updatedAt + ifUpdatedAt` 乐观并发控制  
- **语义化动作**：Agent Action 作为统一写入口（可选更新项目 + 自动写入审计事件 + 幂等）

---

## 快速开始（本地开发）

### 环境要求
- Python 3.10+
- Node.js 22.x（见 `NODE_VERSION.md`）

### 安装依赖
```bash
python -m pip install -r requirements.txt
```

```bash
cd frontend
npm ci
```

### 启动服务

后端：

```bash
python server/main.py
```

前端构建（首次或更新前端后）：

```bash
cd frontend
npm run build
```

默认访问：

* Web UI: [http://localhost:8689/](http://localhost:8689/)
* API: [http://localhost:8689/api](http://localhost:8689/api)

---

## 环境变量

* `PM_PORT`：服务端口（默认 `8689`）
* `PM_DEBUG`：调试开关（默认 `0`）
* `PM_DB_FILE`：SQLite 文件路径（默认 `data/pm.db`）
* `PM_ADMIN_TOKEN`：管理接口口令（备份/恢复/部署）
* `PM_AGENT_TOKEN`：Agent API 口令

PowerShell 示例：

```powershell
$env:PM_ADMIN_TOKEN = "<your-admin-token>"
$env:PM_AGENT_TOKEN = "<your-agent-token>"
python server\main.py
```

---

## 部署（Linux）

```bash
sudo ./deploy_pull_restart.sh
```

可选自动备份：

```bash
sudo ./setup_auto_backup.sh
```

---

## 交流与支持

* Issue / Feature Request：请使用 GitHub Issues
* 如有问题，欢迎联系作者交流。

---

## 赞助 / Sponsor

如果你在工作中受益于我开发维护的项目，请考虑支持一下我的工作 :)

---

