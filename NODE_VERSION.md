# Node.js Version Management

## Required Version

This project requires **Node.js v22.x** (any minor/patch version in the 22 series).

- `.nvmrc` specifies the major version: `22`
- `package.json` enforces version range: `>=22.0.0 <23.0.0`
- Deploy script validates major version match only

### Why Major Version Only?

**Stability with Flexibility:**
- **API stability**: Node.js 22.x won't have breaking changes (LTS guarantee)
- **Auto security updates**: `nvm install 22` gets latest 22.x with security patches
- **Simpler ops**: Dev (22.14.0), server (22.22.0) both work fine
- **Lockfile compatibility**: npm 11.x (bundled with all Node 22.x) uses same resolution logic

**When to Pin Exact Version:**
If you experience `package-lock.json` conflicts between environments despite matching major versions, pin to exact version in `.nvmrc` (e.g., `22.14.0`).

## Setup

### Development Environment

#### Using nvm (Recommended)

```bash
# Install nvm if not already installed
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# Install latest from 22.x series
nvm install 22
nvm use 22

# Set as default
nvm alias default 22
```

#### Manual Installation

Download any Node.js v22.x version from [nodejs.org](https://nodejs.org/)

### Production/Server Environment

#### Option 1: Using nvm

```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc

# Install latest 22.x
nvm install 22
nvm use 22
nvm alias default 22
```

#### Option 2: System Package (CentOS/RHEL)

```bash
# Add NodeSource repository (Node 22.x - always gets latest 22.x)
curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash -

# Install
sudo yum install -y nodejs

# Verify version is 22.x
node -v  # Should output v22.x.x
```

#### Option 3: Docker (Future)

```dockerfile
FROM node:22-alpine  # Always pulls latest 22.x
# ... rest of Dockerfile
```

## Version Verification

The deploy script automatically verifies the Node.js **major version**:

```bash
./deploy_pull_restart.sh
# Will succeed as long as Node is v22.x.x (any minor/patch)
# Example output: ✓ Node.js major version verified: v22.x (v22.22.0)
```

## Why Version Lock?

- **Consistency**: Identical builds across dev/staging/production
- **No `package-lock.json` conflicts**: Same npm version = same lock file
- **Reproducibility**: Anyone can get exact same dependencies
- **Security**: Prevents unexpected dependency updates

## Troubleshooting

### "Node.js major version mismatch" error

```bash
# Quick fix - install any 22.x version
nvm install 22
nvm use 22
```

### `package-lock.json` modified after `npm ci`

**This should be rare with major version matching.** If it happens:

1. Check versions across environments:
   ```bash
   node -v  # Should be v22.x.x
   npm -v   # Should be 11.x.x
   ```

2. If same major version but lockfile still changes:
   - Different npm patch versions (11.0 vs 11.2) can have subtle differences
   - **Solution**: Pin exact Node version in `.nvmrc` (e.g., `22.14.0`)
   - Rebuild lockfile: `rm -rf node_modules package-lock.json && npm install`

3. If different major versions:
   - Update server to match dev environment's major version
   - Run deploy again
