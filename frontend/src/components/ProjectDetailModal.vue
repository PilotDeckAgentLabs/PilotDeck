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
            <p>{{ formatDate(project.created_at) }}</p>
          </div>
          <div class="detail-section">
            <label>更新时间</label>
            <p>{{ formatDate(project.updated_at) }}</p>
          </div>
        </div>

        <div v-if="project.budget" class="detail-row">
          <div class="detail-section">
            <label>预算 (元)</label>
            <p>{{ project.budget.toLocaleString() }}</p>
          </div>
          <div class="detail-section">
            <label>已花费 (元)</label>
            <p>{{ (project.actual_cost || 0).toLocaleString() }}</p>
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

function formatDate(date: string): string {
  return new Date(date).toLocaleString('zh-CN')
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
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
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
  background: var(--hover-bg);
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
  background: var(--hover-bg);
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
  background: var(--tag-bg);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.text-muted {
  color: var(--text-secondary);
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

.status-planning { background: #dbeafe; color: #1e40af; }
.status-in-progress { background: #fef3c7; color: #92400e; }
.status-paused { background: #e5e7eb; color: #374151; }
.status-completed { background: #d1fae5; color: #065f46; }
.status-cancelled { background: #fee2e2; color: #991b1b; }

.priority-low { background: #f3f4f6; color: #6b7280; }
.priority-medium { background: #dbeafe; color: #1e40af; }
.priority-high { background: #fed7aa; color: #9a3412; }
.priority-urgent { background: #fecaca; color: #991b1b; }

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
  background: var(--secondary-color);
}

.timeline-content {
  background: var(--card-bg);
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
  background: var(--secondary-color);
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

.run-status.pending { background: #fef3c7; color: #92400e; }
.run-status.running { background: #dbeafe; color: #1e40af; }
.run-status.completed { background: #d1fae5; color: #065f46; }
.run-status.failed { background: #fee2e2; color: #991b1b; }

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
  background: var(--bg-secondary);
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

.event-type.status_change { background: #dbeafe; color: #1e40af; }
.event-type.progress_update { background: #fef3c7; color: #92400e; }
.event-type.comment { background: #e5e7eb; color: #374151; }
.event-type.file_added { background: #d1fae5; color: #065f46; }
.event-type.milestone { background: #fecaca; color: #991b1b; }

.event-data {
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow-x: auto;
}

.event-data pre {
  margin: 0;
  font-size: 12px;
  font-family: 'Courier New', monospace;
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
  background: var(--secondary-color);
  color: white;
}

.btn-danger {
  background: #dc2626;
  color: white;
}

.btn-danger:hover {
  background: #b91c1c;
}
</style>
