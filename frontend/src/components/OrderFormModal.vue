<template>
  <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>创建订单</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <form @submit.prevent="handleSubmit" class="order-form">
        <div class="form-row">
          <div class="form-group">
            <label for="orderTitle">订单名称 <span class="required">*</span></label>
            <input id="orderTitle" v-model.trim="form.title" type="text" required placeholder="如：企业官网定制项目" />
          </div>
          <div class="form-group">
            <label for="orderCustomer">客户名称 <span class="required">*</span></label>
            <input id="orderCustomer" v-model.trim="form.customer" type="text" required placeholder="如：某科技有限公司" />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="orderAmount">订单金额（元）<span class="required">*</span></label>
            <input id="orderAmount" v-model.number="form.amount" type="number" min="0" step="0.01" required />
          </div>
          <div class="form-group">
            <label for="orderCost">预计成本（元）<span class="required">*</span></label>
            <input id="orderCost" v-model.number="form.cost" type="number" min="0" step="0.01" required />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="orderStatus">订单状态</label>
            <select id="orderStatus" v-model="form.status">
              <option value="pending">待确认</option>
              <option value="confirmed">已确认</option>
              <option value="delivered">交付中</option>
              <option value="completed">已完成</option>
              <option value="cancelled">已取消</option>
            </select>
          </div>
          <div class="form-group">
            <label for="orderDueDate">交付日期</label>
            <input id="orderDueDate" v-model="form.dueDate" type="date" />
          </div>
        </div>

        <div class="form-group">
          <label for="orderNote">订单备注</label>
          <textarea id="orderNote" v-model.trim="form.note" rows="3" placeholder="补充交付范围、回款节点等"></textarea>
        </div>

        <div class="preview">
          <span class="preview-label">预估毛利</span>
          <span class="preview-value" :class="profit >= 0 ? 'profit' : 'loss'">
            ¥{{ formatMoney(profit) }}
          </span>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" @click="$emit('close')">取消</button>
          <button type="submit" class="btn btn-primary">创建订单</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { OrderItem, OrderStatus } from '../api/types'

defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  close: []
  save: [order: OrderItem]
}>()

const form = ref<{
  title: string
  customer: string
  amount: number
  cost: number
  status: OrderStatus
  dueDate: string
  note: string
}>({
  title: '',
  customer: '',
  amount: 0,
  cost: 0,
  status: 'pending',
  dueDate: '',
  note: '',
})

const profit = computed(() => Number(form.value.amount || 0) - Number(form.value.cost || 0))

function formatMoney(value: number): string {
  return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function resetForm() {
  form.value = {
    title: '',
    customer: '',
    amount: 0,
    cost: 0,
    status: 'pending',
    dueDate: '',
    note: '',
  }
}

function createOrderId(): string {
  return `ord-${Math.random().toString(36).slice(2, 10)}`
}

function handleSubmit() {
  const title = form.value.title.trim()
  const customer = form.value.customer.trim()
  const amount = Number(form.value.amount || 0)
  const cost = Number(form.value.cost || 0)

  if (!title || !customer || amount < 0 || cost < 0) {
    return
  }

  emit('save', {
    id: createOrderId(),
    title,
    customer,
    amount,
    cost,
    status: form.value.status,
    createdAt: new Date().toISOString(),
    dueDate: form.value.dueDate || undefined,
    note: form.value.note.trim() || undefined,
  })

  resetForm()
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
  padding: 20px;
}

.modal-content {
  width: 100%;
  max-width: 680px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-lg);
  backdrop-filter: var(--backdrop-blur);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
  color: var(--text-muted);
  line-height: 1;
  cursor: pointer;
  width: 30px;
  height: 30px;
  border-radius: 6px;
}

.close-btn:hover {
  background: var(--bg-color);
  color: var(--text-primary);
}

.order-form {
  padding: 24px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 14px;
}

.form-group {
  margin-bottom: 14px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.required {
  color: var(--danger-color);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--card-bg);
  color: var(--text-primary);
  padding: 9px 12px;
  font-size: 14px;
  font-family: inherit;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(17, 24, 39, 0.08);
}

.preview {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid var(--border-color);
  background: var(--bg-color);
  border-radius: 10px;
  padding: 10px 12px;
}

.preview-label {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.preview-value {
  font-size: 18px;
  font-weight: 700;
}

.preview-value.profit {
  color: var(--success-color);
}

.preview-value.loss {
  color: var(--danger-color);
}

.modal-actions {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn {
  padding: 10px 18px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.btn-secondary {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--bg-color);
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-hover);
}

@media (max-width: 740px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
