# PilotDeck Backend Documentation

Welcome to the PilotDeck backend developer guide! This directory contains technical documentation for the Flask-based server and SQLite database.

## 🚀 Technology Stack

- **Framework**: Flask 3.x
- **Database**: SQLite 3 (WAL mode)
- **Language**: Python 3.10+
- **Auth**: Session-based (Web) & Token-based (Admin/Agent)

## 📖 Documentation Index

- **[ARCHITECTURE.md](./ARCHITECTURE.md)**: Backend architecture, directory structure, and service layers.
- **[API_REFERENCE.md](./API_REFERENCE.md)**: REST API quick reference with curl examples.
- **[DATABASE.md](./DATABASE.md)**: Database schema, migrations, and operations (formerly DB_OPS.md).
- **[AUTHENTICATION.md](./AUTHENTICATION.md)**: Detailed explanation of the authentication system (formerly LOGIN_FEATURE.md).
- **[DEPLOYMENT.md](./DEPLOYMENT.md)**: Complete production deployment guide with systemd, backups, and troubleshooting.

## 🛠 Common Tasks

### How do I add a new API endpoint?
1. Define the route in the appropriate blueprint in `server/mypm/api/`.
2. Implement business logic in `server/mypm/services/`.
3. Add data normalization/validation in `server/mypm/domain/models.py`.
4. Update [API_REFERENCE.md](./API_REFERENCE.md) with the new endpoint.

### How do I modify the database schema?
1. Update `server/mypm/storage/sqlite_db.py` with the new schema.
2. Increment `PRAGMA user_version` and add a migration step.
3. Update [DATABASE.md](./DATABASE.md) to reflect the changes.

### How do I run background tasks?
- Use the `deploy_service.py` pattern for long-running jobs.
- Ensure proper logging to `data/`.

## 💻 Development Workflow

### Setup
```bash
python -m pip install -r requirements.txt
```

### Development
```bash
python server/main.py
```
The server runs at `http://localhost:8689`.

### Environment Variables
- `PM_PORT`: Server port (default 8689)
- `PM_DB_FILE`: SQLite file path
- `PM_ADMIN_TOKEN`: Admin operations token
- `PM_AGENT_TOKEN`: Agent API token

---
**Last Updated**: 2026-02-11
