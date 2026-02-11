# PilotDeck Server Deployment Guide

Complete guide for deploying PilotDeck to production Linux servers.

---

## 📋 Prerequisites

### System Requirements

- **OS**: Linux (CentOS, Ubuntu, Debian, or similar)
- **Python**: 3.10+ (3.8+ supported but 3.10+ recommended)
- **Node.js**: v22.x (any minor/patch version in the 22 series)
- **Git**: For pulling updates
- **systemd**: For service management (optional, falls back to nohup)

### Required Tools

```bash
# Check prerequisites
python3 --version  # Should be 3.10+
node --version     # Should be v22.x.x
npm --version      # Should be 11.x.x (bundled with Node 22)
git --version      # Any recent version
systemctl --version  # Optional but recommended
```

---

## 🚀 Initial Server Setup

### 1. Clone Repository

```bash
cd /opt  # or your preferred directory
git clone https://github.com/YourOrg/PilotDeck.git
cd PilotDeck
```

### 2. Install Node.js v22.x

**Option A: Using nvm (Recommended)**

```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc

# Install Node.js 22.x
nvm install 22
nvm use 22
nvm alias default 22

# Verify
node -v  # Should output v22.x.x
```

**Option B: System Package (CentOS/RHEL/Alibaba Cloud Linux)**

```bash
# Add NodeSource repository
curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash -

# Install
sudo yum install -y nodejs

# Verify
node -v  # Should output v22.x.x
```

**Option C: System Package (Ubuntu/Debian)**

```bash
# Add NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -

# Install
sudo apt-get install -y nodejs

# Verify
node -v  # Should output v22.x.x
```

### 3. Configure Environment Variables

Create environment file (optional but recommended for security):

```bash
sudo mkdir -p /etc/pilotdeck
sudo nano /etc/pilotdeck/server.env
```

Add the following:

```bash
# Server Configuration
PM_PORT=8689
PM_DEBUG=0

# Database
PM_DB_FILE=/opt/PilotDeck/data/pm.db

# Security Tokens
PM_ADMIN_TOKEN=<your-secure-random-token>
PM_AGENT_TOKEN=<your-agent-api-token>

# Flask Session Secret (optional, auto-generated if not set)
PM_SECRET_KEY=<your-secret-key>
```

**Generate secure tokens:**

```bash
# Generate random tokens (Linux/Mac)
openssl rand -hex 32  # Use for PM_ADMIN_TOKEN
openssl rand -hex 32  # Use for PM_AGENT_TOKEN
openssl rand -hex 32  # Use for PM_SECRET_KEY
```

**Important**: Keep these tokens secret! Never commit them to git.

### 4. Initial Deployment

Run the deployment script:

```bash
sudo ./deploy_pull_restart.sh
```

This script will:
1. ✅ Verify Python 3.8+ and Node.js v22.x
2. ✅ Pull latest code from git
3. ✅ Create Python virtual environment (`.venv`)
4. ✅ Install Python dependencies
5. ✅ Build frontend (`npm ci && npm run build`)
6. ✅ Create systemd service (`/etc/systemd/system/pilotdeck.service`)
7. ✅ Start the service

---

## 🔧 Systemd Service Configuration

### Service File Location

```
/etc/systemd/system/pilotdeck.service
```

### Default Service Configuration

The `deploy_pull_restart.sh` script automatically creates this service file:

```ini
[Unit]
Description=PilotDeck (Flask)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/PilotDeck
Environment=PM_PORT=8689
Environment=PM_DEBUG=0
ExecStart=/opt/PilotDeck/.venv/bin/python /opt/PilotDeck/server/main.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

### Using Environment File (Recommended)

For better security, modify the service to use an environment file:

```bash
sudo nano /etc/systemd/system/pilotdeck.service
```

Change to:

```ini
[Unit]
Description=PilotDeck (Flask)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/PilotDeck
EnvironmentFile=-/etc/pilotdeck/server.env
ExecStart=/opt/PilotDeck/.venv/bin/python /opt/PilotDeck/server/main.py
Restart=always
RestartSec=2

# Security hardening (optional)
User=pilotdeck
Group=pilotdeck
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/PilotDeck/data

[Install]
WantedBy=multi-user.target
```

**Note**: If using `User=pilotdeck`, create the user first and set permissions:

```bash
sudo useradd -r -s /bin/false pilotdeck
sudo chown -R pilotdeck:pilotdeck /opt/PilotDeck
```

### Reload Service After Changes

```bash
sudo systemctl daemon-reload
sudo systemctl restart pilotdeck
```

---

## 📦 Routine Updates

### Quick Update

```bash
sudo ./deploy_pull_restart.sh
```

This is the **recommended** way to update. It handles everything automatically.

### Manual Update Process

If you need more control:

```bash
# 1. Stop service
sudo systemctl stop pilotdeck

# 2. Pull latest code
git fetch --all --prune
git pull --rebase

# 3. Update backend dependencies
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Build frontend
cd frontend
npm ci
npm run build
cd ..

# 5. Start service
sudo systemctl start pilotdeck
```

---

## 🔒 Configuration Management

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PM_PORT` | No | `8689` | Server port |
| `PM_DEBUG` | No | `0` | Debug mode (0=off, 1=on) |
| `PM_DB_FILE` | No | `data/pm.db` | SQLite database path |
| `PM_ADMIN_TOKEN` | **Yes*** | _(none)_ | Admin API token |
| `PM_AGENT_TOKEN` | No | _(none)_ | Agent API token (if not set, agent endpoints are open) |
| `PM_SECRET_KEY` | No | _(auto)_ | Flask session secret (auto-generated if not provided) |

**\*PM_ADMIN_TOKEN** is required for:
- Database backup/restore operations
- Remote deployment triggers via Web UI
- Admin API endpoints

### Modifying Configuration

**Method 1: Edit Environment File (Recommended)**

```bash
sudo nano /etc/pilotdeck/server.env
# Edit values
sudo systemctl restart pilotdeck
```

**Method 2: Edit Service File Directly**

```bash
sudo nano /etc/systemd/system/pilotdeck.service
# Edit Environment= lines
sudo systemctl daemon-reload
sudo systemctl restart pilotdeck
```

**Method 3: Temporary Override (Testing)**

```bash
sudo systemctl stop pilotdeck
export PM_DEBUG=1
.venv/bin/python server/main.py
```

---

## 🗄️ Database Backup (Automated)

### Setup Daily Auto-Backup

Install systemd timer for daily snapshots at midnight:

```bash
sudo ./setup_auto_backup.sh
```

This installs:
- **Service**: `/etc/systemd/system/pilotdeck-backup.service`
- **Timer**: `/etc/systemd/system/pilotdeck-backup.timer`
- **Config**: `/etc/pilotdeck/backup.env` (optional)

### Backup Configuration

Edit backup settings:

```bash
sudo nano /etc/pilotdeck/backup.env
```

Available options:

```bash
# Local paths (optional overrides)
PM_DB_FILE=/opt/PilotDeck/data/pm.db
PM_BACKUP_FILE=/opt/PilotDeck/data/pm_backup.db

# Optional cloud upload
PM_BACKUP_UPLOAD_URL=https://your-bucket.s3.amazonaws.com/backups/pm_backup.db?signature=...
PM_BACKUP_UPLOAD_TOKEN=your-bearer-token
PM_BACKUP_UPLOAD_METHOD=PUT
```

### Backup Management Commands

```bash
# Check backup timer status
sudo ./setup_auto_backup.sh status

# View recent backup logs
sudo journalctl -u pilotdeck-backup.service -n 50

# Disable auto-backup (keeps service, stops timer)
sudo ./setup_auto_backup.sh disable

# Re-enable auto-backup
sudo ./setup_auto_backup.sh install

# Completely remove auto-backup
sudo ./setup_auto_backup.sh remove

# Manual backup (run immediately)
sudo systemctl start pilotdeck-backup.service
```

### Manual Backup

```bash
# Local snapshot
./backup_db_snapshot.sh

# Output: data/pm_backup.db
```

---

## 🔄 Database Restore

### Restore from Backup

```bash
# Stop service
sudo systemctl stop pilotdeck

# Restore (creates rollback: data/pm.db.bak.<timestamp>)
./restore_db_snapshot.sh --from ./data/pm_backup.db --force

# Start service
sudo systemctl start pilotdeck
```

### Restore via Web UI

1. Open PilotDeck Web UI
2. Navigate to **Ops** panel
3. Enter `PM_ADMIN_TOKEN`
4. Click **"Restore from backup"**
5. Upload `pm_backup_*.db` file

The server handles the restore atomically and creates a rollback backup automatically.

---

## 🌐 Reverse Proxy (Nginx)

### Basic Nginx Configuration

```nginx
server {
    listen 80;
    server_name pilotdeck.example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name pilotdeck.example.com;

    ssl_certificate /etc/ssl/certs/pilotdeck.crt;
    ssl_certificate_key /etc/ssl/private/pilotdeck.key;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy to PilotDeck
    location / {
        proxy_pass http://127.0.0.1:8689;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Static assets caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://127.0.0.1:8689;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Enable HTTPS Session Cookies

When using HTTPS, update the service environment:

```bash
sudo nano /etc/pilotdeck/server.env
```

Add:

```bash
SESSION_COOKIE_SECURE=True
```

Then restart:

```bash
sudo systemctl restart pilotdeck
```

---

## 🐳 Docker Deployment (Future)

Docker support is planned but not yet implemented. See [Issue #XX](#) for progress.

---

## 📊 Monitoring & Logs

### Service Status

```bash
# Check service status
sudo systemctl status pilotdeck

# View recent logs (last 50 lines)
sudo journalctl -u pilotdeck.service -n 50

# Follow logs in real-time
sudo journalctl -u pilotdeck.service -f

# View logs since boot
sudo journalctl -u pilotdeck.service -b
```

### Application Logs

PilotDeck logs to **stdout/stderr**, captured by systemd journal.

For additional logging, check:
- Deploy logs: `deploy_run.log`
- Deploy state: `deploy_state.json`

### Health Check

```bash
# Quick health check
curl -s http://localhost:8689/api/health

# Expected output:
# {"status":"healthy","success":true,"timestamp":"..."}
```

### Database Status

```bash
# Check database file
ls -lh data/pm.db*

# SQLite WAL mode files (normal)
# pm.db         - Main database
# pm.db-wal     - Write-ahead log
# pm.db-shm     - Shared memory

# Check database integrity
sqlite3 data/pm.db "PRAGMA integrity_check;"
```

---

## 🛠️ Troubleshooting

### Service Won't Start

**Check logs:**

```bash
sudo journalctl -u pilotdeck.service -n 100 --no-pager
```

**Common issues:**

1. **Port already in use:**
   ```bash
   # Check what's using port 8689
   sudo netstat -tlnp | grep 8689
   # or
   sudo lsof -i :8689
   ```

2. **Missing dependencies:**
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Database locked:**
   ```bash
   # Check for multiple instances
   ps aux | grep "server/main.py"
   # Kill duplicates if found
   ```

### Deploy Script Fails

**Node.js version mismatch:**

```bash
# Install correct version
nvm install 22
nvm use 22
nvm alias default 22
```

**Frontend build fails:**

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

**Git conflicts:**

```bash
# View conflicts
git status

# Reset to remote (WARNING: loses local changes)
git fetch --all
git reset --hard origin/main
```

### Database Issues

**Database is locked:**

```bash
# Check for multiple server instances
ps aux | grep "python.*server/main.py"
# Kill extra instances

# Check for backup process
ps aux | grep "backup_db_snapshot"

# Wait and retry
```

**Restore failed:**

```bash
# Check backup file integrity
sqlite3 data/pm_backup.db "PRAGMA integrity_check;"

# Manual restore
sudo systemctl stop pilotdeck
cp data/pm.db data/pm.db.manual_backup
cp data/pm_backup.db data/pm.db
sudo systemctl start pilotdeck
```

### Performance Issues

**Too many WAL checkpoints:**

```bash
# Check WAL file size
ls -lh data/pm.db-wal

# If > 100MB, checkpoint manually
sqlite3 data/pm.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

**Database growing large:**

```bash
# Check size
du -sh data/pm.db

# Vacuum (requires downtime)
sudo systemctl stop pilotdeck
sqlite3 data/pm.db "VACUUM;"
sudo systemctl start pilotdeck
```

---

## 🔐 Security Best Practices

### Firewall Configuration

```bash
# Allow only HTTP/HTTPS (if using Nginx)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# Or allow port 8689 directly
sudo firewall-cmd --permanent --add-port=8689/tcp
sudo firewall-cmd --reload
```

### Token Security

- ✅ **Generate strong random tokens** (32+ characters)
- ✅ **Store in environment files**, not in code
- ✅ **Restrict file permissions**: `chmod 600 /etc/pilotdeck/*.env`
- ✅ **Rotate tokens periodically**
- ✅ **Use HTTPS in production** (`SESSION_COOKIE_SECURE=True`)

### File Permissions

```bash
# Recommended permissions
sudo chown -R pilotdeck:pilotdeck /opt/PilotDeck
sudo chmod 755 /opt/PilotDeck
sudo chmod 700 /opt/PilotDeck/data
sudo chmod 600 /etc/pilotdeck/*.env
```

---

## 📚 Related Documentation

- **[Architecture Overview](../../docs/ARCHITECTURE.md)** - System design and data flow
- **[Database Operations](./DATABASE.md)** - Detailed backup/restore procedures
- **[API Reference](./API_REFERENCE.md)** - REST API endpoints
- **[Node.js Version Guide](../../NODE_VERSION.md)** - Node version requirements

---

## 🆘 Getting Help

- **GitHub Issues**: Report bugs or request features
- **Logs**: Always check `journalctl -u pilotdeck.service -n 100`
- **Health Check**: `curl http://localhost:8689/api/health`

---

**Last Updated**: 2026-02-11  
**Maintained By**: PilotDeck Team
