<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content detail-modal">
      <div class="modal-header">
        <div class="header-content">
          <h2>{{ project.name }}</h2>
          <div class="project-id-row">
            <span class="project-id-label">ID:</span>
            <code class="project-id">{{ project.id }}</code>
            <button 
              @click.stop="copyProjectId" 
              class="copy-id-btn"
              :class="{ copied: idCopied }"
              :title="idCopied ? '已复制!' : '复制项目ID'"
            >
              {{ idCopied ? '✓' : '📋' }}
            </button>
          </div>
        </div>
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
        <button
          :class="['tab-btn', { active: activeTab === 'orders' }]"
          @click="activeTab = 'orders'"
        >
          财务记录
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
            <p>{{ formatMoney(currentCostTotal) }}</p>
          </div>
        </div>

        <div class="detail-row">
          <div class="detail-section">
            <label>总收入 (元)</label>
            <p>{{ formatMoney(currentRevenueTotal) }}</p>
          </div>
          <div class="detail-section">
            <label>净现金流 (元)</label>
            <p :class="currentRevenueTotal - currentCostTotal >= 0 ? 'profit' : 'loss'">
              {{ formatMoney(currentRevenueTotal - currentCostTotal) }}
            </p>
          </div>
        </div>
      </div>

      <!-- Timeline Tab -->
      <div v-else-if="activeTab === 'timeline'" class="modal-body timeline-body">
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

      <!-- Orders Tab -->
      <div v-else class="modal-body orders-body">
        <div class="orders-toolbar">
          <div class="orders-summary">
            <div class="summary-item">
              <span class="summary-label">记录数</span>
              <span class="summary-value">{{ orders.length }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">收入合计</span>
              <span class="summary-value revenue">¥{{ formatMoney(orderStats.totalIncome) }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">支出合计</span>
              <span class="summary-value cost">¥{{ formatMoney(orderStats.totalExpense) }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">净现金流</span>
              <span class="summary-value" :class="orderStats.net >= 0 ? 'profit' : 'loss'">
                ¥{{ formatMoney(orderStats.net) }}
              </span>
            </div>
          </div>
          <button class="btn btn-primary" @click="showOrderModal = true">新增记录</button>
        </div>

        <div v-if="orders.length === 0" class="orders-empty">
          <div class="empty-icon">🧾</div>
          <h3>暂无财务记录</h3>
          <p>可记录研发经费、服务器采购、服务收入等条目。</p>
        </div>

        <div v-else class="orders-table-wrap">
          <table class="orders-table">
            <thead>
              <tr>
                <th>事项</th>
                <th>类型</th>
                <th>金额</th>
                <th>记账时间</th>
                <th>备注</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in orders" :key="order.id">
                <td><div class="order-title">{{ order.title }}</div></td>
                <td>
                  <span class="badge" :class="order.kind === 'income' ? 'entry-income' : 'entry-expense'">
                    {{ order.kind === 'income' ? '收入' : '支出' }}
                  </span>
                </td>
                <td :class="order.kind === 'income' ? 'profit' : 'loss'">
                  {{ order.kind === 'income' ? '+' : '-' }}¥{{ formatMoney(order.amount) }}
                </td>
                <td>{{ formatDate(order.createdAt) }}</td>
                <td class="order-note">{{ order.note || '-' }}</td>
                <td>
                  <button class="btn btn-danger btn-xs" @click="removeOrder(order.id)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="modal-footer">
        <button @click="$emit('edit', project)" class="btn btn-primary">编辑</button>
        <button @click="handleDelete" class="btn btn-danger">删除</button>
      </div>
    </div>

    <OrderFormModal
      :show="showOrderModal"
      @close="showOrderModal = false"
      @save="handleSaveOrder"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useAgentStore } from '../stores/agent'
import { useProjectsStore } from '../stores/projects'
import { useToast } from '../composables/useToast'
import AgentTimeline from './timeline/AgentTimeline.vue'
import OrderFormModal from './OrderFormModal.vue'
import type { Project, OrderItem } from '../api/types'

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
const projectsStore = useProjectsStore()
const { showToast } = useToast()
const activeTab = ref<'details' | 'timeline' | 'orders'>('details')
const loadingTimeline = ref(false)
const timelineError = ref<string | null>(null)
const idCopied = ref(false)
const showOrderModal = ref(false)
const orders = ref<OrderItem[]>([])

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

const orderStats = computed(() => {
  return orders.value.reduce(
    (acc, order) => {
      const amount = Number(order.amount || 0)
      if (order.kind === 'income') {
        acc.totalIncome += amount
      } else {
        acc.totalExpense += amount
      }
      acc.net = acc.totalIncome - acc.totalExpense
      return acc
    },
    { totalIncome: 0, totalExpense: 0, net: 0 }
  )
})

const currentCostTotal = computed(() => {
  if (orders.value.length > 0) {
    return orderStats.value.totalExpense
  }
  return getActualCostValue(props.project)
})

const currentRevenueTotal = computed(() => {
  if (orders.value.length > 0) {
    return orderStats.value.totalIncome
  }
  return getRevenueValue(props.project)
})

watch(
  () => props.project,
  (project) => {
    const normalized = Array.isArray(project.orders) ? project.orders : []
    orders.value = normalized
      .map((item) => {
        const rawKind = String((item as { kind?: unknown }).kind || '')
        const legacyAmount = Number(item.amount || 0)
        const legacyCost = Number((item as { cost?: unknown }).cost || 0)
        const normalizedKind =
          rawKind === 'income' || rawKind === 'expense'
            ? rawKind
            : legacyCost > 0 && legacyAmount === 0
              ? 'expense'
              : 'income'
        const normalizedAmount =
          rawKind === 'income' || rawKind === 'expense'
            ? legacyAmount
            : normalizedKind === 'expense'
              ? (legacyCost > 0 ? legacyCost : legacyAmount)
              : legacyAmount

        return {
          id: String(item.id),
          title: String(item.title || ''),
          kind: normalizedKind,
          amount: Math.max(0, Number(normalizedAmount || 0)),
          createdAt: String(item.createdAt || new Date().toISOString()),
          note: item.note ? String(item.note) : undefined,
        }
      })
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt)) as OrderItem[]
  },
  { immediate: true, deep: true }
)

async function persistOrders(nextOrders: OrderItem[], successMessage: string) {
  try {
    const { totalIncome, totalExpense } = nextOrders.reduce(
      (acc, order) => {
        const amount = Number(order.amount || 0)
        if (order.kind === 'income') {
          acc.totalIncome += amount
        } else {
          acc.totalExpense += amount
        }
        return acc
      },
      { totalIncome: 0, totalExpense: 0 }
    )
    const updatedProject = await projectsStore.patchProject(props.project.id, {
      orders: nextOrders,
      revenueTotal: totalIncome,
      costTotal: totalExpense,
    })
    orders.value = (updatedProject.orders || []) as OrderItem[]
    showToast(successMessage, 'success')
  } catch (err) {
    console.error('Failed to save orders:', err)
    showToast('保存订单失败，请稍后重试', 'error')
  }
}

async function handleSaveOrder(order: OrderItem) {
  const nextOrders = [order, ...orders.value]
  orders.value = nextOrders
  showOrderModal.value = false
  await persistOrders(nextOrders, '记录已新增')
}

async function removeOrder(orderId: string) {
  const nextOrders = orders.value.filter((order) => order.id !== orderId)
  orders.value = nextOrders
  await persistOrders(nextOrders, '记录已删除')
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

function getRevenueValue(project: Project): number {
  const revenue = (project as { revenue?: { total?: unknown } }).revenue
  if (revenue && typeof revenue === 'object') {
    const num = Number(revenue.total)
    return Number.isFinite(num) ? num : 0
  }
  return 0
}

function handleDelete() {
  if (confirm(`确定要删除项目"${props.project.name}"吗？`)) {
    emit('delete', props.project.id)
  }
}

async function copyProjectId() {
  try {
    await navigator.clipboard.writeText(props.project.id)
    idCopied.value = true
    setTimeout(() => {
      idCopied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy project ID:', err)
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
  align-items: flex-start;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.header-content {
  flex: 1;
  padding-right: 16px;
}

.modal-header h2 {
  margin: 0 0 8px 0;
  font-size: 20px;
  color: var(--text-primary);
}

.project-id-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}

.project-id-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.project-id {
  font-family: 'SF Mono', 'Roboto Mono', 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-color);
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid var(--border-color);
}

.copy-id-btn {
  background: none;
  border: 1px solid var(--border-color);
  padding: 2px 6px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);
  transition: all 0.2s;
  line-height: 1;
}

.copy-id-btn:hover {
  background: var(--bg-color);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.copy-id-btn.copied {
  background: var(--success-color);
  border-color: var(--success-color);
  color: white;
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

.orders-body {
  padding: 20px 24px;
}

.orders-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.orders-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 10px;
  flex: 1;
}

.summary-item {
  padding: 10px 12px;
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 10px;
}

.summary-label {
  display: block;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  color: var(--text-muted);
  margin-bottom: 3px;
}

.summary-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.summary-value.revenue,
.profit {
  color: var(--success-color);
}

.summary-value.cost,
.loss {
  color: var(--danger-color);
}

.orders-empty {
  text-align: center;
  padding: 38px 18px;
  border: 1px dashed var(--border-color);
  border-radius: 12px;
  color: var(--text-secondary);
}

.orders-empty .empty-icon {
  font-size: 30px;
  margin-bottom: 8px;
}

.orders-empty h3 {
  margin: 0 0 6px;
  color: var(--text-primary);
}

.orders-empty p {
  margin: 0;
}

.orders-table-wrap {
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow-x: auto;
}

.orders-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 720px;
}

.orders-table th,
.orders-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
  color: var(--text-primary);
  vertical-align: top;
}

.orders-table th {
  background: var(--bg-color);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  font-size: 11px;
}

.orders-table tbody tr:last-child td {
  border-bottom: none;
}

.order-title {
  font-weight: 600;
}

.order-note {
  color: var(--text-muted);
  font-size: 12px;
  max-width: 280px;
}

.btn-xs {
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
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
.entry-income { background: #dcfce7; color: #166534; }
.entry-expense { background: #fee2e2; color: #991b1b; }

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

@media (max-width: 980px) {
  .orders-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .orders-summary {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }
}
</style>
