<template>
  <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>新增财务记录</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <form @submit.prevent="handleSubmit" class="order-form">
        <div class="form-group">
          <label for="orderTitle">记录名称 <span class="required">*</span></label>
          <input id="orderTitle" v-model.trim="form.title" type="text" required placeholder="如：研发经费 / 购买云服务器 / 服务收入" />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="orderType">类型 <span class="required">*</span></label>
            <select id="orderType" v-model="form.kind">
              <option value="income">收入</option>
              <option value="expense">支出</option>
            </select>
          </div>
          <div class="form-group">
            <label for="orderAmount">金额（元）<span class="required">*</span></label>
            <input id="orderAmount" v-model.number="form.amount" type="number" min="0" step="0.01" required />
          </div>
        </div>

        <div class="form-group">
          <label for="orderDate">记账日期</label>
          <input id="orderDate" v-model="form.date" type="date" />
        </div>

        <div class="form-group">
          <label for="orderNote">备注</label>
          <textarea id="orderNote" v-model.trim="form.note" rows="3" placeholder="可填写来源、用途、审批编号等"></textarea>
        </div>

        <div class="preview">
          <span class="preview-label">本次影响</span>
          <span class="preview-value" :class="previewAmount >= 0 ? 'profit' : 'loss'">
            {{ previewAmount >= 0 ? '+' : '-' }}¥{{ formatMoney(Math.abs(previewAmount)) }}
          </span>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" @click="$emit('close')">取消</button>
          <button type="submit" class="btn btn-primary">保存记录</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { OrderItem, OrderKind } from '../api/types'

defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  close: []
  save: [order: OrderItem]
}>()

const form = ref<{
  title: string
  kind: OrderKind
  amount: number
  date: string
  note: string
}>({
  title: '',
  kind: 'expense',
  amount: 0,
  date: new Date().toISOString().slice(0, 10),
  note: '',
})

const previewAmount = computed(() => {
  const amount = Number(form.value.amount || 0)
  return form.value.kind === 'income' ? amount : -amount
})

function formatMoney(value: number): string {
  return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function resetForm() {
  form.value = {
    title: '',
    kind: 'expense',
    amount: 0,
    date: new Date().toISOString().slice(0, 10),
    note: '',
  }
}

function createOrderId(): string {
  return `ord-${Math.random().toString(36).slice(2, 10)}`
}

function handleSubmit() {
  const title = form.value.title.trim()
  const amount = Number(form.value.amount || 0)

  if (!title || amount < 0) {
    return
  }

  const parsedDate = form.value.date ? new Date(`${form.value.date}T00:00:00`) : new Date()
  const createdAt = Number.isNaN(parsedDate.getTime()) ? new Date().toISOString() : parsedDate.toISOString()

  emit('save', {
    id: createOrderId(),
    title,
    kind: form.value.kind,
    amount,
    createdAt,
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
