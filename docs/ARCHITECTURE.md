# PilotDeck Architecture Overview

This document provides a high-level system architecture overview for all developers.

> **For detailed architecture documentation**:
> - Frontend: [../frontend/docs/ARCHITECTURE.md](../frontend/docs/ARCHITECTURE.md)
> - Backend: [../server/docs/ARCHITECTURE.md](../server/docs/ARCHITECTURE.md)

---

## System Overview

PilotDeck is a self-hosted **ProjectOps × AgentOps** control console for individual developers and internal teams. It provides project management with agent integration, audit trail, and cost observability.

**Core Philosophy**:
- **Project-driven**: `projects / runs / events / actions` model
- **Process auditable**: Append-only timeline (who, what, when, why)
- **Cost observable**: Token/cost tracking and aggregation
- **Lightweight**: Single-file SQLite database, no external dependencies
- **Concurrent-safe**: Optimistic locking with `updatedAt + ifUpdatedAt`

---

## Technology Stack

### Backend
- **Framework**: Flask 3.x (Python 3.10+)
- **Database**: SQLite 3 with WAL mode
- **Architecture**: Service-oriented with blueprints
- **Auth**: Session cookies (UI) + Token headers (Admin/Agent)

### Frontend
- **Framework**: Vue 3 (Composition API)
- **State**: Pinia
- **Router**: Vue Router 5
- **Build**: Vite 5
- **Language**: TypeScript
- **Styling**: CSS Variables (Design Tokens)

---

## Repository Layout

```
PilotDeck/
├── server/                    # Flask backend
│   ├── main.py                # Entry point
│   ├── mypm/                  # Main package
│   │   ├── app.py             # Application factory
│   │   ├── config.py          # Configuration
│   │   ├── domain/            # Domain logic
│   │   ├── storage/           # SQLite stores
│   │   ├── services/          # Business logic
│   │   └── api/               # REST blueprints
│   └── docs/                  # Backend documentation
│       ├── README.md          # Backend dev guide
│       ├── ARCHITECTURE.md    # Backend architecture
│       ├── API_REFERENCE.md   # API quick reference
│       ├── DATABASE.md        # DB operations
│       └── AUTHENTICATION.md  # Auth system
├── frontend/                  # Vue 3 frontend
│   ├── src/
│   │   ├── api/               # API client
│   │   ├── components/        # Vue components
│   │   ├── stores/            # Pinia stores
│   │   ├── pages/             # Page components
│   │   ├── router/            # Vue Router
│   │   └── styles/            # CSS tokens
│   └── docs/                  # Frontend documentation
│       ├── README.md          # Frontend dev guide
│       ├── ARCHITECTURE.md    # Frontend architecture
│       └── COMPONENTS.md      # Component library
├── docs/                      # Product documentation
│   ├── README.md              # Documentation index
│   ├── ARCHITECTURE.md        # This file (system overview)
│   ├── agent/                 # Agent integration docs
│   │   ├── AGENT_API.md       # Agent API guide (EN)
│   │   ├── AGENT_API.zh-CN.md # Agent API guide (中文)
│   │   ├── PILOTDECK_SKILL.md # OhMyOpenCode skill (EN)
│   │   └── PILOTDECK_SKILL.zh-CN.md
│   └── product/               # Product templates
│       ├── PROJECT_STATUS_TEMPLATE.md
│       └── PROJECT_STATUS_TEMPLATE.zh-CN.md
├── data/                      # Runtime data (gitignored)
│   └── pm.db                  # SQLite database
└── scripts/                   # Helper scripts
```

---

## Data Model

### Core Entities

```
Project (projects table)
├── id, name, description, notes
├── status, priority, progress (0-100)
├── budget, actualCost, revenue
├── tags, category
├── github, workspace
├── createdAt, updatedAt (ISO 8601)
└── payload_json (full data)

AgentRun (agent_runs table)
├── id, projectId, agentId
├── title, summary, status
├── startedAt, finishedAt
├── links, tags, metrics
└── payload_json

AgentEvent (agent_events table)
├── id, ts, type, level
├── projectId, runId, agentId
├── title, message
└── data (arbitrary JSON)
```

### Relationships

```
Project (1) ──< (N) AgentRun ──< (N) AgentEvent
```

- One project can have multiple runs
- One run can have multiple events
- Events are append-only (immutable audit trail)

---

## Key Architectural Patterns

### 1. Optimistic Concurrency Control

Prevents lost updates in concurrent scenarios:

```
Client A reads project: updatedAt = "2026-02-11T15:00:00Z"
Client B reads project: updatedAt = "2026-02-11T15:00:00Z"

Client A updates with ifUpdatedAt="2026-02-11T15:00:00Z" → Success
  New updatedAt = "2026-02-11T15:01:00Z"

Client B updates with ifUpdatedAt="2026-02-11T15:00:00Z" → Conflict (409)
  Must re-read and retry
```

### 2. Idempotent Operations

Agent operations use deterministic IDs:

```python
# Safe to retry - same ID returns existing resource
POST /api/agent/runs
{
  "id": "run-abc123",  # Client-generated ID
  "projectId": "proj-456",
  "status": "running"
}
```

### 3. Semantic Actions

Unified interface for project updates + audit events:

```python
POST /api/agent/actions
{
  "action": "bump_progress",
  "params": { "delta": 10, "reason": "Milestone completed" }
}

# Result:
# 1. Project progress += 10
# 2. AgentEvent created with action details
```

Available actions: `set_status`, `set_priority`, `set_progress`, `bump_progress`, `append_note`, `add_tag`, `remove_tag`

### 4. Indexed JSON Storage

**Design**: Index commonly-queried fields + store full JSON payload

```sql
CREATE TABLE projects (
  id TEXT PRIMARY KEY,
  name TEXT,              -- Indexed for search
  status TEXT,            -- Indexed for filtering
  updatedAt TEXT,         -- Indexed for sorting
  payload_json TEXT       -- Full project data
);
```

**Benefits**:
- Fast queries on indexed fields
- Full data flexibility in JSON
- Schema evolution without migrations

---

## Request Flow

### Web UI Request
```
Browser → Flask Session Auth → Blueprint → Service → Store → SQLite
         ↓                                                      ↓
    [Session Cookie]                                    [SQL Query]
```

### Agent API Request
```
Agent → Token Auth (optional) → Blueprint → Service → Store → SQLite
       ↓                                                       ↓
  [X-PM-Agent-Token]                               [Optimistic Lock Check]
```

### Admin Operation
```
Admin → Token Auth → Blueprint → Service → SQLite Backup/Restore
       ↓                                    ↓
  [X-PM-Token]                      [Python sqlite3.backup()]
```

---

## Authentication Mechanisms

| Type | Use Case | Auth Method |
|------|----------|-------------|
| **Session** | Web UI | Flask session cookies |
| **Admin Token** | Backup/Restore/Deploy | `X-PM-Token` header |
| **Agent Token** | Agent API | `X-PM-Agent-Token` header (optional) |

**Default User**:
- Username: `admin`
- Password: `admin`

---

## Key Operational Flows

### 1. Project Updates from Agents

```
1. Agent reads project (GET /api/projects/<id>)
   → Captures updatedAt timestamp

2. Agent performs work

3. Agent updates project:
   Option A: Direct PATCH with ifUpdatedAt
   Option B: Semantic action (POST /api/agent/actions)

4. Agent writes audit event (POST /api/agent/events)

5. Agent updates run status (PATCH /api/agent/runs/<id>)
```

### 2. Database Backup & Restore

**Backup**:
```
UI → GET /api/admin/backup
  → Server creates consistent SQLite snapshot
  → Returns file: pm_backup_<timestamp>.db
```

**Restore**:
```
UI → POST /api/admin/restore (upload snapshot)
  → Server saves current DB as pm.db.bak.<timestamp>
  → Atomically replaces pm.db
  → Sets maintenance flag during restore
```

### 3. Timeline Visualization

```
UI opens project detail
  → Fetches runs: GET /api/agent/runs?projectId=<id>
  → Fetches events: GET /api/agent/events?projectId=<id>
  → Merges & sorts by timestamp (newest first)
  → Renders with AgentTimeline component
```

---

## Component Architecture

### Backend Services

```
API Blueprint (HTTP)
    ↓
Service Layer (Business Logic)
    ↓
Store Layer (Data Access)
    ↓
SQLite Database (Persistence)
```

### Frontend Components

```
App.vue
  ↓
Router (Auth Guards)
  ↓
Pages (ProjectsPage, LoginPage)
  ↓
Components (ProjectCard, ProjectDetailModal, AgentTimeline)
  ↓
Stores (Pinia: projects, agent, auth)
  ↓
API Client (fetch with credentials)
```

---

## Deployment

### Development

```bash
# Backend
python server/main.py  # http://localhost:8689

# Frontend (dev server)
cd frontend && npm run dev  # http://localhost:5173
```

### Production

```bash
# Build frontend
cd frontend && npm run build

# Start backend (serves built frontend at /)
python server/main.py
```

### Linux Deployment

```bash
# Deploy script (pull, build, restart)
sudo ./deploy_pull_restart.sh

# Optional: Setup auto-backup (systemd timer)
sudo ./setup_auto_backup.sh
```

---

## Configuration

### Environment Variables

```bash
PM_PORT=8689                    # Server port
PM_DEBUG=0                      # Debug mode (0/1)
PM_DB_FILE=data/pm.db           # SQLite database path
PM_ADMIN_TOKEN=<secret>         # Admin operations token
PM_AGENT_TOKEN=<secret>         # Agent API token (optional)
PM_SECRET_KEY=<secret>          # Flask session secret (auto-generated if not set)
```

### Database

- **File**: `data/pm.db`
- **Mode**: WAL (Write-Ahead Logging)
- **Backup**: `data/pm_backup.db` (via backup script)
- **Rollback**: `data/pm.db.bak.<timestamp>` (created on restore)

---

## Documentation Navigation

### For Developers

| Role | Start Here |
|------|-----------|
| **Frontend Developer** | [../frontend/docs/README.md](../frontend/docs/README.md) |
| **Backend Developer** | [../server/docs/README.md](../server/docs/README.md) |
| **Agent Integrator** | [./agent/AGENT_API.md](./agent/AGENT_API.md) |
| **System Admin** | [../server/docs/DATABASE.md](../server/docs/DATABASE.md) |

### Quick References

- **API Endpoints**: [../server/docs/API_REFERENCE.md](../server/docs/API_REFERENCE.md)
- **Component Library**: [../frontend/docs/COMPONENTS.md](../frontend/docs/COMPONENTS.md)
- **Database Operations**: [../server/docs/DATABASE.md](../server/docs/DATABASE.md)
- **Authentication**: [../server/docs/AUTHENTICATION.md](../server/docs/AUTHENTICATION.md)

---

## Design Principles

### Backend
- **Service-oriented**: Business logic in services, not controllers
- **Optimistic locking**: Prevent lost updates without pessimistic locks
- **Idempotency**: Safe retries with client-generated IDs
- **Append-only events**: Immutable audit trail

### Frontend
- **Component-driven**: Reusable Vue 3 components with TypeScript
- **State management**: Centralized Pinia stores
- **Design tokens**: Theme-agnostic CSS variables
- **Progressive enhancement**: Works without JavaScript for critical paths

### Database
- **WAL mode**: Concurrent reads without blocking
- **Indexed JSON**: Fast queries + flexible schema
- **Consistent snapshots**: Safe backups without downtime
- **Foreign keys**: Data integrity enforced

---

## Security Considerations

- **Authentication**: Multi-layer (session, admin token, agent token)
- **Concurrency**: Optimistic locking prevents race conditions
- **Backup**: Consistent snapshots via Python sqlite3.backup()
- **Secrets**: Never commit tokens to git, use environment variables
- **HTTPS**: Required in production (set `SESSION_COOKIE_SECURE=True`)

---

## Performance Characteristics

- **Concurrent reads**: Excellent (SQLite WAL mode)
- **Concurrent writes**: Good (optimistic locking + retry)
- **Database size**: Scales to millions of events (SQLite limit: 281 TB)
- **Backup/Restore**: Fast (single-file copy, <1s for typical databases)
- **Frontend**: Static build, cacheable assets, minimal runtime

---

## Future Enhancements

- [ ] Multi-user support with RBAC
- [ ] Real-time updates (WebSocket)
- [ ] Advanced analytics dashboard
- [ ] Gantt chart timeline view
- [ ] Export reports (PDF, CSV)
- [ ] Webhook integrations

---

**Last Updated**: 2026-02-11  
**Architecture Version**: 2.0 (Refactored documentation structure)

**Related Documentation**:
- [Documentation Index](./README.md)
- [Frontend Architecture](../frontend/docs/ARCHITECTURE.md)
- [Backend Architecture](../server/docs/ARCHITECTURE.md)
- [Agent API Guide](./agent/AGENT_API.md)
