# PilotDeck Frontend Components

This document provides a comprehensive guide to all Vue 3 components in the PilotDeck frontend.

> **Audience**: Developers working on the frontend or integrating new features.

---

## Table of Contents

- [Component Overview](#component-overview)
- [Timeline Components](#timeline-components)
- [Project Components](#project-components)
- [Layout Components](#layout-components)
- [Utility Components](#utility-components)
- [Usage Examples](#usage-examples)

---

## Component Overview

### Component Hierarchy

```
App.vue
└── TheHeader.vue
└── Router View
    ├── LoginPage.vue
    └── ProjectsPage.vue
        ├── TheFilters.vue
        ├── ProjectCard.vue (multiple)
        ├── ProjectDetailModal.vue
        │   ├── AgentTimeline.vue
        │   │   └── TimelineItem.vue (multiple)
        │   │       └── DataViewer.vue (recursive)
        ├── ProjectFormModal.vue
        ├── StatsModal.vue
        ├── OpsModal.vue
        └── Toast.vue
```

---

## Timeline Components

### 🔷 AgentTimeline.vue

**Purpose**: Main container for displaying Agent runs and events in chronological order.

**Props**:
```typescript
interface Props {
  runs: AgentRun[]        // Array of agent runs
  events: AgentEvent[]    // Array of agent events
  loading?: boolean       // Loading state (default: false)
}
```

**Features**:
- Merges and sorts runs + events by timestamp (newest first)
- Search bar: searches title, summary, agent ID, status
- Type filter: All / Runs / Events
- Level filter: All / Info+ / Warn+ / Error Only
- Pagination: shows 50 items, "Load More" button for remaining
- Empty state, loading spinner

**Example**:
```vue
<AgentTimeline 
  :runs="agentStore.runs" 
  :events="agentStore.events" 
  :loading="loadingTimeline"
/>
```

**Internal State**:
- `searchQuery`: Search input text
- `filterType`: 'all' | 'run' | 'event'
- `filterLevel`: 'all' | 'info' | 'warn' | 'error'
- `displayLimit`: Number of items to show (increments by 50)

**Computed**:
- `mergedTimeline`: Combined & sorted timeline
- `filteredTimeline`: After applying search & filters
- `visibleTimeline`: First N items based on displayLimit
- `hasMore`: Whether more items exist
- `remainingCount`: Number of hidden items

---

### 🔷 TimelineItem.vue

**Purpose**: Displays a single timeline item (Agent Run or Event) with expandable details.

**Props**:
```typescript
interface Props {
  item: TimelineItemData  // Run or Event data
  initiallyExpanded?: boolean  // Default expansion state (default: false)
}
```

**Item Types**:

#### Agent Run
- Status badge (running/completed/failed/cancelled)
- Agent ID
- Duration (calculated from startedAt/finishedAt)
- Summary text
- Expandable metrics (DataViewer)
- Links (if any)

#### Agent Event
- Level badge (debug/info/warn/error) with color coding
- Type badge (note/action/result/error/milestone)
- Title and message
- Expandable data (DataViewer)

**Features**:
- Click header to toggle expansion
- Copy JSON button (copies entire item as JSON)
- Smooth expand/collapse animation
- Marker icon (R for Run, E for Event)

**Example**:
```vue
<TimelineItem
  :item="timelineItem"
  :initially-expanded="false"
/>
```

**Internal State**:
- `isExpanded`: Expansion toggle state

**Computed**:
- `isRun`: Whether item is an AgentRun
- `statusClass`: CSS class based on status/level
- `typeLabel`: Human-readable type label
- `itemTitle`: Derived from title/summary
- `formattedTime`: Formatted timestamp
- `duration`: Duration string (for runs)

---

### 🔷 DataViewer.vue

**Purpose**: Recursive JSON data viewer with syntax highlighting and smart formatting.

**Props**:
```typescript
interface Props {
  data: any           // JSON data to display
  label?: string      // Optional key label
  depth?: number      // Current recursion depth (default: 0)
  maxDepth?: number   // Maximum recursion depth (default: 3)
  showCopy?: boolean  // Show copy button at root (default: true)
}
```

**Features**:
- **Primitive Types**:
  - String: Green with quotes, truncated if > 100 chars (expandable)
  - Number: Blue
  - Boolean: Purple (true/false)
  - Null/Undefined: Gray italic
  
- **Complex Types**:
  - Object: `{ key: value }` with expand/collapse
  - Array: `[items]` with expand/collapse
  - Collapsed preview shows first few keys/items
  - Item count badge

- **Interactions**:
  - Click primitive value to copy
  - Click header to toggle expand/collapse
  - Copy JSON button at root level
  - Recursion depth limit prevents performance issues

**Example**:
```vue
<DataViewer 
  :data="{ foo: 'bar', nested: { a: 1 } }" 
  :depth="0" 
  :max-depth="3"
/>
```

**Internal State**:
- `expanded`: Expansion state for complex types
- `stringExpanded`: Expansion state for long strings
- `copied`: Copy feedback state

**Computed**:
- `isPrimitive`: Whether data is primitive type
- `isArray`: Whether data is array
- `type`: Data type ('string' | 'number' | 'boolean' | 'null' | 'undefined')
- `formattedValue`: Formatted primitive value
- `displayString`: Truncated or full string
- `previewContent`: Collapsed preview text
- `itemCount`: Number of items in object/array

---

## Project Components

### 🔷 ProjectCard.vue

**Purpose**: Display project summary in grid or list view.

**Props**:
```typescript
interface Props {
  project: Project
  viewMode: 'card' | 'list'
}
```

**Emits**:
- `click`: Project clicked (opens detail modal)
- `edit`: Edit button clicked
- `delete`: Delete button clicked

**Features**:
- Status badge (color-coded)
- Priority indicator
- Progress bar (0-100%)
- Cost vs Budget display
- Tags display
- GitHub/Workspace links (if present)
- Hover actions (Edit, Delete)

---

### 🔷 ProjectDetailModal.vue

**Purpose**: Full-screen modal showing project details and agent timeline.

**Props**:
```typescript
interface Props {
  project: Project
}
```

**Emits**:
- `close`: Close modal
- `edit`: Edit button clicked
- `delete`: Delete confirmation

**Tabs**:
1. **项目详情 (Details)**:
   - Description, notes
   - Status, priority, progress
   - Category, tags
   - Budget vs Actual cost
   - Created/Updated timestamps
   
2. **Agent 时间线 (Timeline)**:
   - AgentTimeline component
   - Loads runs/events on tab switch

**Features**:
- Tab navigation
- Auto-loads timeline when tab is clicked
- Error handling with retry button
- Edit/Delete actions in footer

---

### 🔷 ProjectFormModal.vue

**Purpose**: Create or edit project form.

**Props**:
```typescript
interface Props {
  project?: Project  // If provided, edit mode; else create mode
}
```

**Emits**:
- `close`: Close modal
- `submit`: Form submitted with data

**Form Fields**:
- Name (required)
- Description (textarea)
- Notes (textarea)
- Status (select)
- Priority (select)
- Progress (slider 0-100)
- Cost Total (number)
- Revenue Total (number)
- GitHub URL (text)
- Workspace Path (text)
- Tags (comma-separated)

**Validation**:
- Name is required
- Progress clamped to 0-100
- Numbers validated

---

## Layout Components

### 🔷 TheHeader.vue

**Purpose**: Application header with navigation and utilities.

**Features**:
- Logo and app name
- Theme toggle button (dark/light)
- Operations button (opens OpsModal)
- User menu (logout)

**State**:
- Uses `useTheme()` composable for theme management
- Uses `useAuthStore()` for user info

---

### 🔷 TheFilters.vue

**Purpose**: Filter bar for projects page.

**Emits**:
- `update:status`: Status filter changed
- `update:priority`: Priority filter changed
- `update:category`: Category filter changed
- `update:search`: Search query changed

**Features**:
- Status dropdown (all/planning/in-progress/paused/completed/cancelled)
- Priority dropdown (all/low/medium/high/urgent)
- Category input
- Search input
- Clear filters button

---

## Utility Components

### 🔷 Toast.vue

**Purpose**: Toast notification system.

**Props**:
```typescript
interface Props {
  message: string
  type?: 'success' | 'error' | 'info'
  duration?: number  // Auto-hide duration (ms)
}
```

**Features**:
- Auto-hide after duration
- Different colors per type
- Slide-in animation

---

### 🔷 StatsModal.vue

**Purpose**: Display aggregated project statistics.

**Features**:
- Total projects count
- By status breakdown
- By priority breakdown
- Financial summary (cost/revenue/profit)

---

### 🔷 OpsModal.vue

**Purpose**: Admin operations dashboard.

**Features**:
- Backup database (download)
- Restore database (upload)
- Deploy trigger (if configured)
- View deploy logs
- Requires admin token in headers

---

## Usage Examples

### Example 1: Opening Project Detail Modal

```vue
<script setup lang="ts">
import { ref } from 'vue'
import ProjectDetailModal from '@/components/ProjectDetailModal.vue'
import type { Project } from '@/api/types'

const selectedProject = ref<Project | null>(null)

function openProjectDetail(project: Project) {
  selectedProject.value = project
}

function closeModal() {
  selectedProject.value = null
}
</script>

<template>
  <div>
    <button @click="openProjectDetail(someProject)">
      View Details
    </button>
    
    <ProjectDetailModal
      v-if="selectedProject"
      :project="selectedProject"
      @close="closeModal"
      @edit="handleEdit"
      @delete="handleDelete"
    />
  </div>
</template>
```

### Example 2: Using DataViewer for Custom Data

```vue
<script setup lang="ts">
import DataViewer from '@/components/timeline/DataViewer.vue'

const complexData = {
  user: {
    name: 'John Doe',
    email: 'john@example.com',
    roles: ['admin', 'developer']
  },
  metrics: {
    requests: 12345,
    errors: 42
  }
}
</script>

<template>
  <div class="custom-viewer">
    <h3>System Metrics</h3>
    <DataViewer 
      :data="complexData" 
      :max-depth="2"
    />
  </div>
</template>
```

### Example 3: Custom Timeline Filter

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useAgentStore } from '@/stores/agent'
import AgentTimeline from '@/components/timeline/AgentTimeline.vue'

const agentStore = useAgentStore()

// Filter only failed runs and error events
const criticalRuns = computed(() => 
  agentStore.runs.filter(r => r.status === 'failed')
)

const criticalEvents = computed(() => 
  agentStore.events.filter(e => e.level === 'error')
)
</script>

<template>
  <div>
    <h2>Critical Issues</h2>
    <AgentTimeline 
      :runs="criticalRuns" 
      :events="criticalEvents"
    />
  </div>
</template>
```

---

## Component Best Practices

### 1. TypeScript Types
Always import types from `@/api/types.ts`:
```typescript
import type { Project, AgentRun, AgentEvent } from '@/api/types'
```

### 2. Prop Validation
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

### 3. Emits Definition
Always define emits with types:
```typescript
const emit = defineEmits<{
  submit: [data: FormData]
  cancel: []
}>()
```

### 4. CSS Variables
Use design tokens from `tokens.css`:
```css
.my-component {
  background: var(--card-bg);
  color: var(--text-primary);
  border-radius: var(--border-radius-sm);
  box-shadow: var(--shadow-md);
}
```

### 5. Theme Support
Components automatically support dark/light themes via CSS variables. No JavaScript theme logic needed in components (handled by `[data-theme]` attribute on root).

---

## Testing Components

### Manual Testing Checklist

- [ ] Component renders correctly in light theme
- [ ] Component renders correctly in dark theme
- [ ] All props work as expected
- [ ] All emits fire correctly
- [ ] Error states display properly
- [ ] Loading states display properly
- [ ] Responsive on mobile/tablet/desktop
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] No TypeScript errors
- [ ] No console errors/warnings

---

## Future Component Ideas

- [ ] ProjectTimeline.vue - Gantt-style project timeline
- [ ] AgentInsights.vue - Agent performance analytics dashboard
- [ ] TokenUsageChart.vue - Token usage visualization
- [ ] NotificationCenter.vue - Persistent notification system
- [ ] CommandPalette.vue - Keyboard command palette
- [ ] BulkProjectEditor.vue - Multi-select bulk edit interface

---

**Last Updated**: 2026-02-11  
**Version**: 1.0 (Timeline System Launch)
