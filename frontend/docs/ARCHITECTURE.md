# PilotDeck Frontend Architecture

This document describes the frontend architecture for developers working on the Vue 3 UI.

> **For complete system architecture**, see [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)

---

## Technology Stack

- **Framework**: Vue 3 (Composition API)
- **State Management**: Pinia
- **Router**: Vue Router 5
- **Build Tool**: Vite 5
- **Language**: TypeScript
- **Styling**: CSS Variables (Design Tokens) with Dark/Light theme support

---

## Directory Structure

```
frontend/src/
├── api/
│   ├── client.ts          # API client functions
│   └── types.ts           # TypeScript type definitions (Project, AgentRun, AgentEvent, etc.)
├── components/
│   ├── timeline/          # Timeline component system (new)
│   │   ├── AgentTimeline.vue    # Main timeline container with search/filter
│   │   ├── TimelineItem.vue     # Individual timeline item (Run/Event)
│   │   └── DataViewer.vue       # Recursive JSON viewer with syntax highlighting
│   ├── ProjectCard.vue          # Project card in grid/list view
│   ├── ProjectDetailModal.vue   # Project details with tabs (details + timeline)
│   ├── ProjectFormModal.vue     # Create/Edit project form
│   ├── StatsModal.vue           # Statistics dashboard
│   ├── OpsModal.vue             # Admin operations (backup/restore/deploy)
│   ├── TheHeader.vue            # App header with theme toggle
│   ├── TheFilters.vue           # Project filters (status/priority/search)
│   └── Toast.vue                # Toast notifications
├── composables/
│   └── theme.ts           # Dark/Light theme management
├── pages/
│   ├── ProjectsPage.vue   # Main projects dashboard (authenticated)
│   └── LoginPage.vue      # Login page
├── router/
│   └── index.ts           # Vue Router configuration with auth guards
├── stores/
│   ├── projects.ts        # Projects state management (Pinia)
│   ├── agent.ts           # Agent runs/events state management (Pinia)
│   └── auth.ts            # Authentication state management (Pinia)
├── styles/
│   ├── tokens.css         # Design system tokens (colors, spacing, shadows)
│   └── base.css           # Global base styles
├── App.vue                # Root component
├── main.ts                # Application entry point
└── vite-env.d.ts          # Vite TypeScript declarations
```

---

## State Management (Pinia Stores)

### `stores/projects.ts`
- **State**: projects list, loading state, error handling
- **Getters**: filtered projects, project by ID
- **Actions**:
  - `fetchProjects()`: Load all projects
  - `createProject(data)`: Create new project
  - `updateProject(id, data)`: Update existing project
  - `deleteProject(id)`: Delete project
  - `reorderProjects(order)`: Persist manual sort order
  - `batchUpdate(updates)`: Batch update multiple projects

### `stores/agent.ts`
- **State**: runs, events, loading state, error handling
- **Getters**: 
  - `runsByProject(projectId)`: Filter runs by project
  - `eventsByProject(projectId)`: Filter events by project
  - `eventsByRun(runId)`: Filter events by run
  - `runById(runId)`: Get run by ID
- **Actions**:
  - `fetchRuns(projectId?)`: Load agent runs
  - `fetchEvents(projectId?, runId?)`: Load agent events
  - `fetchProjectTimeline(projectId)`: Load both runs and events for a project

### `stores/auth.ts`
- **State**: user, isAuthenticated, isLoading
- **Actions**:
  - `login(username, password)`: Authenticate user
  - `logout()`: Clear session
  - `setUser(user)`: Update user state
  - `setLoading(loading)`: Update loading state

---

## Routing & Navigation

**Routes**:
- `/` (ProjectsPage) - Requires authentication
- `/login` (LoginPage) - Public route
  
**Navigation Guards**:
- Auto-redirect to `/login` if unauthenticated
- Auto-redirect to `/` if authenticated user visits `/login`
- Server auth check on first load

---

## Component Architecture

### Timeline Component System

**Design Philosophy**: Modern, user-friendly Agent activity visualization

#### 1. AgentTimeline.vue (Container)
- Merges AgentRun and AgentEvent data
- Sorts chronologically (newest first)
- **Features**:
  - Real-time search (title/summary/agentId)
  - Type filter (All/Runs/Events)
  - Level filter (Info/Warn/Error)
  - Pagination (50 items per load)
  - Loading/Empty states

#### 2. TimelineItem.vue (Item Renderer)
- Unified component for both Run and Event types
- **Run Display**:
  - Status badge (running/completed/failed/cancelled)
  - Agent ID, duration, timestamps
  - Expandable metrics (DataViewer)
  - Links and tags
- **Event Display**:
  - Level indicator (debug/info/warn/error) with color coding
  - Type badge (note/action/result/error/milestone)
  - Expandable data (DataViewer)
- **Interactions**:
  - Click to expand/collapse details
  - Copy JSON button
  - Smooth animations (0.2-0.3s ease-in-out)

#### 3. DataViewer.vue (JSON Viewer)
- Recursive tree-view for any JSON data
- **Features**:
  - Syntax highlighting (strings, numbers, booleans, null)
  - Collapsible objects/arrays
  - Long string truncation with expand
  - Copy entire JSON or individual values
  - Recursion depth limit (max 3 levels)
  - Null/undefined/empty value handling

### Other Key Components

- **ProjectCard.vue**: Displays project summary with status, priority, progress, cost/revenue
- **ProjectDetailModal.vue**: Tabbed modal (Details + Agent Timeline)
- **ProjectFormModal.vue**: Form for creating/editing projects with validation
- **TheHeader.vue**: App-wide header with theme toggle, ops button, user menu
- **TheFilters.vue**: Filter projects by status, priority, category, search query

**For detailed component documentation**, see [COMPONENTS.md](./COMPONENTS.md)

---

## Design System

### CSS Tokens (`styles/tokens.css`)

#### Light Theme
- Background: `#f6f7f9` (gradient overlay)
- Card: `#ffffff` with subtle shadow
- Primary: `#111827` (monochrome)
- Text: `#0f172a` (primary), `#334155` (secondary)

#### Dark Theme (`[data-theme='dark']`)
- Background: `#080b12` (deep space gradient)
- Card: `rgba(17, 24, 39, 0.92)` with backdrop blur
- Primary: `#e2e8f0`
- Text: `#f8fafc` (primary), `#cbd5e1` (secondary)

#### Semantic Colors
- **Status badges**: planning (blue), in-progress (orange), paused (gray), completed (green), cancelled (red)
- **Priority badges**: low (gray), medium (blue), high (orange), urgent (red)
- Both themes have corresponding color variants

#### Effects
- Border radius: `16px` (large), `8px` (small)
- Shadows: `--shadow-sm`, `--shadow-md`, `--shadow-lg`
- Backdrop blur: `blur(12px)`

---

## Build & Development

**Development**:
```bash
npm run dev  # Vite dev server at http://localhost:5173
```

**Build**:
```bash
npm run build  # TypeScript check + Vite build to dist/
```

**Preview**:
```bash
npm run preview  # Preview production build
```

Build output is served by Flask at `/` when `frontend/dist/` exists.

---

## API Integration

Frontend communicates with backend via `src/api/client.ts`:
- Base URL: `/api`
- Session-based auth (cookies)
- TypeScript types in `src/api/types.ts`
- Error handling with toast notifications

**For complete API documentation**, see [../../server/docs/API_REFERENCE.md](../../server/docs/API_REFERENCE.md)

---

## Best Practices

### TypeScript Types
Always import types from `@/api/types.ts`:
```typescript
import type { Project, AgentRun, AgentEvent } from '@/api/types'
```

### Prop Validation
Use TypeScript interfaces for props:
```typescript
interface Props {
  required: string
  optional?: number
}

const props = withDefaults(defineProps<Props>(), {
  optional: 0
})
```

### CSS Variables
Use design tokens from `tokens.css`:
```css
.my-component {
  background: var(--card-bg);
  color: var(--text-primary);
  border-radius: var(--border-radius-sm);
  box-shadow: var(--shadow-md);
}
```

### Theme Support
Components automatically support dark/light themes via CSS variables. No JavaScript theme logic needed in components (handled by `[data-theme]` attribute on root).

---

**Last Updated**: 2026-02-11  
**Related Documentation**:
- [Component Reference](./COMPONENTS.md)
- [System Architecture](../../docs/ARCHITECTURE.md)
- [API Reference](../../server/docs/API_REFERENCE.md)
