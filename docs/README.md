# PilotDeck Documentation

Welcome to PilotDeck documentation! This index helps you quickly find the right documentation for your needs.

---

## 🎯 Choose Your Path

### 👨‍💻 I'm a Developer Starting a New Session
**Start Here**: [ARCHITECTURE.md](./ARCHITECTURE.md)  
Quick overview of the entire codebase, technology stack, and design decisions.

### 🎨 I'm Working on the Frontend
**Start Here**: [frontend/docs/README.md](../frontend/docs/README.md)  
Vue 3 component library, frontend architecture, and development workflow.

### ⚙️ I'm Working on the Backend
**Start Here**: [server/docs/README.md](../server/docs/README.md)  
Flask API, SQLite storage, and backend architecture.

### 🔌 I'm Integrating an Agent
**Start Here**: [agent/AGENT_API.md](./agent/AGENT_API.md)  
Complete guide to integrating your agent with PilotDeck's API.

### 📡 I Need API Documentation
**Start Here**: [server/docs/API_REFERENCE.md](../server/docs/API_REFERENCE.md)  
Quick reference for all REST API endpoints with curl examples.

### 🔧 I'm Managing Operations
**Start Here**: [server/docs/DEPLOYMENT.md](../server/docs/DEPLOYMENT.md)  
Production deployment, systemd configuration, backups, and troubleshooting.

### 🗄️ I Need Database Operations
**Start Here**: [server/docs/DATABASE.md](../server/docs/DATABASE.md)  
Backup, restore, migration, and database procedures.

---

## 📚 Complete Documentation List

### Core Technical Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Complete system architecture | All developers |
| [ARCHITECTURE.zh-CN.md](./ARCHITECTURE.zh-CN.md) | 完整系统架构（中文） | 中文开发者 |
| [Frontend Guide](../frontend/docs/README.md) | Frontend developer portal | Frontend developers |
| [Backend Guide](../server/docs/README.md) | Backend developer portal | Backend developers |

### Frontend Details

| Document | Purpose | Audience |
|----------|---------|----------|
| [Frontend Architecture](../frontend/docs/ARCHITECTURE.md) | Vue 3 architecture details | Frontend developers |
| [Components Guide](../frontend/docs/COMPONENTS.md) | UI component library | Frontend developers |

### Backend Details

| Document | Purpose | Audience |
|----------|---------|----------|
| [Backend Architecture](../server/docs/ARCHITECTURE.md) | Flask architecture details | Backend developers |
| [API Reference](../server/docs/API_REFERENCE.md) | REST API quick reference | All developers |
| [Deployment Guide](../server/docs/DEPLOYMENT.md) | Production deployment | DevOps/SysAdmin |
| [Database Ops](../server/docs/DATABASE.md) | DB schema & operations | Backend/DevOps |
| [Authentication](../server/docs/AUTHENTICATION.md) | Auth system details | Backend developers |

### Agent Integration

| Document | Purpose | Audience |
|----------|---------|----------|
| [AGENT_API.md](./agent/AGENT_API.md) | Agent integration guide (EN) | Agent developers |
| [AGENT_API.zh-CN.md](./agent/AGENT_API.zh-CN.md) | Agent 集成指南（中文） | Agent 开发者 |
| [PILOTDECK_SKILL.md](./agent/PILOTDECK_SKILL.md) | OhMyOpenCode Skill guide (EN) | OhMyOpenCode users |
| [PILOTDECK_SKILL.zh-CN.md](./agent/PILOTDECK_SKILL.zh-CN.md) | OhMyOpenCode Skill 指南（中文） | OhMyOpenCode 用户 |

### Templates & Examples

| Document | Purpose | Audience |
|----------|---------|----------|
| [PROJECT_STATUS_TEMPLATE.md](./product/PROJECT_STATUS_TEMPLATE.md) | Agent sync template (EN) | Agent developers |
| [PROJECT_STATUS_TEMPLATE.zh-CN.md](./product/PROJECT_STATUS_TEMPLATE.zh-CN.md) | Agent 同步模板（中文） | Agent 开发者 |

---

## 🆕 What's New

### 2026-02-11: Production Deployment Guide
- **New Documentation**: Complete `DEPLOYMENT.md` with systemd configuration, environment variables, backup automation, reverse proxy setup, and troubleshooting.
- **Comprehensive Coverage**: Detailed explanation of `deploy_pull_restart.sh`, service management, and security best practices.

### 2026-02-11: Documentation Refactoring
- **Separated Concerns**: Documentation is now split into `frontend/docs/` and `server/docs/` for better maintainability.
- **New Portals**: Created dedicated READMEs for frontend and backend developers.
- **Updated Structure**: Moved integration docs to `docs/agent/` and templates to `docs/product/`.

### 2026-02-11: Timeline System Launch
- **New Components**: Modern Agent timeline visualization system
- **Documentation Updates**: Added comprehensive component and architecture guides.

---

## 🔍 Quick References

### Common Tasks

**How do I...**

- **Create a new project via API?**  
  → [API_REFERENCE.md](../server/docs/API_REFERENCE.md)

- **Understand the component hierarchy?**  
  → [COMPONENTS.md](../frontend/docs/COMPONENTS.md)

- **Integrate an agent with optimistic locking?**  
  → [AGENT_API.md](./agent/AGENT_API.md)

- **Backup the database?**  
  → [DATABASE.md](../server/docs/DATABASE.md)

- **Deploy to production server?**  
  → [DEPLOYMENT.md](../server/docs/DEPLOYMENT.md)

- **Configure systemd service?**  
  → [DEPLOYMENT.md](../server/docs/DEPLOYMENT.md#systemd-service-configuration)

- **Add a new Vue component?**  
  → [COMPONENTS.md](../frontend/docs/COMPONENTS.md)

- **Understand data flow between Project/Run/Event?**  
  → [ARCHITECTURE.md](./ARCHITECTURE.md)

### Technology Stack Quick Links

- **Backend**: Flask + SQLite (WAL mode)
- **Frontend**: Vue 3 + Pinia + Vite + TypeScript
- **Styling**: CSS Variables (Design Tokens)
- **API**: RESTful with optimistic concurrency control
- **Auth**: Session cookies (UI) + Token headers (Admin/Agent)

---

## 📖 Learning Path

### For New Contributors

1. **Start**: Read [ARCHITECTURE.md](./ARCHITECTURE.md) (15 min)
2. **Frontend**: Explore [Frontend Guide](../frontend/docs/README.md) (10 min)
3. **Backend**: Explore [Backend Guide](../server/docs/README.md) (10 min)
4. **Build**: Create your first feature!

### For Agent Developers

1. **Start**: Read [AGENT_API.md](./agent/AGENT_API.md) introduction (5 min)
2. **Setup**: Configure auth tokens (2 min)
3. **Test**: Try example API calls (10 min)
4. **Integrate**: Implement agent workflow (30 min)

---

## 🤝 Contributing to Documentation

### Documentation Standards

- **Keep it concise**: Developers are busy
- **Show examples**: Code speaks louder than words
- **Stay current**: Update docs when code changes
- **Bilingual support**: Provide EN + zh-CN versions when possible

---

## 📞 Need Help?

- **Found a bug in docs?** → Open a GitHub Issue
- **Want to improve docs?** → Submit a Pull Request
- **Have questions?** → Contact the maintainers

---

**Documentation Version**: 1.1  
**Last Updated**: 2026-02-11  
**Maintained By**: PilotDeck Team
