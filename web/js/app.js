// Project Manager Web App (vanilla JS)

// Same-origin API (works on any host/port).
const API_BASE_URL = '/api'

let currentProjects = []
let sortMode = 'manual'
let currentDetailProjectId = null
let opsLogTimer = null
let opsLastLogText = ''
let opsLastLogLines = []
let opsPollFailCount = 0
let opsPollDelayMs = 1500
let opsPolling = false
let opsLastTransientNoteAt = 0

const STATUS_LABELS = {
  'planning': '计划中',
  'in-progress': '进行中',
  'paused': '暂停',
  'completed': '已完成',
  'cancelled': '已取消',
}

const PRIORITY_LABELS = {
  'low': '低',
  'medium': '中',
  'high': '高',
  'urgent': '紧急',
}

function $(id) {
  return document.getElementById(id)
}

function showLoading(show) {
  $('loading').style.display = show ? 'block' : 'none'
}

function showEmptyState(show) {
  $('emptyState').style.display = show ? 'block' : 'none'
}

function showToast(message, type = 'success') {
  const toast = $('toast')
  toast.textContent = message
  toast.className = `toast show ${type}`
  window.clearTimeout(showToast._t)
  showToast._t = window.setTimeout(() => {
    toast.className = 'toast'
  }, 2400)
}

async function apiFetch(path, options = {}) {
  const url = `${API_BASE_URL}${path}`
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  const text = await res.text()
  let json
  try {
    json = text ? JSON.parse(text) : null
  } catch (e) {
    json = null
  }

  if (!res.ok) {
    const errMsg = (json && (json.error || json.message)) || `HTTP ${res.status}`
    const outRaw = (json && json.output) ? String(json.output || '') : ''
    const out = outRaw ? outRaw.split('\n').slice(-80).join('\n').trim() : ''
    throw new Error(out ? `${errMsg}\n${out}` : errMsg)
  }
  return json
}

function getOpsToken() {
  const el = $('opsToken')
  const v = el ? String(el.value || '').trim() : ''
  return v
}

function setOpsOutput(text) {
  const el = $('opsOutput')
  if (!el) return
  el.textContent = String(text || '')
}

function appendOpsOutput(text) {
  const el = $('opsOutput')
  if (!el) return
  el.textContent = `${el.textContent || ''}${String(text || '')}`
}

function setOpsDeployStatus(kind, text) {
  const el = $('opsDeployStatus')
  if (!el) return
  el.className = `ops-status ops-status-${kind}`
  el.textContent = String(text || '')
}

function nowMs() {
  return Date.now()
}

function clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n))
}

function isTransientOpsError(e) {
  const msg = String((e && e.message) || '')
  if (msg.startsWith('HTTP 502')) return true
  if (msg.startsWith('HTTP 503')) return true
  if (msg.startsWith('HTTP 504')) return true
  if (msg.toLowerCase().includes('failed to fetch')) return true
  return false
}

function shouldStopPollingOnError(e) {
  const msg = String((e && e.message) || '')
  // Wrong token / not configured: stop spamming.
  if (msg === 'Unauthorized') return true
  if (msg.toLowerCase().includes('admin token not configured')) return true
  return false
}

function computeLineDelta(oldLines, newLines) {
  const a = Array.isArray(oldLines) ? oldLines : []
  const b = Array.isArray(newLines) ? newLines : []
  if (a.length === 0) return { mode: 'replace', lines: b }
  if (b.length === 0) return { mode: 'replace', lines: b }

  const maxK = Math.min(a.length, b.length)
  for (let k = maxK; k >= 1; k -= 1) {
    let ok = true
    for (let i = 0; i < k; i += 1) {
      if (a[a.length - k + i] !== b[i]) {
        ok = false
        break
      }
    }
    if (ok) {
      return { mode: 'append', lines: b.slice(k) }
    }
  }

  // No overlap found; replace.
  return { mode: 'replace', lines: b }
}

async function opsFetch(path, options = {}) {
  const token = getOpsToken()
  if (!token) throw new Error('请先填写管理口令（PM_ADMIN_TOKEN）')
  const headers = {
    ...(options.headers || {}),
    'X-PM-Token': token,
  }
  return apiFetch(path, { ...options, headers })
}

function buildQuery(params) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && String(v).trim() !== '') q.set(k, v)
  })
  const s = q.toString()
  return s ? `?${s}` : ''
}

function escapeHtml(s) {
  return String(s || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function formatMoneyCny(n) {
  if (n === null || n === undefined || n === '') return ''
  const v = Number(n)
  if (Number.isNaN(v)) return ''
  return `¥${v.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`
}

function statusBadgeClass(status) {
  return `badge badge-${status || 'planning'}`
}

function priorityBadgeClass(priority) {
  return `badge badge-${priority || 'medium'}`
}

function priorityRank(priority) {
  const v = String(priority || '').trim()
  if (v === 'urgent') return 0
  if (v === 'high') return 1
  if (v === 'medium') return 2
  if (v === 'low') return 3
  return 9
}

function getCostTotal(p) {
  const n = p && p.cost && typeof p.cost.total === 'number' ? p.cost.total : 0
  return Number.isFinite(n) ? n : 0
}

function getRevenueTotal(p) {
  const n = p && p.revenue && typeof p.revenue.total === 'number' ? p.revenue.total : 0
  return Number.isFinite(n) ? n : 0
}

function setSaving(el, saving) {
  if (!el) return
  if (saving) {
    el.classList.add('pm-saving')
    el.disabled = true
  } else {
    el.classList.remove('pm-saving')
    el.disabled = false
  }
}

function findProjectById(projectId) {
  return (currentProjects || []).find(p => p && p.id === projectId) || null
}

async function updateProjectPartial(projectId, patch) {
  const res = await apiFetch(`/projects/${encodeURIComponent(projectId)}`, {
    method: 'PUT',
    body: JSON.stringify(patch),
  })
  const updated = res && res.data
  if (!updated) return
  const idx = (currentProjects || []).findIndex(p => p && p.id === projectId)
  if (idx >= 0) currentProjects[idx] = updated
}

function renderProjects(projects) {
  const list = $('projectsList')
  list.innerHTML = ''

  if (!projects || projects.length === 0) {
    showEmptyState(true)
    return
  }
  showEmptyState(false)

  const displayProjects = (projects || []).slice()
  if (sortMode === 'priority') {
    displayProjects.sort((a, b) => {
      const pr = priorityRank(a && a.priority) - priorityRank(b && b.priority)
      if (pr !== 0) return pr
      const an = String((a && a.name) || '')
      const bn = String((b && b.name) || '')
      return an.localeCompare(bn, 'zh-CN')
    })
  }

  const table = document.createElement('table')
  table.className = 'pm-table'

  const thead = document.createElement('thead')
  thead.innerHTML = `
    <tr>
      <th class="pm-col-drag"></th>
      <th>项目</th>
      <th>状态</th>
      <th>优先级</th>
      <th class="pm-col-num">进度%</th>
      <th class="pm-col-num">成本</th>
      <th class="pm-col-num">收入</th>
      <th class="pm-col-actions">操作</th>
    </tr>
  `.trim()
  table.appendChild(thead)

  const tbody = document.createElement('tbody')

  function makeSelect(options, value) {
    const sel = document.createElement('select')
    sel.className = 'pm-cell-input'
    options.forEach(([v, label]) => {
      const opt = document.createElement('option')
      opt.value = v
      opt.textContent = label
      sel.appendChild(opt)
    })
    sel.value = value
    return sel
  }

  displayProjects.forEach((p) => {
    const tr = document.createElement('tr')
    tr.setAttribute('data-id', p.id)
    if (sortMode === 'manual') tr.draggable = true

    const dragTd = document.createElement('td')
    dragTd.className = 'pm-drag'
    dragTd.textContent = sortMode === 'manual' ? '⋮⋮' : ''
    dragTd.title = sortMode === 'manual' ? '拖动排序' : ''
    tr.appendChild(dragTd)

    const nameTd = document.createElement('td')
    const nameInput = document.createElement('input')
    nameInput.className = 'pm-cell-input'
    nameInput.type = 'text'
    nameInput.value = p.name || ''
    nameInput.setAttribute('data-field', 'name')
    nameTd.appendChild(nameInput)
    tr.appendChild(nameTd)

    const statusTd = document.createElement('td')
    const statusSel = makeSelect([
      ['planning', '计划中'],
      ['in-progress', '进行中'],
      ['paused', '暂停'],
      ['completed', '已完成'],
      ['cancelled', '已取消'],
    ], p.status || 'planning')
    statusSel.setAttribute('data-field', 'status')
    statusTd.appendChild(statusSel)
    tr.appendChild(statusTd)

    const priorityTd = document.createElement('td')
    const prioritySel = makeSelect([
      ['low', '低'],
      ['medium', '中'],
      ['high', '高'],
      ['urgent', '紧急'],
    ], p.priority || 'medium')
    prioritySel.setAttribute('data-field', 'priority')
    priorityTd.appendChild(prioritySel)
    tr.appendChild(priorityTd)

    const progressTd = document.createElement('td')
    const progressInput = document.createElement('input')
    progressInput.className = 'pm-cell-input pm-num'
    progressInput.type = 'number'
    progressInput.min = '0'
    progressInput.max = '100'
    progressInput.step = '1'
    progressInput.value = String(Number(p.progress || 0))
    progressInput.setAttribute('data-field', 'progress')
    progressTd.appendChild(progressInput)
    tr.appendChild(progressTd)

    const costTd = document.createElement('td')
    const costInput = document.createElement('input')
    costInput.className = 'pm-cell-input pm-num'
    costInput.type = 'number'
    costInput.min = '0'
    costInput.step = '0.01'
    costInput.value = String(getCostTotal(p))
    costInput.setAttribute('data-field', 'costTotal')
    costTd.appendChild(costInput)
    tr.appendChild(costTd)

    const revenueTd = document.createElement('td')
    const revenueInput = document.createElement('input')
    revenueInput.className = 'pm-cell-input pm-num'
    revenueInput.type = 'number'
    revenueInput.min = '0'
    revenueInput.step = '0.01'
    revenueInput.value = String(getRevenueTotal(p))
    revenueInput.setAttribute('data-field', 'revenueTotal')
    revenueTd.appendChild(revenueInput)
    tr.appendChild(revenueTd)

    const actionsTd = document.createElement('td')
    actionsTd.className = 'pm-actions'
    const detailBtn = document.createElement('button')
    detailBtn.className = 'btn btn-secondary btn-small'
    detailBtn.type = 'button'
    detailBtn.textContent = '详情'
    detailBtn.setAttribute('data-action', 'detail')
    const delBtn = document.createElement('button')
    delBtn.className = 'btn btn-danger btn-small'
    delBtn.type = 'button'
    delBtn.textContent = '删除'
    delBtn.setAttribute('data-action', 'delete')
    actionsTd.appendChild(detailBtn)
    actionsTd.appendChild(delBtn)
    tr.appendChild(actionsTd)

    tbody.appendChild(tr)
  })

  table.appendChild(tbody)
  list.appendChild(table)

  table.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return
    const el = e.target
    if (!el || !el.getAttribute) return
    if (!el.getAttribute('data-field')) return
    e.preventDefault()
    el.blur()
  }, true)

  async function commitField(el) {
    const field = el.getAttribute('data-field')
    const tr = el.closest('tr[data-id]')
    if (!field || !tr) return
    const projectId = tr.getAttribute('data-id')
    const p = findProjectById(projectId)
    if (!p) return

    let patch = null
    if (field === 'name') {
      const v = String(el.value || '').trim()
      if (!v) {
        showToast('项目名称不能为空', 'error')
        el.value = p.name || ''
        return
      }
      if (v === (p.name || '')) return
      patch = { name: v }
    } else if (field === 'status') {
      const v = String(el.value || '').trim()
      if (v === (p.status || 'planning')) return
      patch = { status: v }
    } else if (field === 'priority') {
      const v = String(el.value || '').trim()
      if (v === (p.priority || 'medium')) return
      patch = { priority: v }
    } else if (field === 'progress') {
      const v = Number(el.value)
      if (Number.isNaN(v) || v < 0 || v > 100) {
        showToast('进度必须在0-100之间', 'error')
        el.value = String(Number(p.progress || 0))
        return
      }
      if (v === Number(p.progress || 0)) return
      patch = { progress: v }
    } else if (field === 'costTotal') {
      const v = Number(el.value)
      if (Number.isNaN(v) || v < 0) {
        showToast('成本必须是非负数字', 'error')
        el.value = String(getCostTotal(p))
        return
      }
      if (v === getCostTotal(p)) return
      patch = { cost: { ...(p.cost || {}), total: v } }
    } else if (field === 'revenueTotal') {
      const v = Number(el.value)
      if (Number.isNaN(v) || v < 0) {
        showToast('收入必须是非负数字', 'error')
        el.value = String(getRevenueTotal(p))
        return
      }
      if (v === getRevenueTotal(p)) return
      patch = { revenue: { ...(p.revenue || {}), total: v } }
    }

    if (!patch) return
    try {
      setSaving(el, true)
      await updateProjectPartial(projectId, patch)
    } catch (e) {
      showToast(`保存失败: ${e.message}`, 'error')
      await loadProjects()
    } finally {
      setSaving(el, false)
    }
  }

  table.addEventListener('change', (e) => {
    const el = e.target
    if (!el || !el.getAttribute) return
    if (!el.getAttribute('data-field')) return
    commitField(el)
  }, true)

  table.addEventListener('blur', (e) => {
    const el = e.target
    if (!el || !el.getAttribute) return
    if (!el.getAttribute('data-field')) return
    commitField(el)
  }, true)

  table.addEventListener('click', (e) => {
    const btn = e.target && e.target.closest && e.target.closest('button[data-action]')
    if (!btn) return
    const tr = btn.closest('tr[data-id]')
    if (!tr) return
    const id = tr.getAttribute('data-id')
    const action = btn.getAttribute('data-action')
    if (action === 'detail') {
      e.preventDefault()
      e.stopPropagation()
      showProjectDetail(id)
    } else if (action === 'delete') {
      e.preventDefault()
      e.stopPropagation()
      deleteProject(id)
    }
  })

  // Drag & drop ordering (manual mode only)
  let draggedId = null
  tbody.addEventListener('dragstart', (e) => {
    if (sortMode !== 'manual') return
    const tr = e.target && e.target.closest && e.target.closest('tr[data-id]')
    if (!tr) return
    draggedId = tr.getAttribute('data-id')
    tr.classList.add('pm-dragging')
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = 'move'
      e.dataTransfer.setData('text/plain', draggedId)
    }
  })

  tbody.addEventListener('dragend', (e) => {
    const tr = e.target && e.target.closest && e.target.closest('tr[data-id]')
    if (tr) tr.classList.remove('pm-dragging')
    draggedId = null
  })

  tbody.addEventListener('dragover', (e) => {
    if (sortMode !== 'manual') return
    if (!draggedId) return
    e.preventDefault()
    const over = e.target && e.target.closest && e.target.closest('tr[data-id]')
    const dragging = draggedId ? tbody.querySelector(`tr[data-id="${CSS.escape(draggedId)}"]`) : null
    if (!over || !dragging || over === dragging) return
    const rect = over.getBoundingClientRect()
    const before = e.clientY < rect.top + rect.height / 2
    tbody.insertBefore(dragging, before ? over : over.nextSibling)
  })

  tbody.addEventListener('drop', async (e) => {
    if (sortMode !== 'manual') return
    if (!draggedId) return
    e.preventDefault()
    const ids = Array.from(tbody.querySelectorAll('tr[data-id]')).map(r => r.getAttribute('data-id'))
    try {
      const res = await apiFetch('/projects/reorder', {
        method: 'POST',
        body: JSON.stringify({ ids }),
      })
      currentProjects = (res && res.data) || currentProjects
      renderProjects(currentProjects)
    } catch (err) {
      showToast(`排序保存失败: ${err.message}`, 'error')
      await loadProjects()
    }
  })
}

async function loadProjects() {
  showLoading(true)
  try {
    const status = $('statusFilter').value
    const priority = $('priorityFilter').value

    const query = buildQuery({ status, priority })
    const res = await apiFetch(`/projects${query}`)
    currentProjects = (res && res.data) || []
    renderProjects(currentProjects)
  } catch (e) {
    showToast(`加载失败: ${e.message}`, 'error')
  } finally {
    showLoading(false)
  }
}

function applyFilters() {
  loadProjects()
}

function applySortMode() {
  const sel = $('sortMode')
  sortMode = (sel && sel.value) ? sel.value : 'manual'
  renderProjects(currentProjects)
}

function resetProjectForm() {
  $('projectForm').reset()
  $('projectStatus').value = 'planning'
  $('projectPriority').value = 'medium'
  $('projectProgress').value = '0'
  $('projectCostTotal').value = '0'
  $('projectRevenueTotal').value = '0'
  $('modalTitle').textContent = '添加项目'
}

function openModal(modalId) {
  const m = $(modalId)
  m.classList.add('show')
}

function closeModal(modalId) {
  const m = $(modalId)
  m.classList.remove('show')
}

function openOpsModal() {
  setOpsOutput('')
  opsLastLogText = ''
  opsLastLogLines = []
  opsPollFailCount = 0
  opsPollDelayMs = 1500
  opsPolling = false
  opsLastTransientNoteAt = 0
  setOpsDeployStatus('idle', '未开始部署')
  openModal('opsModal')
}

function closeOpsModal() {
  opsStopDeployLog()
  closeModal('opsModal')
}

function opsStartDeployLog() {
  opsStopDeployLog()
  opsPolling = true
  opsPollFailCount = 0
  opsPollDelayMs = 1500
  setOpsDeployStatus('running', '正在获取部署日志...（服务重启期间可能短暂不可用，将自动重连）')

  const tick = async () => {
    if (!opsPolling) return
    try {
      // 先拉日志：用户更关心“发生了什么”。
      await opsFetchDeployLog()

      // 再拿状态：决定是否结束轮询。
      const st = await opsFetchDeployStatus()
      const state = st && st.state ? st.state : 'unknown'
      if (state === 'success') {
        setOpsDeployStatus('success', '部署完成：成功。建议刷新页面确认功能正常。')
        appendOpsOutput('\n[INFO] Deploy status: success\n')
        showToast('部署成功', 'success')
        opsStopDeployLog()
        return
      }
      if (state === 'failed') {
        let hint = '部署完成：失败。请查看日志末尾的错误信息。'
        const log = String(opsLastLogText || '')
        if (log.includes('cannot pull with rebase') || log.includes('You have unstaged changes')) {
          hint = '部署失败：服务器代码仓库有未提交修改，无法 git pull --rebase。请先在服务器上提交/暂存这些代码修改后再试。'
        }
        setOpsDeployStatus('failed', hint)
        appendOpsOutput('\n[ERROR] Deploy status: failed\n')
        showToast('部署失败（查看运维日志）', 'error')
        opsStopDeployLog()
        return
      }

      // 正常情况：保持较快轮询。
      opsPollFailCount = 0
      opsPollDelayMs = 1500
    } catch (e) {
      if (shouldStopPollingOnError(e)) {
        appendOpsOutput(`\n[WARN] 日志刷新停止: ${e.message}\n`)
        setOpsDeployStatus('failed', `无法继续获取日志：${e.message}`)
        opsStopDeployLog()
        return
      }

      if (isTransientOpsError(e)) {
        setOpsDeployStatus('restarting', '服务重启中，正在等待恢复连接...（通常 10-30 秒）')
        const t = nowMs()
        if (t - opsLastTransientNoteAt > 6000) {
          appendOpsOutput(`\n[INFO] 服务重启中，等待恢复连接... (${e.message})\n`)
          opsLastTransientNoteAt = t
        }
        opsPollFailCount += 1
        opsPollDelayMs = clamp(1500 * (2 ** Math.min(opsPollFailCount, 3)), 1500, 10000)
      } else {
        appendOpsOutput(`\n[WARN] 日志获取失败: ${e.message}\n`)
        opsPollFailCount += 1
        opsPollDelayMs = clamp(1500 * (2 ** Math.min(opsPollFailCount, 3)), 1500, 10000)
      }
    } finally {
      if (!opsPolling) return
      opsLogTimer = window.setTimeout(tick, opsPollDelayMs)
    }
  }

  tick().catch(() => {})
}

function opsStopDeployLog() {
  opsPolling = false
  if (opsLogTimer) {
    window.clearTimeout(opsLogTimer)
    opsLogTimer = null
  }
}

async function opsPushData() {
  try {
    setOpsOutput('[INFO] Pushing data repo changes to GitHub...\n')
    const res = await opsFetch('/admin/push', {
      method: 'POST',
      body: JSON.stringify({ mode: 'data-only' }),
    })
    appendOpsOutput((res && res.output) ? `${res.output}\n` : '[INFO] Done.\n')
  } catch (e) {
    appendOpsOutput(`[ERROR] ${e.message}\n`)
    showToast(e.message, 'error')
  }
}

async function opsPullDataRepo() {
  try {
    setOpsOutput('[INFO] Pulling data repo updates from GitHub...\n')
    const res = await opsFetch('/admin/data/pull', { method: 'POST' })
    appendOpsOutput((res && res.output) ? `${res.output}\n` : '[INFO] Done.\n')
    showToast('数据仓库已更新', 'success')
  } catch (e) {
    appendOpsOutput(`[ERROR] ${e.message}\n`)
    showToast(e.message, 'error')
  }
}

async function opsPullRestart() {
  try {
    setOpsOutput('[INFO] Starting deploy_pull_restart.sh in background...\n')
    const res = await opsFetch('/admin/deploy', { method: 'POST' })
    const jobId = res && res.jobId ? res.jobId : ''
    const method = res && res.method ? res.method : ''
    const unit = res && res.unit ? res.unit : ''
    const pid = res && res.pid ? res.pid : ''
    appendOpsOutput(`[INFO] Deploy started. jobId=${jobId} method=${method}${unit ? ` unit=${unit}` : ''}${pid ? ` pid=${pid}` : ''}\n`)
    appendOpsOutput('[INFO] 服务会重启：期间可能出现 HTTP 502，这是正常现象，日志会自动重连。\n')
    setOpsDeployStatus('running', '正在拉取更新并部署...')
    opsStartDeployLog()
  } catch (e) {
    appendOpsOutput(`[ERROR] ${e.message}\n`)
    showToast(e.message, 'error')
  }
}

async function opsFetchDeployStatus() {
  const res = await opsFetch('/admin/deploy/status', { method: 'GET' })
  return (res && res.data) ? res.data : null
}

async function opsFetchDeployLog() {
  try {
    const res = await opsFetch('/admin/deploy/log', { method: 'GET' })
    const lines = (res && res.lines) ? res.lines : []
    const el = $('opsOutput')
    const atBottom = el ? (el.scrollTop + el.clientHeight + 24 >= el.scrollHeight) : true

    const delta = computeLineDelta(opsLastLogLines, lines)
    if (delta.mode === 'replace') {
      setOpsOutput(lines.join('\n'))
    } else if (delta.mode === 'append' && delta.lines.length > 0) {
      const prefix = (el && el.textContent && !String(el.textContent).endsWith('\n')) ? '\n' : ''
      appendOpsOutput(prefix + delta.lines.join('\n'))
    }

    opsLastLogLines = lines
    opsLastLogText = lines.join('\n')
    if (el && atBottom) el.scrollTop = el.scrollHeight
  } catch (e) {
    // Let the poll loop handle UX for transient errors.
    throw e
  }
}

function showAddProjectModal() {
  resetProjectForm()
  openModal('projectModal')
}

function closeProjectModal() {
  closeModal('projectModal')
}

function closeProjectDetailModal() {
  closeModal('projectDetailModal')
}

function showProjectDetail(projectId) {
  const p = findProjectById(projectId)
  if (!p) {
    showToast('项目未找到', 'error')
    return
  }

  currentDetailProjectId = projectId

  const repo = p.github && p.github.repository ? String(p.github.repository) : ''
  const workdir = p.workspace && p.workspace.localPath ? String(p.workspace.localPath) : ''
  const notes = String(p.notes || '')
  const desc = String(p.description || '')

  const el = $('projectDetailContent')
  el.innerHTML = `
    <div class="stats-section">
      <h3>${escapeHtml(p.name || '')}</h3>
      <div class="stats-list">
        <div class="stats-item"><span>状态</span><strong>${escapeHtml(STATUS_LABELS[p.status] || p.status || '')}</strong></div>
        <div class="stats-item"><span>优先级</span><strong>${escapeHtml(PRIORITY_LABELS[p.priority] || p.priority || '')}</strong></div>
        <div class="stats-item"><span>进度</span><strong>${escapeHtml(String(Number(p.progress || 0)))}%</strong></div>
        <div class="stats-item"><span>成本（已花费）</span><strong>${escapeHtml(formatMoneyCny(getCostTotal(p)) || '¥0')}</strong></div>
        <div class="stats-item"><span>收入（目前）</span><strong>${escapeHtml(formatMoneyCny(getRevenueTotal(p)) || '¥0')}</strong></div>
      </div>
    </div>

    <form class="pm-detail-form" onsubmit="return false;">
      <div class="form-group">
        <label>项目描述</label>
        <textarea class="pm-cell-input" rows="3" data-field="description">${escapeHtml(desc)}</textarea>
      </div>

      <div class="form-group">
        <label>工作目录</label>
        <input class="pm-cell-input" type="text" data-field="workspaceLocalPath" value="${escapeHtml(workdir)}" placeholder="如: E:/Projects/MyProject" />
      </div>

      <div class="form-group">
        <label>GitHub 仓库</label>
        <input class="pm-cell-input" type="text" data-field="githubRepository" value="${escapeHtml(repo)}" placeholder="如: https://github.com/user/repo" />
      </div>

      <div class="form-group">
        <label>备注</label>
        <textarea class="pm-cell-input" rows="3" data-field="notes">${escapeHtml(notes)}</textarea>
      </div>
    </form>
  `.trim()

  openModal('projectDetailModal')
}

function bindProjectDetailInlineEdit() {
  const container = $('projectDetailContent')
  if (!container) return

  async function commitField(el) {
    const field = el && el.getAttribute && el.getAttribute('data-field')
    if (!field) return
    const projectId = currentDetailProjectId
    if (!projectId) return
    const p = findProjectById(projectId)
    if (!p) return

    let patch = null
    if (field === 'description') {
      const v = String(el.value || '').trim()
      if (v === String(p.description || '').trim()) return
      patch = { description: v }
    } else if (field === 'notes') {
      const v = String(el.value || '').trim()
      if (v === String(p.notes || '').trim()) return
      patch = { notes: v }
    } else if (field === 'workspaceLocalPath') {
      const v = String(el.value || '').trim()
      const cur = p.workspace && p.workspace.localPath ? String(p.workspace.localPath) : ''
      if (v === cur) return
      patch = v ? { workspace: { ...(p.workspace || {}), localPath: v } } : { workspace: null }
    } else if (field === 'githubRepository') {
      const v = String(el.value || '').trim()
      const cur = p.github && p.github.repository ? String(p.github.repository) : ''
      if (v === cur) return
      patch = v ? { github: { ...(p.github || {}), repository: v, branch: (p.github && p.github.branch) ? p.github.branch : 'main' } } : { github: null }
    }

    if (!patch) return
    try {
      setSaving(el, true)
      await updateProjectPartial(projectId, patch)
    } catch (e) {
      showToast(`保存失败: ${e.message}`, 'error')
      await loadProjects()
    } finally {
      setSaving(el, false)
    }
  }

  container.addEventListener('keydown', (e) => {
    const el = e.target
    if (!el || !el.getAttribute) return
    if (!el.getAttribute('data-field')) return
    if (e.key !== 'Enter') return
    if (el.tagName && el.tagName.toLowerCase() === 'textarea') return
    e.preventDefault()
    el.blur()
  }, true)

  container.addEventListener('blur', (e) => {
    const el = e.target
    if (!el || !el.getAttribute) return
    if (!el.getAttribute('data-field')) return
    commitField(el)
  }, true)
}

function buildProjectPayloadFromForm() {
  const name = $('projectName').value.trim()
  if (!name) throw new Error('项目名称不能为空')

  const progress = Number($('projectProgress').value)
  if (Number.isNaN(progress) || progress < 0 || progress > 100) {
    throw new Error('进度必须在0-100之间')
  }

  const costTotal = Number($('projectCostTotal').value)
  if (Number.isNaN(costTotal) || costTotal < 0) throw new Error('成本必须是非负数字')

  const revenueTotal = Number($('projectRevenueTotal').value)
  if (Number.isNaN(revenueTotal) || revenueTotal < 0) throw new Error('收入必须是非负数字')

  const payload = {
    name,
    description: $('projectDescription').value.trim(),
    status: $('projectStatus').value,
    priority: $('projectPriority').value,
    progress,
    cost: { total: costTotal },
    revenue: { total: revenueTotal },
    notes: $('projectNotes').value.trim(),
  }

  const repo = $('projectGithub').value.trim()
  if (repo) {
    payload.github = { repository: repo, branch: 'main' }
  }

  const localPath = $('projectWorkspace').value.trim()
  if (localPath) {
    payload.workspace = { localPath }
  }

  return payload
}

async function saveProject(evt) {
  evt.preventDefault()
  try {
    const payload = buildProjectPayloadFromForm()

    await apiFetch('/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    showToast('项目创建成功', 'success')

    closeProjectModal()
    await loadProjects()
  } catch (e) {
    showToast(e.message, 'error')
  }
}

async function deleteProject(projectId) {
  if (!window.confirm(`确认删除项目 ${projectId} ?`)) return
  try {
    await apiFetch(`/projects/${encodeURIComponent(projectId)}`, { method: 'DELETE' })
    showToast('项目已删除', 'success')
    await loadProjects()
  } catch (e) {
    showToast(`删除失败: ${e.message}`, 'error')
  }
}

function showStats() {
  loadStats()
}

function closeStatsModal() {
  closeModal('statsModal')
}

async function loadStats() {
  try {
    const res = await apiFetch('/stats')
    const s = res && res.data
    if (!s) throw new Error('统计数据为空')

    const el = $('statsContent')
    const financial = s.financial || {}

    el.innerHTML = `
      <div class="stats-grid">
        <div class="stat-card"><div class="stat-value">${escapeHtml(String(s.total || 0))}</div><div class="stat-label">项目总数</div></div>
        <div class="stat-card"><div class="stat-value">${escapeHtml(formatMoneyCny(financial.totalCost || 0))}</div><div class="stat-label">总成本</div></div>
        <div class="stat-card"><div class="stat-value">${escapeHtml(formatMoneyCny(financial.totalRevenue || 0))}</div><div class="stat-label">总收入</div></div>
        <div class="stat-card"><div class="stat-value">${escapeHtml(formatMoneyCny(financial.netProfit || 0))}</div><div class="stat-label">净收益</div></div>
      </div>

      <div class="stats-section">
        <h3>按状态</h3>
        <div class="stats-list">
          ${Object.entries(s.byStatus || {}).map(([k, v]) => `
            <div class="stats-item"><span>${escapeHtml(STATUS_LABELS[k] || k)}</span><strong>${escapeHtml(String(v))}</strong></div>
          `).join('') || '<div class="stats-item"><span>暂无数据</span><strong>0</strong></div>'}
        </div>
      </div>

      <div class="stats-section">
        <h3>按优先级</h3>
        <div class="stats-list">
          ${Object.entries(s.byPriority || {}).map(([k, v]) => `
            <div class="stats-item"><span>${escapeHtml(PRIORITY_LABELS[k] || k)}</span><strong>${escapeHtml(String(v))}</strong></div>
          `).join('') || '<div class="stats-item"><span>暂无数据</span><strong>0</strong></div>'}
        </div>
      </div>
    `.trim()

    openModal('statsModal')
  } catch (e) {
    showToast(`获取统计失败: ${e.message}`, 'error')
  }
}

function bindModalOverlayClose() {
  const projectModal = $('projectModal')
  const projectDetailModal = $('projectDetailModal')
  const statsModal = $('statsModal')
  const opsModal = $('opsModal')
  ;[projectModal, projectDetailModal, statsModal, opsModal].forEach((m) => {
    if (!m) return
    m.addEventListener('click', (e) => {
      if (e.target === m) {
        m.classList.remove('show')
      }
    })
  })
}

window.showAddProjectModal = showAddProjectModal
window.closeProjectModal = closeProjectModal
window.saveProject = saveProject
window.applyFilters = applyFilters
window.applySortMode = applySortMode
window.showStats = showStats
window.closeStatsModal = closeStatsModal
window.closeProjectDetailModal = closeProjectDetailModal
window.openOpsModal = openOpsModal
window.closeOpsModal = closeOpsModal
window.opsPushData = opsPushData
window.opsPullDataRepo = opsPullDataRepo
window.opsPullRestart = opsPullRestart
window.opsFetchDeployLog = opsFetchDeployLog
window.opsStartDeployLog = opsStartDeployLog
window.opsStopDeployLog = opsStopDeployLog

document.addEventListener('DOMContentLoaded', () => {
  bindModalOverlayClose()
  bindProjectDetailInlineEdit()
  const sel = $('sortMode')
  sortMode = (sel && sel.value) ? sel.value : 'manual'
  loadProjects()
})
