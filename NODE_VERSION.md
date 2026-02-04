# Node.js Version Management

## Required Version

This project requires **Node.js v22.14.0** across all environments.

- `.nvmrc` specifies the exact version
- `package.json` enforces engine requirements
- Deploy script validates version before build

## Setup

### Development Environment

#### Using nvm (Recommended)

```bash
# Install nvm if not already installed
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# Install and use the required version
nvm install
nvm use

# Set as default
nvm alias default $(cat .nvmrc)
```

#### Manual Installation

Download Node.js v20.18.1 from [nodejs.org](https://nodejs.org/)

### Production/Server Environment

#### Option 1: Using nvm

```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc

# Install required version
nvm install v22.14.0
nvm use v22.14.0
nvm alias default v22.14.0
```

#### Option 2: System Package (CentOS/RHEL)

```bash
# Add NodeSource repository (Node 22.x)
curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash -

# Install specific version
sudo yum install -y nodejs
```

#### Option 3: Docker (Future)

```dockerfile
FROM node:22.14.0-alpine
# ... rest of Dockerfile
```

## Version Verification

The deploy script automatically verifies the Node.js version:

```bash
./deploy_pull_restart.sh
# Will fail with clear error if version doesn't match .nvmrc
```

## Why Version Lock?

- **Consistency**: Identical builds across dev/staging/production
- **No `package-lock.json` conflicts**: Same npm version = same lock file
- **Reproducibility**: Anyone can get exact same dependencies
- **Security**: Prevents unexpected dependency updates

## Troubleshooting

### "Node.js version mismatch" error

```bash
# Quick fix
nvm install $(cat .nvmrc)
nvm use $(cat .nvmrc)
```

### `package-lock.json` modified after `npm ci`

This should NOT happen if Node.js versions match. If it does:

1. Verify version: `node -v` should output exactly `v22.14.0`
2. Check npm version: `npm -v` should be `11.x.x`
3. If mismatch persists, check for mixed nvm/system Node installations
