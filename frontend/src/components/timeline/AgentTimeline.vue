<template>
  <div class="agent-timeline">
    <!-- Controls -->
    <div class="timeline-controls">
      <div class="search-bar">
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="搜索 Agent 活动..." 
          class="search-input"
        />
      </div>
      
      <div class="filters">
        <select v-model="filterType" class="filter-select">
          <option value="all">全部类型</option>
          <option value="run">Runs</option>
          <option value="event">Events</option>
        </select>
        
        <select v-model="filterLevel" class="filter-select">
          <option value="all">全部级别</option>
          <option value="info">Info+</option>
          <option value="warn">Warn+</option>
          <option value="error">Error Only</option>
        </select>
      </div>
    </div>

    <!-- Timeline List -->
    <div class="timeline-list" ref="listContainer">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="filteredTimeline.length === 0" class="empty-state">
        <p>没有找到相关记录</p>
      </div>

      <div v-else>
        <TimelineItem
          v-for="item in visibleTimeline"
          :key="item.id"
          :item="item"
          :initially-expanded="false"
        />
        
        <div v-if="hasMore" class="load-more">
          <button @click="loadMore" class="btn-load-more">
            加载更多 ({{ remainingCount }})
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import TimelineItem from './TimelineItem.vue'
import type { AgentRun, AgentEvent } from '../../api/types'

interface Props {
  runs: AgentRun[]
  events: AgentEvent[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  runs: () => [],
  events: () => [],
  loading: false
})

// State
const searchQuery = ref('')
const filterType = ref<'all' | 'run' | 'event'>('all')
const filterLevel = ref<'all' | 'info' | 'warn' | 'error'>('all')
const displayLimit = ref(50)

// Reset limit when filters change
watch([searchQuery, filterType, filterLevel], () => {
  displayLimit.value = 50
})

// Merged & Sorted Timeline
const mergedTimeline = computed(() => {
  const items: any[] = []

  // Process Runs
  props.runs.forEach(run => {
    const ts = run.startedAt || run.createdAt || run.updatedAt
    if (ts) {
      items.push({
        ...run,
        type: 'run',
        timestamp: ts,
        // Normalize fields for search
        _search: `${run.title || ''} ${run.summary || ''} ${run.agentId || ''} ${run.status || ''}`.toLowerCase()
      })
    }
  })

  // Process Events
  props.events.forEach((event, idx) => {
    const ts = event.ts
    if (ts) {
      items.push({
        ...event,
        type: 'event',
        id: event.id || `evt-${idx}-${Date.now()}`, // Ensure ID
        timestamp: ts,
        event_type: event.type, // Map type to event_type to avoid conflict if needed, but we use type='event' discriminator
        // Normalize fields for search
        _search: `${event.title || ''} ${event.message || ''} ${event.agentId || ''} ${event.type || ''}`.toLowerCase()
      })
    }
  })

  // Sort descending
  return items.sort((a, b) => {
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  })
})

// Filtered Timeline
const filteredTimeline = computed(() => {
  let result = mergedTimeline.value

  // 1. Filter by Type
  if (filterType.value !== 'all') {
    result = result.filter(item => item.type === filterType.value)
  }

  // 2. Filter by Level (only affects events, or maybe runs if we map status)
  // For now, only filter events. Runs are always shown unless filtered by type.
  if (filterLevel.value !== 'all') {
    const levels = ['debug', 'info', 'warn', 'error']
    const minLevelIdx = levels.indexOf(filterLevel.value)
    
    result = result.filter(item => {
      if (item.type === 'run') return true // Always show runs in level filter? Or maybe filter failed runs?
      // Let's keep runs visible as they are important context.
      // Or maybe map 'failed' run to 'error' level?
      
      const itemLevel = (item.level || 'info').toLowerCase()
      const itemLevelIdx = levels.indexOf(itemLevel)
      return itemLevelIdx >= minLevelIdx
    })
  }

  // 3. Search
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(item => item._search.includes(query))
  }

  return result
})

// Visible Timeline (Pagination/Virtual Scroll)
const visibleTimeline = computed(() => {
  return filteredTimeline.value.slice(0, displayLimit.value)
})

const hasMore = computed(() => {
  return displayLimit.value < filteredTimeline.value.length
})

const remainingCount = computed(() => {
  return filteredTimeline.value.length - displayLimit.value
})

function loadMore() {
  displayLimit.value += 50
}
</script>

<style scoped>
.agent-timeline {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-color);
  border-radius: var(--border-radius);
  overflow: hidden;
}

.timeline-controls {
  padding: 16px;
  background: var(--card-bg);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.search-bar {
  flex: 1;
  min-width: 200px;
}

.search-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-sm);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px var(--primary-glow);
}

.filters {
  display: flex;
  gap: 8px;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-sm);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
}

.filter-select:focus {
  outline: none;
  border-color: var(--primary-color);
}

.timeline-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  position: relative;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: var(--text-secondary);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--bg-secondary);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.load-more {
  display: flex;
  justify-content: center;
  padding: 20px 0;
}

.btn-load-more {
  padding: 8px 24px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.btn-load-more:hover {
  background: var(--bg-color);
  color: var(--primary-color);
  border-color: var(--primary-color);
}
</style>
