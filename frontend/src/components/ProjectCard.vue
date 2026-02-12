<template>
  <div class="project-card" @click="$emit('click', project)" :data-project-id="project.id">
    <div class="card-header">
      <div class="header-top">
        <h3 class="project-name">{{ project.name }}</h3>
        <span class="badge priority-badge" :class="`priority-${project.priority}`">
          {{ priorityLabels[project.priority] || project.priority }}
        </span>
      </div>
      <div class="project-id-chip" :title="project.id">
        <code class="id-chip-value">{{ project.id.slice(0, 10) }}...</code>
        <button
          @click.stop="copyId"
          class="copy-id-chip-btn"
          :class="{ copied: copied }"
          :title="copied ? '已复制!' : '复制完整ID'"
        >
          {{ copied ? '✓' : '复制ID' }}
        </button>
      </div>
      <div class="status-wrapper">
        <span class="badge status-badge" :class="`status-${project.status}`">
          <span class="status-dot"></span>
          {{ statusLabels[project.status] || project.status }}
        </span>
      </div>
    </div>

    <p v-if="project.description" class="project-desc">{{ project.description }}</p>

    <div class="progress-section">
      <div class="progress-label">
        <span>进度</span>
        <span class="progress-value">{{ project.progress }}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${project.progress}%` }"></div>
      </div>
    </div>

    <div class="card-footer">
      <div class="footer-content">
        <div class="finance">
          <div class="finance-item cost">
            <span class="label">成本</span>
            <span class="value">¥{{ formatMoney(project.cost.total) }}</span>
          </div>
          <div class="finance-divider"></div>
          <div class="finance-item revenue">
            <span class="label">收入</span>
            <span class="value">¥{{ formatMoney(project.revenue.total) }}</span>
          </div>
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
}

.project-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: var(--primary-color);
}

.card-header {
  margin-bottom: 16px;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.project-name {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.4;
  flex: 1;
  padding-right: 12px;
}

.status-wrapper {
  display: flex;
}

.project-id-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.id-chip-value {
  font-family: 'SF Mono', 'Roboto Mono', monospace;
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 4px 8px;
}

.copy-id-chip-btn {
  border: 1px solid var(--border-color);
  background: var(--card-bg);
  color: var(--text-muted);
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  padding: 4px 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.copy-id-chip-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.copy-id-chip-btn.copied {
  border-color: var(--success-color);
  color: var(--success-color);
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  letter-spacing: 0.5px;
}

.status-badge {
  gap: 6px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: currentColor;
}

/* Status Colors from Tokens */
.status-planning { background: var(--status-planning-bg); color: var(--status-planning-text); }
.status-in-progress { background: var(--status-in-progress-bg); color: var(--status-in-progress-text); }
.status-paused { background: var(--status-paused-bg); color: var(--status-paused-text); }
.status-completed { background: var(--status-completed-bg); color: var(--status-completed-text); }
.status-cancelled { background: var(--status-cancelled-bg); color: var(--status-cancelled-text); }

/* Priority Colors from Tokens */
.priority-low { background: var(--priority-low-bg); color: var(--priority-low-text); }
.priority-medium { background: var(--priority-medium-bg); color: var(--priority-medium-text); }
.priority-high { background: var(--priority-high-bg); color: var(--priority-high-text); }
.priority-urgent { background: var(--priority-urgent-bg); color: var(--priority-urgent-text); }

.project-desc {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0 0 20px 0;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex-grow: 1;
}

.progress-section {
  margin-bottom: 16px;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 8px;
  color: var(--text-muted);
  font-weight: 500;
}

.progress-value {
  color: var(--primary-color);
  font-weight: 600;
}

.progress-track {
  height: 6px;
  background: var(--bg-color);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--primary-hover));
  border-radius: 3px;
  transition: width 0.5s ease-out;
  box-shadow: 0 0 10px var(--primary-glow);
}

.card-footer {
  border-top: 1px solid var(--border-color);
  padding-top: 12px;
  margin-top: auto;
}

.footer-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.finance {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
}

.finance-divider {
  width: 1px;
  height: 24px;
  background: var(--border-color);
}

.finance-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.finance-item.cost { text-align: left; }
.finance-item.revenue { text-align: right; }

.finance-item .label {
  color: var(--text-muted);
  font-size: 11px;
  text-transform: uppercase;
}

.finance-item .value {
  font-weight: 600;
  font-size: 14px;
  font-family: 'SF Mono', 'Roboto Mono', monospace; /* Tech feel */
}

.finance-item.cost .value { color: var(--text-primary); }
.finance-item.revenue .value { color: var(--success-color); }
</style>
