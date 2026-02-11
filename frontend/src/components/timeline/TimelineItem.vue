<template>
  <div class="timeline-item" :class="[item.type, { expanded: isExpanded }]">
    <!-- Marker / Icon -->
    <div class="timeline-marker" :class="statusClass" @click="toggle">
      <span v-if="isRun" class="marker-icon">R</span>
      <span v-else class="marker-icon">E</span>
    </div>

    <!-- Content -->
    <div class="timeline-content">
      <!-- Header -->
      <div class="timeline-header" @click="toggle">
        <div class="header-main">
          <span class="type-badge" :class="statusClass">
            {{ typeLabel }}
          </span>
          <span class="title" :title="itemTitle">
            {{ itemTitle }}
          </span>
        </div>
        <div class="header-meta">
          <span class="time">{{ formattedTime }}</span>
          <button class="btn-icon toggle-btn">
            {{ isExpanded ? '−' : '+' }}
          </button>
        </div>
      </div>

      <!-- Body (Collapsible) -->
      <div v-show="isExpanded" class="timeline-body">
        <!-- Run Specifics -->
        <div v-if="isRun" class="run-details">
          <div class="detail-grid">
            <div class="detail-item">
              <label>Status</label>
              <span class="status-text" :class="item.status">{{ item.status }}</span>
            </div>
            <div class="detail-item">
              <label>Agent</label>
              <span>{{ item.agentId || '-' }}</span>
            </div>
            <div class="detail-item">
              <label>Duration</label>
              <span>{{ duration }}</span>
            </div>
            <div class="detail-item" v-if="item.finishedAt">
              <label>Finished</label>
              <span>{{ formatTime(item.finishedAt) }}</span>
            </div>
          </div>

          <div v-if="item.summary" class="detail-block">
            <label>Summary</label>
            <p class="text-content">{{ item.summary }}</p>
          </div>

          <div v-if="hasMetrics" class="detail-block">
            <label>Metrics</label>
            <DataViewer :data="item.metrics" :depth="0" :max-depth="2" />
          </div>
        </div>

        <!-- Event Specifics -->
        <div v-else class="event-details">
          <div class="detail-grid">
            <div class="detail-item">
              <label>Level</label>
              <span class="level-badge" :class="item.level">{{ item.level }}</span>
            </div>
            <div class="detail-item">
              <label>Type</label>
              <span>{{ item.type }}</span>
            </div>
          </div>

          <div v-if="item.message" class="detail-block">
            <label>Message</label>
            <p class="text-content">{{ item.message }}</p>
          </div>

          <div v-if="hasData" class="detail-block">
            <label>Data</label>
            <DataViewer :data="item.data" :depth="0" :max-depth="3" />
          </div>
        </div>

        <!-- Actions -->
        <div class="timeline-actions">
          <button @click.stop="copyItemJson" class="btn-text">Copy JSON</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import DataViewer from './DataViewer.vue'
import type { AgentRun, AgentEvent } from '../../api/types'

// Define the mixed type used in the timeline
export type TimelineItemData = 
  | (AgentRun & { type: 'run'; timestamp: string })
  | (AgentEvent & { type: 'event'; timestamp: string; event_type: string }) // Note: AgentEvent has 'type' field which conflicts with our discriminator 'type'. 
  // Actually, in ProjectDetailModal, it mapped:
  // Run: type='run'
  // Event: type='event', event_type=event.type
  // I should follow that convention or define a cleaner one.
  // Let's assume the parent passes a clean object.
  // But wait, AgentEvent has a 'type' field (note/action/etc).
  // If I merge them, I need to be careful.
  // Let's define a wrapper interface.

export interface TimelineItemWrapper {
  id: string
  timestamp: string
  type: 'run' | 'event'
  data: AgentRun | AgentEvent
  // Helper fields for easier access
  status?: string // for run
  level?: string // for event
  title?: string
  summary?: string
  agentId?: string
  duration?: string
}

// However, to keep it simple and compatible with the "mixed" array approach:
// I'll accept `any` but cast it inside, or define a loose interface.
// The requirement says "Use api/types.ts".
// I will define a prop that accepts the union, but with a discriminator.

interface Props {
  item: any // Using any to be flexible with the merged object structure, but will cast safely
  initiallyExpanded?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  initiallyExpanded: false
})

const isExpanded = ref(props.initiallyExpanded)

const isRun = computed(() => props.item.type === 'run')

// Computed helpers
const itemTitle = computed(() => {
  if (isRun.value) {
    return props.item.title || props.item.summary || 'Untitled Run'
  } else {
    return props.item.title || props.item.event_type || 'Event'
  }
})

const typeLabel = computed(() => {
  if (isRun.value) return 'RUN'
  return props.item.event_type || 'EVENT'
})

const statusClass = computed(() => {
  if (isRun.value) {
    return props.item.status || 'unknown'
  } else {
    return props.item.level || 'info'
  }
})

const formattedTime = computed(() => {
  return formatTime(props.item.timestamp)
})

const duration = computed(() => {
  if (!isRun.value) return null
  const start = new Date(props.item.startedAt || props.item.createdAt).getTime()
  const end = props.item.finishedAt ? new Date(props.item.finishedAt).getTime() : Date.now()
  const diff = end - start
  
  if (diff < 1000) return `${diff}ms`
  if (diff < 60000) return `${(diff/1000).toFixed(1)}s`
  return `${(diff/60000).toFixed(1)}m`
})

const hasMetrics = computed(() => {
  return isRun.value && props.item.metrics && Object.keys(props.item.metrics).length > 0
})

const hasData = computed(() => {
  return !isRun.value && props.item.data !== undefined && props.item.data !== null
})

function toggle() {
  isExpanded.value = !isExpanded.value
}

function formatTime(ts: string) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    month: '2-digit',
    day: '2-digit'
  })
}

async function copyItemJson() {
  try {
    await navigator.clipboard.writeText(JSON.stringify(props.item, null, 2))
  } catch (e) {
    console.error(e)
  }
}
</script>

<style scoped>
.timeline-item {
  position: relative;
  padding-left: 24px;
  margin-bottom: 16px;
}

.timeline-item::before {
  content: '';
  position: absolute;
  left: 11px;
  top: 24px;
  bottom: -16px;
  width: 2px;
  background: var(--border-color);
}

.timeline-item:last-child::before {
  display: none;
}

.timeline-marker {
  position: absolute;
  left: 0;
  top: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bg-color);
  border: 2px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  cursor: pointer;
  transition: all 0.2s;
}

.timeline-marker:hover {
  transform: scale(1.1);
}

.marker-icon {
  font-size: 10px;
  font-weight: bold;
  color: var(--text-secondary);
}

/* Status Colors for Marker */
.timeline-marker.running { border-color: var(--status-in-progress-text); background: var(--status-in-progress-bg); }
.timeline-marker.completed { border-color: var(--status-completed-text); background: var(--status-completed-bg); }
.timeline-marker.failed { border-color: var(--status-cancelled-text); background: var(--status-cancelled-bg); }

.timeline-marker.error { border-color: var(--danger-color); color: var(--danger-color); }
.timeline-marker.warn { border-color: var(--status-in-progress-text); }
.timeline-marker.info { border-color: var(--primary-color); }

.timeline-content {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-sm);
  overflow: hidden;
  transition: box-shadow 0.2s;
}

.timeline-content:hover {
  box-shadow: var(--shadow-sm);
}

.timeline-header {
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  background: rgba(var(--bg-secondary), 0.3);
}

.timeline-header:hover {
  background: var(--bg-secondary);
}

.header-main {
  display: flex;
  align-items: center;
  gap: 12px;
  overflow: hidden;
}

.type-badge {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

/* Badge Colors */
.type-badge.running { background: var(--status-in-progress-bg); color: var(--status-in-progress-text); }
.type-badge.completed { background: var(--status-completed-bg); color: var(--status-completed-text); }
.type-badge.failed { background: var(--status-cancelled-bg); color: var(--status-cancelled-text); }

.type-badge.error { background: var(--status-cancelled-bg); color: var(--status-cancelled-text); }
.type-badge.warn { background: var(--status-in-progress-bg); color: var(--status-in-progress-text); }
.type-badge.info { background: var(--status-planning-bg); color: var(--status-planning-text); }
.type-badge.debug { background: var(--bg-secondary); color: var(--text-muted); }

.title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.time {
  font-size: 12px;
  color: var(--text-secondary);
}

.toggle-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
}

.timeline-body {
  padding: 16px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-color); /* Slightly different bg for body */
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item label {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 600;
}

.detail-item span {
  font-size: 13px;
  color: var(--text-primary);
}

.status-text {
  font-weight: 500;
  text-transform: capitalize;
}
.status-text.running { color: var(--status-in-progress-text); }
.status-text.completed { color: var(--status-completed-text); }
.status-text.failed { color: var(--status-cancelled-text); }

.detail-block {
  margin-top: 16px;
}

.detail-block label {
  display: block;
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 600;
  margin-bottom: 8px;
}

.text-content {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-primary);
  background: var(--card-bg);
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  margin: 0;
}

.timeline-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.btn-text {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  text-decoration: underline;
}

.btn-text:hover {
  color: var(--primary-color);
}
</style>
