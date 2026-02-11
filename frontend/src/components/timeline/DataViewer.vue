<template>
  <div class="data-viewer" :class="{ 'root-node': depth === 0 }">
    <!-- Root Actions -->
    <div v-if="depth === 0 && showCopy" class="root-actions">
      <button @click="copyJson" class="copy-btn" title="Copy JSON">
        <span v-if="copied">已复制!</span>
        <span v-else>复制 JSON</span>
      </button>
    </div>

    <!-- Primitive Types -->
    <div v-if="isPrimitive" class="primitive-row">
      <span v-if="label" class="key">{{ label }}: </span>
      <span 
        :class="['value', type, { 'clickable': type === 'string' || type === 'number' }]" 
        @click="copyValue" 
        :title="type === 'string' || type === 'number' ? '点击复制值' : ''"
      >
        <template v-if="type === 'string'">
          <span class="string-quote">"</span>{{ displayString }}<span class="string-quote">"</span>
        </template>
        <template v-else>{{ formattedValue }}</template>
      </span>
      <span v-if="type === 'string' && isLongString" class="expand-string-btn" @click.stop="toggleString">
        {{ stringExpanded ? '收起' : '展开' }}
      </span>
    </div>

    <!-- Complex Types (Object/Array) -->
    <div v-else class="complex-row">
      <div class="header" @click="toggle">
        <span class="toggle-icon" :class="{ expanded }">▶</span>
        <span v-if="label" class="key">{{ label }}: </span>
        <span class="bracket-start">{{ isArray ? '[' : '{' }}</span>
        
        <span v-if="!expanded" class="collapsed-preview">
          {{ previewContent }}
        </span>
        
        <span v-if="!expanded" class="bracket-end">{{ isArray ? ']' : '}' }}</span>
        <span v-if="!expanded" class="item-count-badge">
          {{ itemCount }} {{ itemCount === 1 ? 'item' : 'items' }}
        </span>
      </div>

      <div v-if="expanded" class="children-container">
        <DataViewer
          v-for="(value, key) in data"
          :key="key"
          :data="value"
          :label="isArray ? undefined : String(key)"
          :depth="depth + 1"
          :max-depth="maxDepth"
          :show-copy="false"
        />
        <div class="bracket-end-row">{{ isArray ? ']' : '}' }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface Props {
  data: any
  label?: string
  depth?: number
  maxDepth?: number
  showCopy?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  depth: 0,
  maxDepth: 3,
  showCopy: true
})

const expanded = ref(props.depth < props.maxDepth)
const stringExpanded = ref(false)
const copied = ref(false)

const type = computed(() => {
  if (props.data === null) return 'null'
  if (props.data === undefined) return 'undefined'
  if (Array.isArray(props.data)) return 'array'
  return typeof props.data
})

const isPrimitive = computed(() => {
  return ['string', 'number', 'boolean', 'null', 'undefined', 'symbol'].includes(type.value)
})

const isArray = computed(() => type.value === 'array')

const itemCount = computed(() => {
  if (isPrimitive.value) return 0
  return Object.keys(props.data).length
})

const formattedValue = computed(() => {
  if (props.data === null) return 'null'
  if (props.data === undefined) return 'undefined'
  return String(props.data)
})

const isLongString = computed(() => {
  return type.value === 'string' && props.data.length > 100
})

const displayString = computed(() => {
  if (type.value !== 'string') return ''
  if (isLongString.value && !stringExpanded.value) {
    return props.data.slice(0, 100) + '...'
  }
  return props.data
})

const previewContent = computed(() => {
  if (itemCount.value === 0) return ''
  if (isArray.value) {
    return ' ... '
  }
  const keys = Object.keys(props.data).slice(0, 3)
  return keys.join(', ') + (Object.keys(props.data).length > 3 ? ', ...' : '')
})

function toggle() {
  expanded.value = !expanded.value
}

function toggleString() {
  stringExpanded.value = !stringExpanded.value
}

async function copyValue() {
  if (type.value === 'string' || type.value === 'number') {
    try {
      await navigator.clipboard.writeText(String(props.data))
      // Could show a tooltip here
    } catch (err) {
      console.error('Failed to copy', err)
    }
  }
}

async function copyJson() {
  try {
    await navigator.clipboard.writeText(JSON.stringify(props.data, null, 2))
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy JSON', err)
  }
}
</script>

<style scoped>
.data-viewer {
  font-family: 'SF Mono', 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
}

.root-node {
  position: relative;
}

.root-actions {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 10;
}

.copy-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.copy-btn:hover {
  background: var(--bg-color);
  color: var(--primary-color);
}

.primitive-row, .complex-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
}

.complex-row {
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.header:hover .key {
  color: var(--text-primary);
}

.toggle-icon {
  display: inline-block;
  width: 16px;
  height: 16px;
  line-height: 16px;
  text-align: center;
  font-size: 10px;
  color: var(--text-muted);
  transition: transform 0.2s;
  margin-right: 4px;
}

.toggle-icon.expanded {
  transform: rotate(90deg);
}

.key {
  color: var(--text-secondary); /* Purple-ish in some themes, but sticking to tokens */
  margin-right: 6px;
  font-weight: 600;
}

.value {
  word-break: break-all;
}

.value.string { color: var(--status-completed-text); } /* Green */
.value.number { color: var(--status-in-progress-text); } /* Orange */
.value.boolean { color: var(--priority-medium-text); } /* Blue */
.value.null { color: var(--text-muted); font-style: italic; }
.value.undefined { color: var(--text-muted); font-style: italic; }

.string-quote {
  opacity: 0.7;
}

.clickable {
  cursor: pointer;
}

.clickable:hover {
  text-decoration: underline;
}

.expand-string-btn {
  margin-left: 8px;
  font-size: 11px;
  color: var(--text-muted);
  cursor: pointer;
  text-decoration: underline;
}

.expand-string-btn:hover {
  color: var(--primary-color);
}

.collapsed-preview {
  color: var(--text-muted);
  font-style: italic;
  margin: 0 4px;
}

.item-count-badge {
  margin-left: 8px;
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-secondary);
  padding: 0 4px;
  border-radius: 4px;
}

.children-container {
  padding-left: 20px;
  border-left: 1px solid var(--border-color);
  margin-left: 7px; /* Align with arrow */
}

.bracket-start, .bracket-end, .bracket-end-row {
  color: var(--text-muted);
  font-weight: bold;
}
</style>
