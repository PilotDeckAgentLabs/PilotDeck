<template>
  <div class="modal-overlay">
    <div class="modal-content ops-modal">
      <div class="modal-header">
        <h2>运维操作</h2>
        <button @click="closeModal" class="btn-close">×</button>
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
            @click="handleBackup"
            :disabled="!token || isRunning"
            class="btn btn-primary"
          >
            <span v-if="operation === 'backup' && isRunning" class="btn-spinner"></span>
            导出备份（下载）
          </button>

          <button
            @click="handleRestore"
            :disabled="!token || isRunning"
            class="btn btn-secondary"
          >
            <span v-if="operation === 'restore' && isRunning" class="btn-spinner"></span>
            从备份恢复
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

        <div v-if="output || statusType === 'running'" class="output-section">
          <label>部署日志</label>
          <pre class="output-content">{{ output || '等待日志...（服务重启期间可能短暂不可用）' }}</pre>
        </div>

        <div class="ops-info">
          <h4>操作说明</h4>
          <ul>
            <li><strong>导出备份:</strong> 生成一致性快照并下载（你可以自行存到任意位置）</li>
            <li><strong>从备份恢复:</strong> 上传备份文件覆盖当前数据库（恢复后建议刷新页面）</li>
            <li><strong>拉取并重启服务:</strong> 拉取代码更新、安装依赖并重启服务（用于部署）</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onUnmounted, ref } from 'vue'
import { opsDownloadBackup, opsRestoreFromBackup, opsPullRestart, opsGetDeployLog, opsGetDeployStatus } from '../api/client'
import { useToast } from '../composables/useToast'

const emit = defineEmits<{
  close: []
}>()

const { showToast } = useToast()

const token = ref('')
const isRunning = ref(false)
const operation = ref<'backup' | 'restore' | 'restart' | null>(null)
const statusType = ref<'idle' | 'running' | 'success' | 'error'>('idle')
const statusMessage = ref('')
const output = ref('')

let deployPollTimer: number | null = null
let deployPollHadError = false

function closeModal() {
  if (statusType.value === 'running') {
    const ok = confirm('部署仍在进行中，关闭后将停止日志轮询。确定关闭吗？')
    if (!ok) return
  }
  stopDeployPolling()
  emit('close')
}

function stopDeployPolling() {
  if (deployPollTimer) {
    window.clearInterval(deployPollTimer)
    deployPollTimer = null
  }
}

function startDeployPolling() {
  stopDeployPolling()
  deployPollHadError = false

  const pollOnce = async () => {
    if (!token.value) return
    try {
      const [st, log] = await Promise.all([
        opsGetDeployStatus(token.value),
        opsGetDeployLog(token.value),
      ])

      deployPollHadError = false

      if (log && Array.isArray(log.lines)) {
        output.value = log.lines.join('\n')
      }

      const state = st && st.data ? st.data.state : 'unknown'
      if (state === 'running') {
        statusType.value = 'running'
        statusMessage.value = '正在拉取更新并部署...'
        return
      }

      if (state === 'success') {
        statusType.value = 'success'
        statusMessage.value = '部署完成'
        stopDeployPolling()
        return
      }

      if (state === 'failed') {
        statusType.value = 'error'
        statusMessage.value = '部署失败'
        stopDeployPolling()
        return
      }
    } catch {
      // expected during restart: keep UI stable and show a one-time hint
      if (!deployPollHadError) {
        deployPollHadError = true
        statusType.value = 'running'
        statusMessage.value = '服务重启中，等待恢复连接...'
        if (!output.value) {
          output.value = '服务重启中，暂时无法获取日志。请稍候...'
        }
      }
    }
  }

  // Run immediately so users can see logs/status ASAP
  void pollOnce()

  deployPollTimer = window.setInterval(() => {
    void pollOnce()
  }, 1500)
}

onUnmounted(() => {
  stopDeployPolling()
})

async function handleBackup() {
  if (!token.value) {
    showToast('请输入访问令牌', 'error')
    return
  }

  isRunning.value = true
  operation.value = 'backup'
  statusType.value = 'running'
  statusMessage.value = '正在生成备份并下载...'
  output.value = ''

  try {
    const { blob, filename } = await opsDownloadBackup(token.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)

    statusType.value = 'success'
    statusMessage.value = '备份已下载'
    output.value = `下载完成: ${filename}`
    showToast('备份已下载', 'success')
  } catch (err: any) {
    statusType.value = 'error'
    statusMessage.value = '备份失败'
    output.value = err.message || String(err)
    showToast('备份失败', 'error')
  } finally {
    isRunning.value = false
    operation.value = null
  }
}

async function handleRestore() {
  if (!token.value) {
    showToast('请输入访问令牌', 'error')
    return
  }

  if (!confirm('将从备份文件恢复数据库。该操作会覆盖当前数据，且可能导致正在使用的页面短暂错误。确定继续吗？')) {
    return
  }

  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.db,application/octet-stream'
  input.onchange = async () => {
    const file = input.files && input.files[0] ? input.files[0] : null
    if (!file) return

    isRunning.value = true
    operation.value = 'restore'
    statusType.value = 'running'
    statusMessage.value = '正在上传备份并恢复...'
    output.value = ''

    try {
      const res = await opsRestoreFromBackup(token.value, file)
      statusType.value = 'success'
      statusMessage.value = '恢复完成（建议刷新页面）'
      output.value = JSON.stringify(res, null, 2)
      showToast('恢复完成', 'success')
    } catch (err: any) {
      statusType.value = 'error'
      statusMessage.value = '恢复失败'
      output.value = err.message || String(err)
      showToast('恢复失败', 'error')
    } finally {
      isRunning.value = false
      operation.value = null
    }
  }

  input.click()
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
    statusMessage.value = '已触发部署（服务会短暂重启）'
    output.value = `已触发部署。\n\n${JSON.stringify(result, null, 2)}`
    showToast('已触发部署', 'success')

    statusType.value = 'running'
    statusMessage.value = '正在拉取更新并部署...'
    startDeployPolling()
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
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-secondary);
  border-color: var(--text-secondary);
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
