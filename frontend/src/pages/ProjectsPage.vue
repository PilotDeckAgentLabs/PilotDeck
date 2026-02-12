<template>
  <div class="projects-page">
    <!-- Header with actions -->
    <TheHeader
      @add-project="openAddModal"
      @show-stats="showStatsModal = true"
      @show-ops="showOpsModal = true"
      @refresh="loadProjects"
    />

    <main class="container">
      <!-- Filters bar -->
      <TheFilters />

      <!-- Loading state -->
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>系统连接中...</p>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error-state">
        <div class="error-icon">⚠️</div>
        <h3>连接失败</h3>
        <p>{{ error }}</p>
        <button @click="loadProjects" class="btn btn-secondary">重试连接</button>
      </div>

      <!-- Empty state -->
      <div v-else-if="filteredProjects.length === 0" class="empty-state">
        <div class="empty-icon">📂</div>
        <h3>{{ projects.length === 0 ? '暂无项目' : '未找到匹配项目' }}</h3>
        <p>{{ projects.length === 0 ? '开始你的第一个项目管理之旅' : '尝试调整筛选条件' }}</p>
        <button v-if="projects.length === 0" @click="openAddModal" class="btn btn-primary">
          创建新项目
        </button>
      </div>

      <!-- Card view -->
      <div v-else-if="viewMode === 'card'" class="projects-grid">
        <div
          v-for="project in filteredProjects"
          :key="project.id"
          class="draggable-card-wrapper"
          :class="{
            'drag-enabled': sortMode === 'manual',
            'dragging': draggingProjectId === project.id,
            'drag-over': dragOverProjectId === project.id && draggingProjectId !== project.id,
          }"
          :draggable="sortMode === 'manual'"
          @dragstart="onDragStart(project.id)"
          @dragover.prevent="onDragOver(project.id)"
          @drop.prevent="onDrop(project.id)"
          @dragend="onDragEnd"
        >
          <ProjectCard
            :project="project"
            @click="openDetailModal(project)"
          />
          <div v-if="sortMode === 'manual'" class="drag-handle-overlay">
            <span class="drag-icon">⠿</span>
          </div>
        </div>
      </div>

      <!-- List view (table) -->
      <div v-else class="projects-table-wrapper">
        <table class="projects-table">
          <thead>
            <tr>
              <th class="drag-column"></th>
              <th>项目名称</th>
              <th>项目ID</th>
              <th>状态</th>
              <th>优先级</th>
              <th>分类</th>
              <th>进度</th>
              <th>标签</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="project in filteredProjects"
              :key="project.id"
              :draggable="sortMode === 'manual'"
              :class="{
                'drag-enabled': sortMode === 'manual',
                'dragging': draggingProjectId === project.id,
                'drag-over': dragOverProjectId === project.id && draggingProjectId !== project.id,
              }"
              @dragstart="onDragStart(project.id)"
              @dragover.prevent="onDragOver(project.id)"
              @drop.prevent="onDrop(project.id)"
              @dragend="onDragEnd"
              @click="openDetailModal(project)"
              class="clickable-row"
            >
              <td class="drag-handle-cell" @click.stop>
                <span v-if="sortMode === 'manual'" class="drag-handle-icon">⠿</span>
              </td>
              <td class="project-name-cell">
                <input
                  class="inline-input project-name-input"
                  :value="getDraft(project).name"
                  @click.stop
                  @input="setDraftValue(project.id, 'name', ($event.target as HTMLInputElement).value)"
                  @blur="saveInlineField(project, 'name')"
                  @keydown.enter.prevent="saveInlineField(project, 'name')"
                />
              </td>
              <td class="project-id-cell">
                <code class="table-project-id" :title="project.id">#{{ project.id.slice(0, 8) }}</code>
                <button 
                  @click.stop="copyProjectId(project.id)" 
                  class="copy-table-btn"
                  :class="{ copied: copiedId === project.id }"
                  :title="copiedId === project.id ? '已复制!' : '复制完整ID'"
                >
                  {{ copiedId === project.id ? '✓' : '📋' }}
                </button>
              </td>
              <td @click.stop>
                <select
                  class="inline-select"
                  :value="getDraft(project).status"
                  @change="updateSelectField(project, 'status', ($event.target as HTMLSelectElement).value)"
                >
                  <option value="planning">计划中</option>
                  <option value="in-progress">进行中</option>
                  <option value="paused">暂停</option>
                  <option value="completed">已完成</option>
                  <option value="cancelled">已取消</option>
                </select>
              </td>
              <td @click.stop>
                <select
                  class="inline-select"
                  :value="getDraft(project).priority"
                  @change="updateSelectField(project, 'priority', ($event.target as HTMLSelectElement).value)"
                >
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                  <option value="urgent">紧急</option>
                </select>
              </td>
              <td class="text-secondary" @click.stop>
                <input
                  class="inline-input"
                  :value="getDraft(project).category"
                  @input="setDraftValue(project.id, 'category', ($event.target as HTMLInputElement).value)"
                  @blur="saveInlineField(project, 'category')"
                  @keydown.enter.prevent="saveInlineField(project, 'category')"
                />
              </td>
              <td class="progress-cell" @click.stop>
                <div class="progress-cell-inner">
                  <div class="progress-bar-wrapper">
                    <div class="progress-bar" :style="{ width: `${getDraft(project).progress}%` }"></div>
                  </div>
                  <input
                    class="inline-progress-input"
                    type="number"
                    min="0"
                    max="100"
                    :value="getDraft(project).progress"
                    @input="setDraftValue(project.id, 'progress', ($event.target as HTMLInputElement).valueAsNumber)"
                    @blur="saveInlineField(project, 'progress')"
                    @keydown.enter.prevent="saveInlineField(project, 'progress')"
                  />
                </div>
              </td>
              <td @click.stop>
                <input
                  class="inline-input tags-input"
                  :value="getDraft(project).tagsText"
                  placeholder="逗号分隔标签"
                  @input="setDraftValue(project.id, 'tagsText', ($event.target as HTMLInputElement).value)"
                  @blur="saveInlineField(project, 'tagsText')"
                  @keydown.enter.prevent="saveInlineField(project, 'tagsText')"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>

    <!-- Modals -->
    <ProjectFormModal
      v-if="showFormModal"
      :show="showFormModal"
      :project="editingProject"
      @close="closeFormModal"
      @save="handleSaveProject"
    />

    <StatsModal
      v-if="showStatsModal"
      :show="showStatsModal"
      @close="showStatsModal = false"
    />

    <ProjectDetailModal
      v-if="showDetailModal && selectedProject"
      :project="selectedProject"
      @close="closeDetailModal"
      @edit="openEditModal"
      @delete="handleDeleteProject"
    />

    <OpsModal
      v-if="showOpsModal"
      @close="showOpsModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useProjectsStore } from '../stores/projects'
import { useToast } from '../composables/useToast'
import { storeToRefs } from 'pinia'
import type { Project, ProjectFormData, ProjectStatus, ProjectPriority } from '../api/types'
import TheHeader from '../components/TheHeader.vue'
import TheFilters from '../components/TheFilters.vue'
import ProjectCard from '../components/ProjectCard.vue'
import ProjectFormModal from '../components/ProjectFormModal.vue'
import StatsModal from '../components/StatsModal.vue'
import ProjectDetailModal from '../components/ProjectDetailModal.vue'
import OpsModal from '../components/OpsModal.vue'

const projectsStore = useProjectsStore()
const { projects, filteredProjects, loading, error, viewMode, sortMode } = storeToRefs(projectsStore)
const { showToast } = useToast()

// Modal states
const showFormModal = ref(false)
const showStatsModal = ref(false)
const showOpsModal = ref(false)
const showDetailModal = ref(false)
const selectedProject = ref<Project | null>(null)
const editingProject = ref<Project | null>(null)
const copiedId = ref<string | null>(null)
const draggingProjectId = ref<string | null>(null)
const dragOverProjectId = ref<string | null>(null)

interface InlineDraft {
  name: string
  status: ProjectStatus
  priority: ProjectPriority
  category: string
  progress: number
  tagsText: string
}

const inlineDrafts = reactive<Record<string, InlineDraft>>({})

// Load projects
async function loadProjects() {
  try {
    await projectsStore.fetchProjects()
  } catch (err) {
    console.error('Failed to load projects:', err)
    showToast('加载项目失败', 'error')
  }
}

// Modal handlers
function openAddModal() {
  editingProject.value = null
  showFormModal.value = true
}

function openEditModal(project: Project) {
  editingProject.value = project
  showDetailModal.value = false
  showFormModal.value = true
}

function openDetailModal(project: Project) {
  selectedProject.value = project
  showDetailModal.value = true
}

function closeFormModal() {
  showFormModal.value = false
  editingProject.value = null
}

function closeDetailModal() {
  showDetailModal.value = false
  selectedProject.value = null
}

// Copy project ID
async function copyProjectId(id: string) {
  try {
    await navigator.clipboard.writeText(id)
    copiedId.value = id
    setTimeout(() => {
      copiedId.value = null
    }, 2000)
  } catch (err) {
    console.error('Failed to copy project ID:', err)
  }
}

function getDraft(project: Project): InlineDraft {
  if (!inlineDrafts[project.id]) {
    inlineDrafts[project.id] = {
      name: project.name,
      status: project.status,
      priority: project.priority,
      category: project.category || '',
      progress: project.progress,
      tagsText: project.tags?.join(', ') || '',
    }
  }
  return inlineDrafts[project.id]
}

function setDraftValue(
  projectId: string,
  field: keyof InlineDraft,
  value: string | number
) {
  const draft = inlineDrafts[projectId]
  if (!draft) return
  if (field === 'progress') {
    const normalized = Number.isFinite(value as number) ? Number(value) : 0
    draft.progress = Math.min(100, Math.max(0, normalized))
    return
  }
  draft[field] = String(value) as never
}

async function saveInlineField(project: Project, field: keyof InlineDraft) {
  const draft = getDraft(project)
  const payload: Partial<ProjectFormData> = {}

  if (field === 'name') {
    const next = draft.name.trim()
    if (!next || next === project.name) return
    payload.name = next
  }

  if (field === 'category') {
    const next = draft.category.trim()
    if ((project.category || '') === next) return
    payload.category = next
  }

  if (field === 'progress') {
    const next = Math.min(100, Math.max(0, Math.round(draft.progress)))
    if (next === project.progress) return
    payload.progress = next
    draft.progress = next
  }

  if (field === 'tagsText') {
    const nextTags = draft.tagsText
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean)
    const current = project.tags || []
    if (JSON.stringify(nextTags) === JSON.stringify(current)) return
    payload.tags = nextTags
    draft.tagsText = nextTags.join(', ')
  }

  if (Object.keys(payload).length === 0) return

  try {
    const updated = await projectsStore.patchProject(project.id, payload)
    inlineDrafts[project.id] = {
      name: updated.name,
      status: updated.status,
      priority: updated.priority,
      category: updated.category || '',
      progress: updated.progress,
      tagsText: updated.tags?.join(', ') || '',
    }
  } catch (err) {
    console.error('Failed to save inline field:', err)
    showToast('保存失败，请重试', 'error')
  }
}

async function updateSelectField(
  project: Project,
  field: 'status' | 'priority',
  value: string
) {
  const draft = getDraft(project)
  if (field === 'status') {
    const status = value as ProjectStatus
    if (status === project.status) return
    draft.status = status
    try {
      await projectsStore.patchProject(project.id, { status })
    } catch (err) {
      draft.status = project.status
      console.error('Failed to update status:', err)
      showToast('更新状态失败', 'error')
    }
    return
  }

  const priority = value as ProjectPriority
  if (priority === project.priority) return
  draft.priority = priority
  try {
    await projectsStore.patchProject(project.id, { priority })
  } catch (err) {
    draft.priority = project.priority
    console.error('Failed to update priority:', err)
    showToast('更新优先级失败', 'error')
  }
}

function reorderVisibleProjects(sourceId: string, targetId: string): string[] {
  const visibleIds = filteredProjects.value.map((project) => project.id)
  const sourceIndex = visibleIds.indexOf(sourceId)
  const targetIndex = visibleIds.indexOf(targetId)
  if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) {
    return []
  }

  const moved = [...visibleIds]
  const [item] = moved.splice(sourceIndex, 1)
  moved.splice(targetIndex, 0, item)

  const visibleSet = new Set(visibleIds)
  const queue = [...moved]
  return projects.value.map((project) => {
    if (!visibleSet.has(project.id)) return project.id
    return queue.shift() || project.id
  })
}

function onDragStart(projectId: string) {
  if (sortMode.value !== 'manual') return
  draggingProjectId.value = projectId
}

function onDragOver(projectId: string) {
  if (!draggingProjectId.value || sortMode.value !== 'manual') return
  dragOverProjectId.value = projectId
}

async function onDrop(projectId: string) {
  if (!draggingProjectId.value || sortMode.value !== 'manual') return
  const sourceId = draggingProjectId.value
  const reordered = reorderVisibleProjects(sourceId, projectId)
  if (reordered.length > 0) {
    try {
      await projectsStore.reorderProjects(reordered)
      showToast('项目顺序已更新', 'success')
    } catch (err) {
      console.error('Failed to reorder projects:', err)
      showToast('拖动排序失败', 'error')
    }
  }
  onDragEnd()
}

function onDragEnd() {
  draggingProjectId.value = null
  dragOverProjectId.value = null
}

// CRUD handlers
async function handleSaveProject(data: ProjectFormData) {
  try {
    if (editingProject.value) {
      await projectsStore.updateProject(editingProject.value.id, data)
      showToast('项目已更新', 'success')
    } else {
      await projectsStore.createProject(data)
      showToast('项目已创建', 'success')
    }
    closeFormModal()
  } catch (err) {
    console.error('Failed to save project:', err)
    showToast(editingProject.value ? '更新项目失败' : '创建项目失败', 'error')
  }
}

async function handleDeleteProject(id: string) {
  try {
    await projectsStore.deleteProject(id)
    showToast('项目已删除', 'success')
    closeDetailModal()
  } catch (err) {
    console.error('Failed to delete project:', err)
    showToast('删除项目失败', 'error')
  }
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
.projects-page {
  min-height: 100vh;
  background: var(--bg-gradient);
  padding-bottom: 40px;
}

.container {
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px;
}

/* States */
.loading,
.error-state,
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-secondary);
}

.spinner {
  border: 3px solid rgba(59, 130, 246, 0.1);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  width: 48px;
  height: 48px;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 24px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon, .error-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state h3, .error-state h3 {
  font-size: 18px;
  color: var(--text-primary);
  margin-bottom: 8px;
}

/* Grid view */
.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  animation: fadeIn 0.4s ease-out;
}

.draggable-card-wrapper {
  position: relative;
  transition: transform 0.2s, opacity 0.2s;
}

.draggable-card-wrapper.drag-enabled {
  cursor: grab;
}

.draggable-card-wrapper.dragging {
  opacity: 0.4;
  transform: scale(0.98);
}

.draggable-card-wrapper.drag-over {
  outline: 2px solid var(--primary-color);
  outline-offset: 4px;
  border-radius: var(--border-radius);
  background: rgba(59, 130, 246, 0.05);
}

.drag-handle-overlay {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--border-color);
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
  pointer-events: none;
  z-index: 10;
  opacity: 0.7;
}

.drag-icon {
  font-size: 16px;
  color: var(--text-muted);
  line-height: 1;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Table view */
.projects-table-wrapper {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--border-radius);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  backdrop-filter: var(--backdrop-blur);
}

.projects-table {
  width: 100%;
  border-collapse: collapse;
}

.projects-table th {
  background: var(--bg-color);
  color: var(--text-muted);
  font-weight: 600;
  text-align: left;
  padding: 16px 20px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-color);
}

.drag-column {
  width: 40px;
  padding: 0 8px;
}

.projects-table td {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
  font-size: 14px;
}

.projects-table tbody tr {
  transition: background 0.2s, opacity 0.2s;
  cursor: pointer;
}

.projects-table tbody tr.drag-enabled {
  cursor: grab;
}

.projects-table tbody tr.dragging {
  opacity: 0.4;
  background: var(--bg-secondary) !important;
}

.projects-table tbody tr.drag-over td {
  border-top: 2px solid var(--primary-color);
  background: rgba(59, 130, 246, 0.05);
}

.drag-handle-cell {
  width: 40px;
  padding: 0 8px;
  text-align: center;
}

.drag-handle-icon {
  font-size: 18px;
  color: var(--text-muted);
  user-select: none;
  opacity: 0.4;
  transition: opacity 0.2s;
}

.projects-table tbody tr:hover .drag-handle-icon {
  opacity: 1;
}

.projects-table tbody tr:hover {
  background: rgba(59, 130, 246, 0.05);
}

.projects-table tbody tr:last-child td {
  border-bottom: none;
}

.inline-input,
.inline-select,
.inline-progress-input {
  width: 100%;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-primary);
  font-size: 14px;
  border-radius: 6px;
  padding: 6px 8px;
  transition: border-color 0.2s, background 0.2s;
}

.inline-input:hover,
.inline-select:hover,
.inline-progress-input:hover {
  background: rgba(59, 130, 246, 0.05);
}

.inline-input:focus,
.inline-select:focus,
.inline-progress-input:focus {
  outline: none;
  border-color: var(--primary-color);
  background: var(--card-bg);
}

.project-name-input {
  font-weight: 600;
}

.inline-select {
  cursor: pointer;
}

.inline-progress-input {
  width: 64px;
  text-align: right;
  font-family: 'SF Mono', 'Roboto Mono', monospace;
}

.tags-input {
  min-width: 160px;
}

.project-id-cell {
  font-family: 'SF Mono', 'Roboto Mono', monospace;
  min-width: 130px;
}

.table-project-id {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-secondary);
  padding: 3px 6px;
  border-radius: 4px;
  margin-right: 6px;
}

.copy-table-btn {
  background: none;
  border: 1px solid var(--border-color);
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: var(--text-muted);
  transition: all 0.2s;
}

.copy-table-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.copy-table-btn.copied {
  background: var(--success-color);
  border-color: var(--success-color);
  color: white;
}

/* Progress Bar in Table */
.progress-cell {
  min-width: 120px;
}

.progress-cell-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar-wrapper {
  flex: 1;
  height: 6px;
  background: var(--bg-secondary);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--primary-color);
  border-radius: 3px;
  transition: width 0.3s;
}

/* Buttons */
.btn {
  padding: 10px 20px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-secondary {
  background: white;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}
</style>
