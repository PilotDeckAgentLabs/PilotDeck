# 登录功能测试指南

## 功能概述

已为 PilotDeck 项目添加了完整的登录认证功能。系统默认只有一个 admin 账户。

## 默认账户信息

- **用户名**: `admin`
- **密码**: `admin`

## 实现内容

### 后端 (Flask + SQLite)

1. **数据库 Migration** (`server/mypm/storage/sqlite_db.py`)
   - 添加了 `users` 表
   - 自动创建默认 admin 用户（用户名: admin, 密码: admin）

2. **认证 API** (`server/mypm/api/auth.py`)
   - `POST /api/auth/login` - 用户登录
   - `GET /api/auth/me` - 获取当前登录用户信息
   - `POST /api/auth/logout` - 退出登录

3. **认证中间件** (`server/mypm/domain/auth.py`)
   - `require_login` 装饰器 - 保护需要登录的路由
   - 基于 Flask session 的会话管理

4. **Session 配置** (`server/mypm/app.py`)
   - 配置了 Flask session
   - 启用了 CORS 支持（支持 credentials）
   - 注册了认证蓝图

5. **路由保护** (`server/mypm/api/projects.py`)
   - 所有 projects API 都添加了 `@require_login` 装饰器

### 前端 (Vue 3 + TypeScript)

1. **认证状态管理** (`frontend/src/stores/auth.ts`)
   - Pinia store 管理用户登录状态
   - 保存当前登录用户信息

2. **登录页面** (`frontend/src/pages/LoginPage.vue`)
   - 美观的登录界面
   - 表单验证
   - 错误提示
   - 加载状态

3. **API 客户端** (`frontend/src/api/client.ts`)
   - `login()` - 登录
   - `checkAuth()` - 检查登录状态
   - `logout()` - 退出登录
   - 所有请求自动携带 cookies (credentials: 'include')

4. **路由守卫** (`frontend/src/router/index.ts`)
   - 未登录用户自动跳转到登录页
   - 已登录用户访问登录页自动跳转到首页
   - 页面刷新时自动检查登录状态

5. **Header 组件** (`frontend/src/components/TheHeader.vue`)
   - 显示当前登录用户名
   - 退出登录按钮

## 测试步骤

### 1. 启动后端

```bash
python server/main.py
```

后端会自动运行 migration，创建 users 表和默认 admin 账户。

### 2. 构建前端

```bash
cd frontend
npm run build
```

### 3. 访问应用

打开浏览器访问: `http://localhost:8689/`

### 4. 测试登录流程

1. **首次访问** - 应该自动跳转到 `/login` 登录页面
2. **输入凭据**:
   - 用户名: `admin`
   - 密码: `admin`
3. **点击登录** - 成功后应该跳转到项目列表页面
4. **查看 Header** - 应该显示用户名 "admin" 和退出按钮
5. **刷新页面** - 应该保持登录状态（不会跳转到登录页）
6. **点击退出** - 应该退出登录并跳转回登录页面

### 5. 测试路由保护

1. **未登录访问首页** - 应该自动跳转到登录页
2. **登录后访问首页** - 应该正常显示项目列表
3. **登录后访问 /login** - 应该自动跳转到首页

### 6. 测试 API 保护

未登录时，所有需要认证的 API 请求应该返回 401 错误。

## 注意事项

### 密码哈希

目前使用 SHA256 哈希存储密码。在生产环境中，建议升级为 bcrypt 或其他更安全的密码哈希算法。

### Session 配置

- `SESSION_COOKIE_SECURE` 当前设置为 `False`，在生产环境部署时应该设置为 `True` 并使用 HTTPS
- `PM_SECRET_KEY` 环境变量可以设置自定义的 session 密钥，否则系统会自动生成

### CORS 配置

前端和后端如果部署在不同域名，需要在 `CORS()` 配置中指定允许的源。

## 可能遇到的问题

### 1. Session 不持久

确保：
- 前端 API 请求配置了 `credentials: 'include'`
- CORS 配置允许 credentials

### 2. 数据库未初始化

如果 migration 没有运行，手动删除 `data/pm.db` 文件，重启后端会自动重建数据库。

### 3. 前端路由守卫不生效

确保前端已重新构建：`npm run build`

## 后续优化建议

1. **密码强度要求** - 添加密码复杂度验证
2. **记住我功能** - 添加持久化登录选项
3. **密码重置** - 添加忘记密码功能
4. **多用户支持** - 如果需要多用户，可以添加用户管理界面
5. **会话超时** - 配置更合理的会话过期时间
6. **日志审计** - 记录登录/登出日志
