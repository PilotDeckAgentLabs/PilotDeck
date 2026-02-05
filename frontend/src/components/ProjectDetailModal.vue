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
        <div v-if="loadingTimeline" class="loading-timeline">
          <div class="spinner"></div>
          <p>加载时间线...</p>
        </div>

        <div v-else-if="timelineError" class="error-timeline">
          <p>{{ timelineError }}</p>
          <button @click="loadTimeline" class="btn btn-secondary">重试</button>
        </div>

        <div v-else-if="timeline.length === 0" class="empty-timeline">
          <p>该项目暂无 Agent 活动记录</p>
        </div>

        <div v-else class="timeline">
          <div v-for="item in timeline" :key="item.id" class="timeline-item">
            <div class="timeline-marker" :class="item.type"></div>
            <div class="timeline-content">
              <div class="timeline-header">
                <span class="timeline-type-badge" :class="item.type">
                  {{ item.type === 'run' ? 'Agent Run' : 'Event' }}
                </span>
                <span class="timeline-time">{{ formatDate(item.timestamp) }}</span>
              </div>

              <div v-if="item.type === 'run'" class="timeline-run">
                <div class="run-info">
                  <span class="run-status" :class="item.status">{{ item.status }}</span>
                  <span class="run-agent" v-if="item.agent_name">{{ item.agent_name }}</span>
                </div>
                <p v-if="item.task_description" class="run-description">
                  {{ item.task_description }}
                </p>
                <div v-if="item.result" class="run-result">
                  <strong>结果:</strong> {{ item.result }}
                </div>
              </div>

              <div v-else class="timeline-event">
                <div class="event-type" :class="item.event_type">
                  {{ eventTypeLabels[item.event_type] || item.event_type }}
                </div>
                <p v-if="item.description" class="event-description">
                  {{ item.description }}
                </p>
                <div v-if="item.data" class="event-data">
                  <pre>{{ JSON.stringify(item.data, null, 2) }}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
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

// Merge runs and events into chronological timeline
const timeline = computed(() => {
  const items: Array<{ id: string; timestamp: string; type: 'run' | 'event'; [key: string]: any }> = []

  // Add runs
  agentStore.runs.forEach((run: AgentRun) => {
    if (run.projectId === props.project.id) {
      const ts = String(run.startedAt || run.createdAt || run.updatedAt || '')
      if (ts) {
        items.push({
          ...run,
          type: 'run',
          timestamp: ts,
        })
      }
    }
  })

  // Add events
  agentStore.events.forEach((event: AgentEvent, idx: number) => {
    if (event.projectId === props.project.id) {
      const ts = String(event.ts || '')
      if (ts) {
        items.push({
          ...event,
          type: 'event',
          id: String(event.id || `evt-${idx}`),
          timestamp: ts,
        })
      }
    }
  })

  // Sort by timestamp descending (newest first)
  return items.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
})

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
.loading-timeline,
.error-timeline,
.empty-timeline {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.spinner {
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.timeline {
  position: relative;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--border-color);
}

.timeline-item {
  position: relative;
  padding-left: 32px;
  padding-bottom: 24px;
}

.timeline-marker {
  position: absolute;
  left: 0;
  top: 4px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 3px solid var(--card-bg);
  z-index: 1;
}

.timeline-marker.run {
  background: var(--primary-color);
}

.timeline-marker.event {
  background: var(--text-secondary);
}

.timeline-content {
  background: rgba(var(--bg-color), 0.5); /* Slight transparency? No, use card-bg but maybe simpler */
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px 16px;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.timeline-type-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.timeline-type-badge.run {
  background: var(--primary-color);
  color: white;
}

.timeline-type-badge.event {
  background: var(--text-secondary);
  color: white;
}

.timeline-time {
  font-size: 12px;
  color: var(--text-secondary);
}

.timeline-run .run-info {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.run-status {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
}

.run-status.pending { background: var(--status-planning-bg); color: var(--status-planning-text); }
.run-status.running { background: var(--status-in-progress-bg); color: var(--status-in-progress-text); }
.run-status.completed { background: var(--status-completed-bg); color: var(--status-completed-text); }
.run-status.failed { background: var(--status-cancelled-bg); color: var(--status-cancelled-text); }

.run-agent {
  font-size: 12px;
  color: var(--text-secondary);
}

.run-description,
.event-description {
  margin: 8px 0;
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.5;
}

.run-result {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(0,0,0,0.05); /* Simple tint */
  border-radius: 4px;
  font-size: 13px;
}

.event-type {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  margin-bottom: 8px;
}

.event-type.status_change { background: var(--status-planning-bg); color: var(--status-planning-text); }
.event-type.progress_update { background: var(--status-in-progress-bg); color: var(--status-in-progress-text); }
.event-type.comment { background: var(--status-paused-bg); color: var(--status-paused-text); }
.event-type.file_added { background: var(--status-completed-bg); color: var(--status-completed-text); }
.event-type.milestone { background: var(--priority-high-bg); color: var(--priority-high-text); }

.event-data {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(0,0,0,0.05);
  border-radius: 4px;
  overflow-x: auto;
}

.event-data pre {
  margin: 0;
  font-size: 12px;
  font-family: 'SF Mono', 'Courier New', monospace;
  color: var(--text-primary);
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
