<template>
  <div class="project-card" @click="$emit('click', project)" :data-project-id="project.id">
    <!-- Header: Title and Status/Priority -->
    <div class="card-header" :class="{ 'with-handle': showDragHandle }">
      <div class="header-main">
        <h3 class="project-name" :title="project.name">{{ project.name }}</h3>
        <div class="badges">
          <span class="badge priority-badge" :class="`priority-${project.priority}`">
            {{ priorityLabels[project.priority] || project.priority }}
          </span>
        </div>
      </div>
      <div class="header-sub">
        <span class="badge status-badge" :class="`status-${project.status}`">
          <span class="status-dot"></span>
          {{ statusLabels[project.status] || project.status }}
        </span>
        <span v-if="project.category" class="category-tag">{{ project.category }}</span>
      </div>
    </div>

    <!-- Body: Description with fixed space -->
    <div class="card-body">
      <p class="project-desc" :class="{ 'no-desc': !project.description }">
        {{ project.description || '暂无项目内容描述...' }}
      </p>
    </div>

    <!-- Progress: Sleek bar -->
    <div class="card-progress">
      <div class="progress-info">
        <span class="progress-label">项目进度</span>
        <span class="progress-value">{{ project.progress }}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${project.progress}%` }"></div>
      </div>
    </div>

    <!-- Footer: ID and Finance -->
    <div class="card-footer">
      <div 
        class="project-id-mini" 
        @click.stop="copyId" 
        :class="{ copied: copied }"
        :title="`点击复制 ID: ${project.id}`"
      >
        <span class="id-hash">#</span>
        <span class="id-value">{{ project.id.slice(0, 8) }}</span>
        <span class="copy-tooltip" v-if="copied">已复制</span>
      </div>
      
      <div class="finance-summary">
        <div class="finance-item cost">
          <span class="fin-label">成本</span>
          <span class="fin-value">¥{{ formatMoney(project.cost.total) }}</span>
        </div>
        <div class="finance-sep"></div>
        <div class="finance-item revenue">
          <span class="fin-label">收入</span>
          <span class="fin-value">¥{{ formatMoney(project.revenue.total) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { Project } from '../api/types'

const props = defineProps<{
  project: Project
  showDragHandle?: boolean
}>()

defineEmits<{
  click: [project: Project]
}>()

const copied = ref(false)

const statusLabels: Record<string, string> = {
  'planning': '计划中',
  'in-progress': '进行中',
  'paused': '暂停',
  'completed': '已完成',
  'cancelled': '已取消',
}

const priorityLabels: Record<string, string> = {
  'low': '低',
  'medium': '中',
  'high': '高',
  'urgent': '紧急',
}

function formatMoney(value: number): string {
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

async function copyId(event: Event) {
  event.stopPropagation()
  try {
    await navigator.clipboard.writeText(props.project.id)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy project ID:', err)
  }
}
</script>

<style scoped>
.project-card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--border-radius);
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 280px;
}

.project-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: var(--primary-color);
}

.card-header {
  margin-bottom: 12px;
  flex-shrink: 0;
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}

.project-name {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.4;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: normal;
  word-break: break-word;
}

.card-header.with-handle .project-name {
  padding-left: 28px;
}

.header-sub {
  display: flex;
  align-items: center;
  gap: 8px;
}

.category-tag {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-secondary);
  padding: 2px 6px;
  border-radius: 4px;
}

.card-body {
  flex: 1;
  margin-bottom: 16px;
  overflow: hidden;
}

.project-desc {
  color: var(--text-secondary);
  font-size: 13.5px;
  margin: 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.project-desc.no-desc {
  color: var(--text-muted);
  font-style: italic;
  opacity: 0.6;
}

.card-progress {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.progress-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.progress-value {
  font-size: 12px;
  color: var(--primary-color);
  font-weight: 700;
  font-family: 'SF Mono', monospace;
}

.progress-track {
  height: 4px;
  background: var(--bg-secondary);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary-color);
  border-radius: 2px;
  transition: width 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.card-footer {
  border-top: 1px solid var(--border-color);
  padding-top: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
  flex-shrink: 0;
}

.project-id-mini {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-family: 'SF Mono', 'Roboto Mono', monospace;
  font-size: 11px;
  color: var(--text-muted);
  opacity: 0.6;
  cursor: pointer;
  transition: all 0.2s;
  padding: 4px 0;
  position: relative;
}

.project-id-mini:hover {
  opacity: 1;
  color: var(--primary-color);
}

.id-hash {
  font-weight: bold;
}

.copy-tooltip {
  position: absolute;
  top: -24px;
  left: 0;
  background: var(--primary-color);
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  white-space: nowrap;
}

.finance-summary {
  display: flex;
  align-items: center;
  gap: 12px;
}

.finance-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.finance-sep {
  width: 1px;
  height: 16px;
  background: var(--border-color);
}

.fin-label {
  font-size: 9px;
  color: var(--text-muted);
  text-transform: uppercase;
  font-weight: 500;
}

.fin-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'SF Mono', monospace;
}

.finance-item.revenue .fin-value {
  color: var(--success-color);
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
}

.status-badge {
  gap: 4px;
}

.status-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background-color: currentColor;
}

.status-planning { background: var(--status-planning-bg); color: var(--status-planning-text); }
.status-in-progress { background: var(--status-in-progress-bg); color: var(--status-in-progress-text); }
.status-paused { background: var(--status-paused-bg); color: var(--status-paused-text); }
.status-completed { background: var(--status-completed-bg); color: var(--status-completed-text); }
.status-cancelled { background: var(--status-cancelled-bg); color: var(--status-cancelled-text); }

.priority-low { background: var(--priority-low-bg); color: var(--priority-low-text); }
.priority-medium { background: var(--priority-medium-bg); color: var(--priority-medium-text); }
.priority-high { background: var(--priority-high-bg); color: var(--priority-high-text); }
.priority-urgent { background: var(--priority-urgent-bg); color: var(--priority-urgent-text); }
</style>
