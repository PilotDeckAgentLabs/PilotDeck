<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content ops-modal">
      <div class="modal-header">
        <h2>运维操作</h2>
        <button @click="$emit('close')" class="btn-close">×</button>
      </div>

      <div class="modal-body">
        <div class="ops-section">
          <label for="token-input">访问令牌</label>
          <input
            id="token-input"
            v-model="token"
            type="password"
            class="form-input"
            placeholder="请输入访问令牌"
            :disabled="isRunning"
          />
        </div>

        <div class="ops-actions">
          <button
            @click="handlePushData"
            :disabled="!token || isRunning"
            class="btn btn-primary"
          >
            <span v-if="operation === 'push' && isRunning" class="btn-spinner"></span>
            推送数据到 GitHub
          </button>

          <button
            @click="handlePullData"
            :disabled="!token || isRunning"
            class="btn btn-secondary"
          >
            <span v-if="operation === 'pull' && isRunning" class="btn-spinner"></span>
            拉取数据仓库
          </button>

          <button
            @click="handlePullRestart"
            :disabled="!token || isRunning"
            class="btn btn-warning"
          >
            <span v-if="operation === 'restart' && isRunning" class="btn-spinner"></span>
            拉取并重启服务
          </button>
        </div>

        <div v-if="statusMessage" class="status-indicator" :class="statusType">
          <div class="status-icon">
            <span v-if="statusType === 'running'">⏳</span>
            <span v-else-if="statusType === 'success'">✓</span>
            <span v-else-if="statusType === 'error'">✗</span>
            <span v-else>ℹ</span>
          </div>
          <div class="status-message">{{ statusMessage }}</div>
        </div>

        <div v-if="output" class="output-section">
          <label>输出</label>
          <pre class="output-content">{{ output }}</pre>
        </div>

        <div class="ops-info">
          <h4>操作说明</h4>
          <ul>
            <li><strong>推送数据到 GitHub:</strong> 将本地数据变更提交并推送到数据仓库</li>
            <li><strong>拉取数据仓库:</strong> 从数据仓库拉取最新数据</li>
            <li><strong>拉取并重启服务:</strong> 拉取代码更新、安装依赖并重启服务（用于部署）</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { opsPushData, opsPullDataRepo, opsPullRestart } from '../api/client'
import { useToast } from '../composables/useToast'

const emit = defineEmits<{
  close: []
}>()

const { showToast } = useToast()

const token = ref('')
const isRunning = ref(false)
const operation = ref<'push' | 'pull' | 'restart' | null>(null)
const statusType = ref<'idle' | 'running' | 'success' | 'error'>('idle')
const statusMessage = ref('')
const output = ref('')

async function handlePushData() {
  if (!token.value) {
    showToast('请输入访问令牌', 'error')
    return
  }

  isRunning.value = true
  operation.value = 'push'
  statusType.value = 'running'
  statusMessage.value = '正在推送数据到 GitHub...'
  output.value = ''

  try {
    const result = await opsPushData(token.value)
    statusType.value = 'success'
    statusMessage.value = '数据推送成功'
    output.value = result.output || '操作完成'
    showToast('数据已推送到 GitHub', 'success')
  } catch (err: any) {
    statusType.value = 'error'
    statusMessage.value = '数据推送失败'
    output.value = err.message || String(err)
    showToast('数据推送失败', 'error')
  } finally {
    isRunning.value = false
    operation.value = null
  }
}

async function handlePullData() {
  if (!token.value) {
    showToast('请输入访问令牌', 'error')
    return
  }

  isRunning.value = true
  operation.value = 'pull'
  statusType.value = 'running'
  statusMessage.value = '正在拉取数据仓库...'
  output.value = ''

  try {
    const result = await opsPullDataRepo(token.value)
    statusType.value = 'success'
    statusMessage.value = '数据拉取成功'
    output.value = result.output || '操作完成'
    showToast('数据已从 GitHub 拉取', 'success')
  } catch (err: any) {
    statusType.value = 'error'
    statusMessage.value = '数据拉取失败'
    output.value = err.message || String(err)
    showToast('数据拉取失败', 'error')
  } finally {
    isRunning.value = false
    operation.value = null
  }
}

async function handlePullRestart() {
  if (!token.value) {
    showToast('请输入访问令牌', 'error')
    return
  }

  if (!confirm('此操作将拉取代码更新并重启服务，确定继续吗？')) {
    return
  }

  isRunning.value = true
  operation.value = 'restart'
  statusType.value = 'running'
  statusMessage.value = '正在拉取代码并重启服务...'
  output.value = ''

  try {
    const result = await opsPullRestart(token.value)
    statusType.value = 'success'
    statusMessage.value = '服务重启成功'
    output.value = result.output || '操作完成'
    showToast('服务已重启', 'success')

    // Give server time to restart then close modal
    setTimeout(() => {
      emit('close')
    }, 2000)
  } catch (err: any) {
    statusType.value = 'error'
    statusMessage.value = '服务重启失败'
    output.value = err.message || String(err)
    showToast('服务重启失败', 'error')
  } finally {
    isRunning.value = false
    operation.value = null
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
  overflow-y: auto;
}

.ops-modal {
  max-width: 700px;
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

.modal-body {
  padding: 24px;
}

.ops-section {
  margin-bottom: 24px;
}

.ops-section label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--input-bg);
  color: var(--text-primary);
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.form-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ops-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.btn {
  padding: 12px 20px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn-secondary {
  background: var(--secondary-color);
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #059669;
}

.btn-warning {
  background: #f59e0b;
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background: #d97706;
}

.btn-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.status-indicator {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.status-indicator.idle {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
}

.status-indicator.running {
  background: #dbeafe;
  border: 1px solid #93c5fd;
}

.status-indicator.success {
  background: #d1fae5;
  border: 1px solid #6ee7b7;
}

.status-indicator.error {
  background: #fee2e2;
  border: 1px solid #fca5a5;
}

.status-icon {
  font-size: 20px;
  line-height: 1;
}

.status-message {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.5;
}

.output-section {
  margin-bottom: 24px;
}

.output-section label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.output-content {
  margin: 0;
  padding: 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 12px;
  font-family: 'Courier New', monospace;
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 300px;
  overflow-y: auto;
}

.ops-info {
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.ops-info h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: var(--text-primary);
}

.ops-info ul {
  margin: 0;
  padding-left: 20px;
}

.ops-info li {
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.ops-info strong {
  color: var(--text-primary);
}
</style>
