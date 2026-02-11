# PilotDeck API Quick Reference

> **Purpose**: Fast API reference for developers integrating with PilotDeck or working in new sessions.  
> **Audience**: Backend/Integration developers, Agent clients.

For detailed Agent API guide, see [../../docs/agent/AGENT_API.md](../../docs/agent/AGENT_API.md).

---

## Base URL

**Local Development**: `http://localhost:8689`  
**Production**: Your deployed server URL

---

## Authentication

### Web UI (Session Cookie)
- `POST /api/auth/login` - Login with username/password
- `GET /api/auth/me` - Check current session
- `POST /api/auth/logout` - Logout

### Admin Operations (Token Header)
Header: `X-PM-Token: <PM_ADMIN_TOKEN>`

### Agent API (Optional Token Header)
Header: `X-PM-Agent-Token: <PM_AGENT_TOKEN>`  
If `PM_AGENT_TOKEN` is not configured, agent endpoints are open.

---

## API Endpoints Overview

| Category | Endpoint | Method | Auth |
|----------|----------|--------|------|
| **Meta** | `/api/health` | GET | None |
| **Meta** | `/api/meta` | GET | None |
| **Projects** | `/api/projects` | GET | Session |
| **Projects** | `/api/projects` | POST | Session |
| **Projects** | `/api/projects/<id>` | GET | Session |
| **Projects** | `/api/projects/<id>` | PUT/PATCH | Session |
| **Projects** | `/api/projects/<id>` | DELETE | Session |
| **Projects** | `/api/projects/reorder` | POST | Session |
| **Projects** | `/api/projects/batch` | POST | Session |
| **Stats** | `/api/stats` | GET | Session |
| **Stats** | `/api/stats/tokens` | GET | Session |
| **Agent** | `/api/agent/runs` | GET/POST | Agent Token |
| **Agent** | `/api/agent/runs/<id>` | GET/PATCH | Agent Token |
| **Agent** | `/api/agent/events` | GET/POST | Agent Token |
| **Agent** | `/api/agent/actions` | POST | Agent Token |
| **Agent Ops** | `/api/agent/profiles` | GET/POST | Session |
| **Agent Ops** | `/api/agent/capabilities` | GET/POST | Session |
| **Agent Ops** | `/api/agent/usage` | GET/POST | Agent Token |
| **Admin** | `/api/admin/backup` | GET | Admin Token |
| **Admin** | `/api/admin/restore` | POST | Admin Token |
| **Admin** | `/api/admin/deploy` | POST | Admin Token |
| **Admin** | `/api/admin/deploy/status` | GET | Admin Token |
| **Admin** | `/api/admin/deploy/log` | GET | Admin Token |

---

## Quick Examples

### 1. List All Projects

```bash
GET /api/projects
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "proj-abc123",
      "name": "My Project",
      "status": "in-progress",
      "priority": "high",
      "progress": 75,
      "budget": 10000,
      "actualCost": 7500,
      "createdAt": "2026-01-15T10:00:00Z",
      "updatedAt": "2026-02-11T14:30:00Z",
      ...
    }
  ]
}
```

### 2. Update Project with Optimistic Locking

```bash
PATCH /api/projects/proj-abc123
Content-Type: application/json

{
  "progress": 80,
  "ifUpdatedAt": "2026-02-11T14:30:00Z"
}
```

**Success**:
```json
{
  "success": true,
  "data": {
    "id": "proj-abc123",
    "progress": 80,
    "updatedAt": "2026-02-11T15:00:00Z",
    ...
  }
}
```

**Conflict** (if project was updated by someone else):
```json
{
  "success": false,
  "error": "Conflict: project was modified by another process",
  "current": { ... }
}
```

### 3. Create Agent Run (Idempotent)

```bash
POST /api/agent/runs
Content-Type: application/json
X-PM-Agent-Token: <your-token>

{
  "id": "run-xyz789",
  "projectId": "proj-abc123",
  "agentId": "claude-sonnet",
  "title": "Implement new feature",
  "status": "running"
}
```

**Response** (creates or returns existing):
```json
{
  "success": true,
  "data": {
    "id": "run-xyz789",
    "projectId": "proj-abc123",
    "status": "running",
    "createdAt": "2026-02-11T15:00:00Z",
    ...
  }
}
```

### 4. Append Agent Event

```bash
POST /api/agent/events
Content-Type: application/json
X-PM-Agent-Token: <your-token>

{
  "id": "evt-001",
  "projectId": "proj-abc123",
  "runId": "run-xyz789",
  "type": "action",
  "level": "info",
  "title": "Created new component",
  "message": "Successfully created timeline component system",
  "data": {
    "files": ["AgentTimeline.vue", "TimelineItem.vue", "DataViewer.vue"]
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": { ... }
}
```

### 5. Agent Action (Semantic Update)

```bash
POST /api/agent/actions
Content-Type: application/json
X-PM-Agent-Token: <your-token>

{
  "id": "action-001",
  "projectId": "proj-abc123",
  "runId": "run-xyz789",
  "agentId": "claude-sonnet",
  "action": "bump_progress",
  "params": {
    "delta": 10,
    "reason": "Completed timeline implementation"
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "project": {
      "id": "proj-abc123",
      "progress": 85,
      "updatedAt": "2026-02-11T15:30:00Z"
    },
    "event": {
      "id": "action-001",
      "type": "action",
      "title": "Progress updated"
    }
  }
}
```

### 6. Export Database Backup

```bash
GET /api/admin/backup
X-PM-Token: <admin-token>
```

**Response**: File download (`pm_backup_<timestamp>.db`)

### 7. Get Statistics

```bash
GET /api/stats
```

**Response**:
```json
{
  "success": true,
  "data": {
    "total": 15,
    "byStatus": {
      "planning": 3,
      "in-progress": 7,
      "completed": 5
    },
    "byPriority": {
      "high": 4,
      "medium": 8,
      "low": 3
    },
    "financial": {
      "totalCost": 125000,
      "totalRevenue": 180000,
      "netProfit": 55000
    }
  }
}
```

---

## Common Request/Response Patterns

### Success Response
```json
{
  "success": true,
  "data": { ... }
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "message": "Optional detailed message"
}
```

### Validation Error
```json
{
  "success": false,
  "error": "Validation failed",
  "details": {
    "field": "name",
    "message": "Name is required"
  }
}
```

---

## Data Types Reference

### Project
```typescript
{
  id: string                    // "proj-xxx"
  name: string
  description: string
  notes: string
  status: 'planning' | 'in-progress' | 'paused' | 'completed' | 'cancelled'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  progress: number              // 0-100
  tags: string[]
  category?: string
  budget: number
  actualCost: number
  cost: { total: number }
  revenue: { total: number }
  github?: string
  workspace?: string
  createdAt: string             // ISO 8601
  updatedAt: string             // ISO 8601
}
```

### AgentRun
```typescript
{
  id: string                    // "run-xxx"
  projectId: string | null
  agentId: string | null
  title: string | null
  summary: string | null
  status: 'running' | 'completed' | 'failed' | 'cancelled'
  createdAt: string
  updatedAt: string
  startedAt: string
  finishedAt: string | null
  links: string[]
  tags: string[]
  metrics: Record<string, any>
  meta: Record<string, any>
}
```

### AgentEvent
```typescript
{
  id: string | null
  ts: string | null             // Timestamp
  type: 'note' | 'action' | 'result' | 'error' | 'milestone'
  level: 'debug' | 'info' | 'warn' | 'error'
  projectId: string | null
  runId: string | null
  agentId: string | null
  title: string | null
  message: string | null
  data: any                     // Arbitrary JSON data
}
```

---

## Agent Actions Reference

Available actions for `/api/agent/actions`:

| Action | Params | Description |
|--------|--------|-------------|
| `set_status` | `{ status: ProjectStatus }` | Update project status |
| `set_priority` | `{ priority: ProjectPriority }` | Update project priority |
| `set_progress` | `{ progress: number }` | Set absolute progress (0-100) |
| `bump_progress` | `{ delta: number, reason?: string }` | Increment progress by delta |
| `append_note` | `{ note: string }` | Append to project notes |
| `add_tag` | `{ tag: string }` | Add tag to project |
| `remove_tag` | `{ tag: string }` | Remove tag from project |

All actions support:
- `recordOnly: boolean` - Only write event, don't update project
- Automatic event creation with action details

---

## Rate Limits & Best Practices

- **No built-in rate limits** (self-hosted)
- **Idempotency**: Use unique IDs for runs/events/actions
- **Optimistic Locking**: Always use `ifUpdatedAt` when updating projects
- **Batch Operations**: Use `/api/projects/batch` for bulk updates
- **Event Append-Only**: Events cannot be modified or deleted
- **Token Security**: Store admin/agent tokens securely, never commit to git

---

## Error Codes

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (missing/invalid auth) |
| 404 | Not Found (resource doesn't exist) |
| 409 | Conflict (optimistic lock failure) |
| 500 | Internal Server Error |

---

## Environment Variables

```bash
PM_PORT=8689                    # Server port (default: 8689)
PM_DEBUG=0                      # Debug mode (0/1)
PM_DB_FILE=data/pm.db           # SQLite database path
PM_ADMIN_TOKEN=<secret>         # Required for admin operations
PM_AGENT_TOKEN=<secret>         # Optional, for agent API
```

---

**Last Updated**: 2026-02-11  
**API Version**: 1.0

For complete Agent API documentation with workflows and examples, see [../../docs/agent/AGENT_API.md](../../docs/agent/AGENT_API.md).
