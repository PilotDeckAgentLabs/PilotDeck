<template>
  <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>统计信息</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <div class="stats-body">
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
          <p>加载中...</p>
        </div>

        <div v-else-if="error" class="error-state">
          <p class="error-text">{{ error }}</p>
          <button class="btn btn-secondary" @click="loadStats">重试</button>
        </div>

        <div v-else-if="stats" class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">项目总数</div>
            <div class="stat-value">{{ stats.total }}</div>
          </div>

          <div class="stat-section">
            <h3>按状态统计</h3>
            <div class="stat-list">
              <div v-for="(count, status) in stats.byStatus" :key="status" class="stat-item">
                <span class="badge" :class="`status-${status}`">
                  {{ statusLabels[status] || status }}
                </span>
                <span class="stat-count">{{ count }}</span>
              </div>
            </div>
          </div>

          <div class="stat-section">
            <h3>按优先级统计</h3>
            <div class="stat-list">
              <div v-for="(count, priority) in stats.byPriority" :key="priority" class="stat-item">
                <span class="badge" :class="`priority-${priority}`">
                  {{ priorityLabels[priority] || priority }}
                </span>
                <span class="stat-count">{{ count }}</span>
              </div>
            </div>
          </div>

          <div class="stat-section financial">
            <h3>财务汇总</h3>
            <div class="financial-grid">
              <div class="financial-item">
                <span class="label">总成本</span>
                <span class="value cost">¥{{ formatMoney(stats.financial.totalCost) }}</span>
              </div>
              <div class="financial-item">
                <span class="label">总收入</span>
                <span class="value revenue">¥{{ formatMoney(stats.financial.totalRevenue) }}</span>
              </div>
              <div class="financial-item">
                <span class="label">净利润</span>
                <span class="value" :class="stats.financial.netProfit >= 0 ? 'profit' : 'loss'">
                  ¥{{ formatMoney(stats.financial.netProfit) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Stats } from '../api/types'
import * as api from '../api/client'

const props = defineProps<{
  show: boolean
}>()

defineEmits<{
  close: []
}>()

const loading = ref(false)
const stats = ref<Stats | null>(null)
const error = ref<string | null>(null)

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

async function loadStats() {
  loading.value = true
  error.value = null
  try {
    stats.value = await api.getStats()
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : '加载统计信息失败'
    error.value = message
    console.error('Failed to load stats:', e)
  } finally {
    loading.value = false
  }
}

watch(
  () => props.show,
  (show) => {
    if (show) {
      loadStats()
    }
  },
  { immediate: true }
)

function formatMoney(value: number): string {
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
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
  border-radius: 12px;
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  color: var(--text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  line-height: 1;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--bg-color);
  color: var(--text-primary);
}

.stats-body {
  padding: 24px;
  min-height: 200px;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px;
  color: var(--text-secondary);
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px;
}

.error-text {
  color: var(--danger-color);
  font-size: 14px;
  text-align: center;
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

.stats-grid {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.stat-card {
  background: var(--bg-color);
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--primary-color);
}

.stat-section h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: var(--text-primary);
}

.stat-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-color);
  border-radius: 6px;
}

.badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
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

.stat-count {
  font-weight: 600;
  color: var(--text-primary);
}

.financial-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.financial-item {
  background: var(--bg-color);
  padding: 16px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.financial-item .label {
  font-size: 13px;
  color: var(--text-secondary);
}

.financial-item .value {
  font-size: 20px;
  font-weight: 700;
}

.financial-item .value.cost {
  color: var(--danger-color);
}

.financial-item .value.revenue {
  color: var(--success-color);
}

.financial-item .value.profit {
  color: var(--success-color);
}

.financial-item .value.loss {
  color: var(--danger-color);
}
</style>
