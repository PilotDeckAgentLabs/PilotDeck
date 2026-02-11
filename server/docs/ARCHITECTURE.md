# PilotDeck Backend Architecture

This document describes the backend architecture for developers working on the Flask server.

> **For complete system architecture**, see [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)

---

## Technology Stack

- **Framework**: Flask 3.x (application factory pattern)
- **Database**: SQLite 3 with WAL mode
- **Language**: Python 3.10+
- **Architecture**: Service-oriented with blueprints
- **Concurrency Control**: Optimistic locking (`ifUpdatedAt`)

---

## Directory Structure

```
server/
├── main.py                    # Application entry point
└── mypm/                      # Main package
    ├── app.py                 # Flask application factory
    ├── config.py              # Configuration management
    ├── domain/                # Domain logic
    │   ├── models.py          # Data normalization and validation
    │   ├── enums.py           # Project status/priority enums
    │   ├── auth.py            # Authentication decorators
    │   └── errors.py          # Custom exception types
    ├── storage/               # Data persistence layer
    │   ├── sqlite_db.py       # Database connection & migrations
    │   └── sqlite_store.py    # Store classes (Projects, Runs, Events)
    ├── services/              # Business logic services
    │   ├── project_service.py # Project CRUD with concurrency
    │   ├── agent_service.py   # Agent runs management
    │   └── deploy_service.py  # Deploy job management
    └── api/                   # REST API blueprints
        ├── meta.py            # Health check & metadata
        ├── projects.py        # Project CRUD endpoints
        ├── stats.py           # Statistics & aggregation
        ├── agent.py           # Agent runs/events/actions
        ├── agent_ops.py       # Agent profiles & capabilities
        ├── admin_ops.py       # Admin operations (backup/restore/deploy)
        └── auth.py            # Authentication endpoints
```

---

## Application Factory

### `server/mypm/app.py`

Creates Flask app with:
- Configuration loading (`Config`)
- Database initialization and migrations
- Store/Service initialization
- Blueprint registration
- Static file serving (frontend `dist/`)
- CORS configuration
- Session management
- Maintenance mode flag (`restoring_db`)

**Key responsibilities**:
- Initializes SQLite database on first run
- Runs schema migrations
- Serves Vue 3 frontend from `/` (SPA fallback)
- Blocks API calls during database restore

---

## Configuration

### `server/mypm/config.py`

**Environment Variables**:
```python
PM_PORT=8689                    # Server port (default: 8689)
PM_DEBUG=0                      # Debug mode (0/1)
PM_DB_FILE=data/pm.db           # SQLite database path
PM_ADMIN_TOKEN=<secret>         # Required for admin operations
PM_AGENT_TOKEN=<secret>         # Optional, for agent API
PM_SECRET_KEY=<secret>          # Flask session secret (auto-generated if not set)
```

**Paths Configuration**:
- `ROOT_DIR`: Project root directory
- `DATA_DIR`: Runtime data directory (`data/`)
- `DB_FILE`: SQLite database file path
- `FRONTEND_DIST_DIR`: Built frontend assets (`frontend/dist/`)

**Deploy Integration**:
- Deploy state/log files
- Systemd unit prefix

---

## Domain Layer

### `server/mypm/domain/models.py`

**Purpose**: Data normalization and validation for API payloads.

**Key Functions**:
- `normalize_project(data: dict) -> dict` - Validates and normalizes project data
- `normalize_agent_run(data: dict) -> dict` - Validates run data
- `normalize_agent_event(data: dict) -> dict` - Validates event data

**Responsibilities**:
- Set default values for optional fields
- Validate required fields
- Normalize timestamps (ISO 8601)
- Ensure data consistency

### `server/mypm/domain/enums.py`

Project status and priority enumerations:

```python
PROJECT_STATUSES = ['planning', 'in-progress', 'paused', 'completed', 'cancelled']
PROJECT_PRIORITIES = ['low', 'medium', 'high', 'urgent']
RUN_STATUSES = ['running', 'completed', 'failed', 'cancelled']
EVENT_LEVELS = ['debug', 'info', 'warn', 'error']
EVENT_TYPES = ['note', 'action', 'result', 'error', 'milestone']
```

### `server/mypm/domain/auth.py`

**Authentication Mechanisms**:

#### 1. Session-Based Auth (Web UI)
```python
@require_login
def my_endpoint():
    user = g.user  # Current logged-in user
    # ...
```

- Uses Flask session cookies
- Login: `POST /api/auth/login`
- Logout: `POST /api/auth/logout`
- Check: `GET /api/auth/me`

#### 2. Token-Based Auth (Admin)
```python
@require_admin
def admin_operation():
    # Header: X-PM-Token: <PM_ADMIN_TOKEN>
    # ...
```

- Required for backup/restore/deploy operations
- Must match `PM_ADMIN_TOKEN` environment variable

#### 3. Agent Token Auth (Optional)
```python
@require_agent  # Optional if PM_AGENT_TOKEN not set
def agent_endpoint():
    # Header: X-PM-Agent-Token: <PM_AGENT_TOKEN>
    # ...
```

- If `PM_AGENT_TOKEN` is configured, agent endpoints require this header
- If not configured, agent endpoints are open

### `server/mypm/domain/errors.py`

Custom exception types for services:

```python
class ProjectNotFoundError(Exception): pass
class ProjectModifiedError(Exception): pass  # Optimistic lock conflict
class ValidationError(Exception): pass
```

---

## Storage Layer (SQLite)

### `server/mypm/storage/sqlite_db.py`

**Database Connection**:
- SQLite in WAL (Write-Ahead Logging) mode
- Connection pool with pragmas:
  - `journal_mode=WAL`
  - `busy_timeout=5000ms`
  - `foreign_keys=ON`
  - `synchronous=NORMAL`

**Schema Management**:
- Version-based migrations using `PRAGMA user_version`
- Current version: 3 (includes users table)
- Automatic migration on app startup

**Schema Tables**:

#### `projects`
```sql
CREATE TABLE projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT,
  priority TEXT,
  progress REAL,
  category TEXT,
  createdAt TEXT,
  updatedAt TEXT,
  payload_json TEXT NOT NULL
);
```

#### `agent_runs`
```sql
CREATE TABLE agent_runs (
  id TEXT PRIMARY KEY,
  projectId TEXT,
  agentId TEXT,
  title TEXT,
  status TEXT,
  createdAt TEXT,
  updatedAt TEXT,
  startedAt TEXT,
  finishedAt TEXT,
  payload_json TEXT NOT NULL
);
```

#### `agent_events`
```sql
CREATE TABLE agent_events (
  id TEXT PRIMARY KEY,
  ts TEXT,
  type TEXT,
  level TEXT,
  projectId TEXT,
  runId TEXT,
  agentId TEXT,
  title TEXT,
  payload_json TEXT NOT NULL
);
```

#### `agent_profiles`
AgentOps profile cards (agent metadata).

#### `agent_capabilities`
PromptPack + SkillPack bundles.

#### `token_usage_records`
Token and cost usage tracking.

#### `users`
User authentication table:
```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

#### `meta`
Key-value metadata storage.

**Design Pattern**: Indexed columns + full JSON payload (`payload_json`)
- Fast queries on indexed fields
- Full data preservation in JSON
- Flexible schema evolution

### `server/mypm/storage/sqlite_store.py`

**Store Classes**:

#### `ProjectsStore`
- `list(filters)` - List projects with optional filters
- `get(id)` - Get project by ID
- `create(data)` - Create new project
- `patch(id, updates)` - Partial update with optimistic locking
- `delete(id)` - Delete project
- `reorder(order)` - Persist manual sort order
- `batch_update(updates)` - Batch update multiple projects
- `get_statistics()` - Aggregate statistics

#### `AgentRunsStore`
- `create(data)` - Create run (idempotent by ID)
- `get(id)` - Get run by ID
- `list(filters)` - List runs with filters
- `patch(id, updates)` - Update run

#### `AgentEventsStore`
- `append(data)` - Append new event (append-only)
- `exists(id)` - Check if event exists
- `list(filters)` - List events with filters

---

## Services Layer

### `server/mypm/services/project_service.py`

**Purpose**: Project business logic and concurrency control.

**Key Methods**:
- `create_project(data)` - Validate and create project
- `update_project(id, updates, if_updated_at)` - Update with optimistic locking
- `delete_project(id)` - Delete project and associated data
- `get_project(id)` - Retrieve project by ID

**Optimistic Concurrency Control**:
```python
# Client reads project with updatedAt timestamp
project = get_project("proj-123")
# updatedAt = "2026-02-11T15:00:00Z"

# Client updates with ifUpdatedAt
update_project(
    id="proj-123",
    updates={"progress": 85},
    if_updated_at="2026-02-11T15:00:00Z"
)
# Success: updatedAt matches, update applied
# Conflict: updatedAt changed, raises ProjectModifiedError
```

### `server/mypm/services/agent_service.py`

**Purpose**: Agent run lifecycle management.

**Key Methods**:
- `create_run(data)` - Create run (idempotent by ID)
- `update_run(id, updates)` - Update run status/metrics
- `get_run(id)` - Retrieve run by ID
- `list_runs(filters)` - List runs with filters

**Idempotency**: Creating a run with existing ID returns existing run.

### `server/mypm/services/deploy_service.py`

**Purpose**: Manage server deployment jobs.

**Key Methods**:
- `trigger_deploy()` - Start deploy script (`deploy_pull_restart.sh`)
- `get_deploy_status()` - Check deploy job status
- `get_deploy_log()` - Retrieve deploy output

**State Tracking**:
- State file: `data/deploy.state.json`
- Log file: `data/deploy.log`

---

## API Blueprints

### `server/mypm/api/meta.py`

**Endpoints**:
- `GET /api/health` - Health check
- `GET /api/meta` - System metadata (enums, capabilities, auth requirements)

**Purpose**: Provide system information to clients.

### `server/mypm/api/projects.py`

**Endpoints**:
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create project
- `GET /api/projects/<id>` - Get project by ID
- `PUT /api/projects/<id>` - Full update
- `PATCH /api/projects/<id>` - Partial update (with `ifUpdatedAt`)
- `DELETE /api/projects/<id>` - Delete project
- `POST /api/projects/reorder` - Save sort order
- `POST /api/projects/batch` - Batch update

**Auth**: All endpoints require `@require_login`

### `server/mypm/api/stats.py`

**Endpoints**:
- `GET /api/stats` - Project statistics
- `GET /api/stats/tokens` - Token usage statistics

**Auth**: Requires `@require_login`

### `server/mypm/api/agent.py`

**Endpoints**:
- `GET /api/agent/runs` - List runs
- `POST /api/agent/runs` - Create run (idempotent)
- `GET /api/agent/runs/<id>` - Get run
- `PATCH /api/agent/runs/<id>` - Update run
- `GET /api/agent/events` - List events
- `POST /api/agent/events` - Append event
- `POST /api/agent/actions` - Semantic actions

**Auth**: `@require_agent` (optional if `PM_AGENT_TOKEN` not set)

**Agent Actions**:
Semantic operations that update projects and create audit events:

| Action | Description |
|--------|-------------|
| `set_status` | Update project status |
| `set_priority` | Update project priority |
| `set_progress` | Set absolute progress (0-100) |
| `bump_progress` | Increment progress by delta |
| `append_note` | Append to project notes |
| `add_tag` | Add tag to project |
| `remove_tag` | Remove tag from project |

**Action Request**:
```json
{
  "id": "action-001",
  "projectId": "proj-123",
  "runId": "run-456",
  "agentId": "claude-sonnet",
  "action": "bump_progress",
  "params": {
    "delta": 10,
    "reason": "Completed milestone"
  },
  "recordOnly": false
}
```

### `server/mypm/api/agent_ops.py`

**Endpoints**:
- `GET /api/agent/profiles` - List agent profiles
- `POST /api/agent/profiles` - Create agent profile
- `GET /api/agent/capabilities` - List capabilities
- `POST /api/agent/capabilities` - Create capability
- `GET /api/agent/usage` - List token usage
- `POST /api/agent/usage` - Record token usage

**Auth**: Mixed (profiles/capabilities require login, usage requires agent token)

### `server/mypm/api/admin_ops.py`

**Endpoints**:
- `GET /api/admin/backup` - Export database snapshot
- `POST /api/admin/restore` - Restore database from snapshot
- `POST /api/admin/deploy` - Trigger deploy job
- `GET /api/admin/deploy/status` - Get deploy status
- `GET /api/admin/deploy/log` - Get deploy log

**Auth**: All require `@require_admin`

**Backup Process**:
1. Client requests `GET /api/admin/backup`
2. Server creates consistent SQLite snapshot
3. Returns file as download (`pm_backup_<timestamp>.db`)

**Restore Process**:
1. Client uploads snapshot via `POST /api/admin/restore`
2. Server saves current DB as `pm.db.bak.<timestamp>`
3. Atomically replaces `pm.db` with uploaded snapshot
4. Sets maintenance flag during restore

### `server/mypm/api/auth.py`

**Endpoints**:
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Current user info
- `POST /api/auth/logout` - User logout

**Default User**:
- Username: `admin`
- Password: `admin`

**Security Notes**:
- Passwords stored as SHA256 hash (consider bcrypt for production)
- Session secret can be set via `PM_SECRET_KEY`
- Use HTTPS in production (`SESSION_COOKIE_SECURE=True`)

---

## Key Operational Flows

### Project Updates from Agents

1. Agent reads project (`GET /api/projects/<id>`) and captures `updatedAt`
2. Agent applies update:
   - Option A: Direct update (`PATCH /api/projects/<id>` with `ifUpdatedAt`)
   - Option B: Semantic action (`POST /api/agent/actions`)
3. Agent writes trace event (`POST /api/agent/events`)
4. Agent updates run status (`PATCH /api/agent/runs/<id>`)

### Backup Export and Restore

**Export**:
- `GET /api/admin/backup` returns consistent snapshot as downloadable file
- Uses Python's `sqlite3.backup()` API for safety

**Restore**:
- `POST /api/admin/restore` accepts uploaded snapshot
- Atomically replaces `data/pm.db`
- Creates rollback file: `pm.db.bak.<timestamp>`

---

## Database Operations

### Backup

**UI Export** (recommended):
1. Open Ops panel
2. Enter `PM_ADMIN_TOKEN`
3. Click "Export backup"

**CLI Snapshot**:
```bash
python scripts/sqlite_backup.py --db data/pm.db --out data/pm_backup.db
```

**Linux wrapper**:
```bash
./backup_db_snapshot.sh
```

### Restore

**UI Restore**:
1. Open Ops panel
2. Enter `PM_ADMIN_TOKEN`
3. Upload `pm_backup_*.db`

**CLI Restore**:
```bash
sudo systemctl stop pilotdeck
./restore_db_snapshot.sh --from ./data/pm_backup.db --force
sudo systemctl start pilotdeck
```

### Scheduled Backups

**Setup** (systemd, opt-in):
```bash
sudo ./setup_auto_backup.sh
```

Creates:
- `pilotdeck-backup.service`
- `pilotdeck-backup.timer`
- `/etc/pilotdeck/backup.env`

**Check status**:
```bash
sudo ./setup_auto_backup.sh status
journalctl -u pilotdeck-backup.service -f
```

---

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export PM_DB_FILE=./data/pm.db
export PM_ADMIN_TOKEN="your-secret"
export PM_AGENT_TOKEN="your-secret"

# Run server
python server/main.py
```

Server starts at `http://localhost:8689`

### Testing with curl

**Login**:
```bash
curl -X POST http://localhost:8689/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}' \
  -c cookies.txt
```

**List projects** (with session):
```bash
curl http://localhost:8689/api/projects \
  -b cookies.txt
```

**Create run** (with agent token):
```bash
curl -X POST http://localhost:8689/api/agent/runs \
  -H "Content-Type: application/json" \
  -H "X-PM-Agent-Token: your-token" \
  -d '{"id": "run-123", "projectId": "proj-456", "agentId": "claude", "status": "running"}'
```

---

## Best Practices

### Concurrency Control
Always use `ifUpdatedAt` when updating projects:
```python
# Read
project = projects_store.get("proj-123")
updated_at = project["updatedAt"]

# Update
projects_store.patch(
    "proj-123",
    {"progress": 85},
    if_updated_at=updated_at
)
```

### Idempotency
Use deterministic IDs for runs/events/actions:
```python
# Safe to retry
create_run({
    "id": f"run-{session_id}-{attempt}",
    "projectId": "proj-123",
    "status": "running"
})
```

### Error Handling
```python
try:
    project_service.update_project(id, updates, if_updated_at)
except ProjectNotFoundError:
    return {"error": "Project not found"}, 404
except ProjectModifiedError:
    return {"error": "Project was modified"}, 409
except ValidationError as e:
    return {"error": str(e)}, 400
```

---

## Security Considerations

### Authentication
- Web UI: Session cookies (CSRF-safe)
- Admin: Token header (keep secret, never commit)
- Agent: Optional token header

### Database
- SQLite in WAL mode (safe for concurrent reads)
- Backup API uses consistent snapshots
- Foreign keys enabled
- Busy timeout configured

### Deployment
- Use HTTPS in production
- Set `SESSION_COOKIE_SECURE=True`
- Rotate `PM_SECRET_KEY` regularly
- Limit `PM_ADMIN_TOKEN` access

---

**Last Updated**: 2026-02-11  
**Related Documentation**:
- [Database Operations](./DATABASE.md)
- [Authentication Guide](./AUTHENTICATION.md)
- [API Reference](./API_REFERENCE.md)
- [System Architecture](../../docs/ARCHITECTURE.md)
