<template>
  <div class="project-card" @click="$emit('click', project)">
    <div class="card-header">
      <h3 class="project-name">{{ project.name }}</h3>
      <div class="badges">
        <span class="badge" :class="`status-${project.status}`">
          {{ statusLabels[project.status] || project.status }}
        </span>
        <span class="badge" :class="`priority-${project.priority}`">
          {{ priorityLabels[project.priority] || project.priority }}
        </span>
      </div>
    </div>

    <p v-if="project.description" class="project-desc">{{ project.description }}</p>

    <div class="progress-section">
      <div class="progress-label">
        <span>进度</span>
        <span class="progress-value">{{ project.progress }}%</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${project.progress}%` }"></div>
      </div>
    </div>

    <div class="card-footer">
      <div class="finance">
        <span class="finance-item cost">
          <span class="label">成本:</span>
          <span class="value">¥{{ formatMoney(project.cost.total) }}</span>
        </span>
        <span class="finance-item revenue">
          <span class="label">收入:</span>
          <span class="value">¥{{ formatMoney(project.revenue.total) }}</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Project } from '../api/types'

defineProps<{
  project: Project
}>()

defineEmits<{
  click: [project: Project]
}>()

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
</script>

<style scoped>
.project-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: var(--shadow);
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
  border-color: var(--primary-color);
}

.card-header {
  margin-bottom: 12px;
}

.project-name {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.badge {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-planning { background: #dbeafe; color: #1e40af; }
.status-in-progress { background: #fef3c7; color: #92400e; }
.status-paused { background: #e5e7eb; color: #374151; }
.status-completed { background: #d1fae5; color: #065f46; }
.status-cancelled { background: #fee2e2; color: #991b1b; }

.priority-low { background: #f3f4f6; color: #6b7280; }
.priority-medium { background: #dbeafe; color: #1e40af; }
.priority-high { background: #fed7aa; color: #9a3412; }
.priority-urgent { background: #fecaca; color: #991b1b; }

.project-desc {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0 0 12px 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.progress-section {
  margin-bottom: 12px;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 6px;
  color: var(--text-secondary);
}

.progress-value {
  font-weight: 600;
  color: var(--text-primary);
}

.progress-bar {
  height: 6px;
  background: var(--bg-color);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--primary-hover));
  border-radius: 3px;
  transition: width 0.3s ease;
}

.card-footer {
  border-top: 1px solid var(--border-color);
  padding-top: 12px;
}

.finance {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.finance-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.finance-item .label {
  color: var(--text-muted);
  font-size: 12px;
}

.finance-item .value {
  font-weight: 600;
  color: var(--text-primary);
}

.finance-item.cost .value {
  color: var(--danger-color);
}

.finance-item.revenue .value {
  color: var(--success-color);
}
</style>
