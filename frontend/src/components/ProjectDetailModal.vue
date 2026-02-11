<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content detail-modal">
      <div class="modal-header">
        <h2>{{ project.name }}</h2>
        <button @click="$emit('close')" class="btn-close">×</button>
      </div>

      <div class="modal-tabs">
        <button
          :class="['tab-btn', { active: activeTab === 'details' }]"
          @click="activeTab = 'details'"
        >
          项目详情
        </button>
        <button
          :class="['tab-btn', { active: activeTab === 'timeline' }]"
          @click="activeTab = 'timeline'; loadTimeline()"
        >
          Agent 时间线
        </button>
      </div>

      <!-- Details Tab -->
      <div v-if="activeTab === 'details'" class="modal-body">
        <div class="detail-section">
          <label>描述</label>
          <p>{{ project.description || '无描述' }}</p>
        </div>

        <div class="detail-row">
          <div class="detail-section">
            <label>状态</label>
            <span class="badge" :class="`status-${project.status}`">
              {{ statusLabels[project.status] }}
            </span>
          </div>
          <div class="detail-section">
            <label>优先级</label>
            <span class="badge" :class="`priority-${project.priority}`">
              {{ priorityLabels[project.priority] }}
            </span>
          </div>
        </div>

        <div class="detail-row">
          <div class="detail-section">
            <label>分类</label>
            <p>{{ project.category || '-' }}</p>
          </div>
          <div class="detail-section">
            <label>进度</label>
            <div class="progress-bar-wrapper">
              <div class="progress-bar" :style="{ width: `${project.progress}%` }"></div>
              <span class="progress-text">{{ project.progress }}%</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <label>标签</label>
          <div class="tags">
            <span v-for="tag in project.tags" :key="tag" class="tag">{{ tag }}</span>
            <span v-if="!project.tags || project.tags.length === 0" class="text-muted">-</span>
          </div>
        </div>

        <div class="detail-row">
          <div class="detail-section">
            <label>创建时间</label>
            <p>{{ formatDate(project.createdAt) }}</p>
          </div>
          <div class="detail-section">
            <label>更新时间</label>
            <p>{{ formatDate(project.updatedAt) }}</p>
          </div>
        </div>

        <div class="detail-row">
          <div class="detail-section">
            <label>预算 (元)</label>
            <p>{{ formatMoney(getBudgetValue(project.budget)) }}</p>
          </div>
          <div class="detail-section">
            <label>已花费 (元)</label>
            <p>{{ formatMoney(getActualCostValue(project)) }}</p>
          </div>
        </div>
      </div>

      <!-- Timeline Tab -->
      <div v-else class="modal-body timeline-body">
        <div v-if="timelineError" class="error-timeline">
          <p>{{ timelineError }}</p>
          <button @click="loadTimeline" class="btn btn-secondary">重试</button>
        </div>

        <AgentTimeline 
          v-else
          :runs="agentStore.runs" 
          :events="agentStore.events" 
          :loading="loadingTimeline"
        />
      </div>

      <div class="modal-footer">
        <button @click="$emit('edit', project)" class="btn btn-primary">编辑</button>
        <button @click="handleDelete" class="btn btn-danger">删除</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAgentStore } from '../stores/agent'
import AgentTimeline from './timeline/AgentTimeline.vue'
import type { Project, AgentRun, AgentEvent } from '../api/types'

interface Props {
  project: Project
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  edit: [project: Project]
  delete: [id: string]
}>()

const agentStore = useAgentStore()
const activeTab = ref<'details' | 'timeline'>('details')
const loadingTimeline = ref(false)
const timelineError = ref<string | null>(null)

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

const eventTypeLabels: Record<string, string> = {
  'status_change': '状态变更',
  'progress_update': '进度更新',
  'comment': '备注',
  'file_added': '文件添加',
  'milestone': '里程碑',
}

async function loadTimeline() {
  loadingTimeline.value = true
  timelineError.value = null

  try {
    await agentStore.fetchProjectTimeline(props.project.id)
  } catch (err) {
    console.error('Failed to load timeline:', err)
    timelineError.value = '加载时间线失败'
  } finally {
    loadingTimeline.value = false
  }
}

function formatDate(date?: string | null): string {
  if (!date) {
    return '-'
  }
  const parsed = new Date(date)
  if (Number.isNaN(parsed.getTime())) {
    return '-'
  }
  return parsed.toLocaleString('zh-CN')
}

function formatMoney(value: number): string {
  const safeValue = Number.isFinite(value) ? value : 0
  return safeValue.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function getBudgetValue(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (value && typeof value === 'object') {
    const planned = (value as { planned?: unknown; total?: unknown; amount?: unknown }).planned
      ?? (value as { planned?: unknown; total?: unknown; amount?: unknown }).total
      ?? (value as { planned?: unknown; total?: unknown; amount?: unknown }).amount
    const num = Number(planned)
    return Number.isFinite(num) ? num : 0
  }
  const num = Number(value)
  return Number.isFinite(num) ? num : 0
}

function getActualCostValue(project: Project): number {
  const raw = (project as { actualCost?: unknown; actual_cost?: unknown }).actualCost
    ?? (project as { actualCost?: unknown; actual_cost?: unknown }).actual_cost
  if (raw !== undefined && raw !== null) {
    const num = Number(raw)
    return Number.isFinite(num) ? num : 0
  }
  const cost = (project as { cost?: { total?: unknown } }).cost
  if (cost && typeof cost === 'object') {
    const num = Number(cost.total)
    return Number.isFinite(num) ? num : 0
  }
  return 0
}

function handleDelete() {
  if (confirm(`确定要删除项目"${props.project.name}"吗？`)) {
    emit('delete', props.project.id)
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: var(--card-bg);
  border-radius: var(--border-radius);
  backdrop-filter: var(--backdrop-blur);
  box-shadow: var(--shadow-lg);
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-color);
}

.detail-modal {
  max-width: 800px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  color: var(--text-primary);
}

.btn-close {
  background: none;
  border: none;
  font-size: 28px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background 0.2s;
}

.btn-close:hover {
  background: var(--bg-color);
}

.modal-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.tab-btn {
  flex: 1;
  padding: 12px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: rgba(59, 130, 246, 0.05);
}

.tab-btn.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.timeline-body {
  padding: 16px 24px;
}

.detail-section {
  margin-bottom: 20px;
}

.detail-section label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-section p {
  margin: 0;
  color: var(--text-primary);
}

.detail-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tag {
  padding: 4px 10px;
  background: var(--bg-color);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.text-muted {
  color: var(--text-muted);
}

.progress-bar-wrapper {
  position: relative;
  width: 100%;
  height: 24px;
  background: var(--bg-secondary);
  border-radius: 12px;
  overflow: hidden;
  margin-top: 4px;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--primary-hover));
  transition: width 0.3s;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
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

/* Timeline styles */
.timeline-body {
  padding: 0;
}

.error-timeline {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  flex-shrink: 0;
}

.btn {
  padding: 10px 20px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-hover);
}

.btn-secondary {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--bg-color);
}

.btn-danger {
  background: var(--danger-color);
  color: white;
}

.btn-danger:hover {
  background: #dc2626;
  box-shadow: 0 4px 8px rgba(239, 68, 68, 0.3);
}
</style>
