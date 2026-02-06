# PilotDeck
![PilotDeckIcon](docs/img/icon-black.png)

中文说明: [README.md](./README.md)

PilotDeck is a **ProjectOps × AgentOps console** for individual developers and internal teams. It focuses on project delivery and auditability, with understandable, editable, and reviewable agent collaboration plus cost visibility.

---

## Core Capabilities
- **Project tracking**: manage status, progress, and milestones with `projects / runs / events / actions`
- **Reviewable process**: append-only timeline records who did what, when, why, and with what impact
- **Cost observability**: report `usage` and view token/cost trends via `stats/tokens`
- **Lightweight self-hosting**: Flask + Vue 3 + SQLite (single-file DB, no external DB service)
- **Safe concurrency**: optimistic control with `updatedAt + ifUpdatedAt`
- **Semantic actions**: Agent Action is the unified write path (optional project update + automatic audit event + idempotency)

---

## Quick Start (Local Development)

### Requirements
- Python 3.10+
- Node.js 22.x (see `NODE_VERSION.md`)

### Install Dependencies
```bash
python -m pip install -r requirements.txt
```

```bash
cd frontend
npm ci
```

### Run Service

Backend:

```bash
python server/main.py
```

Build frontend (first run or after frontend changes):

```bash
cd frontend
npm run build
```

Default endpoints:

* Web UI: [http://localhost:8689/](http://localhost:8689/)
* API: [http://localhost:8689/api](http://localhost:8689/api)

---

## Environment Variables

* `PM_PORT`: service port (default `8689`)
* `PM_DEBUG`: debug flag (default `0`)
* `PM_DB_FILE`: SQLite file path (default `data/pm.db`)
* `PM_ADMIN_TOKEN`: admin token (backup/restore/deploy)
* `PM_AGENT_TOKEN`: agent API token

PowerShell example:

```powershell
$env:PM_ADMIN_TOKEN = "<your-admin-token>"
$env:PM_AGENT_TOKEN = "<your-agent-token>"
python server\main.py
```

---

## Deployment (Linux)

```bash
sudo ./deploy_pull_restart.sh
```

Optional automatic backup:

```bash
sudo ./setup_auto_backup.sh
```

---

## Community & Support

* Issues / Feature Requests: please use GitHub Issues
* Questions are welcome; feel free to contact the author

---

## Sponsor

If my projects help your work, please consider sponsoring the development and maintenance :)

---
