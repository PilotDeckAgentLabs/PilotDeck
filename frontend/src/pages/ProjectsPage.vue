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
        <ProjectCard
          v-for="project in filteredProjects"
          :key="project.id"
          :project="project"
          @click="openDetailModal(project)"
        />
      </div>

      <!-- List view (table) -->
      <div v-else class="projects-table-wrapper">
        <table class="projects-table">
          <thead>
            <tr>
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
              @click="openDetailModal(project)"
              class="clickable-row"
            >
              <td class="project-name-cell">
                <span class="project-name-text">{{ project.name }}</span>
              </td>
              <td class="project-id-cell">
                <code class="table-project-id" :title="project.id">{{ project.id.slice(0, 10) }}...</code>
                <button 
                  @click.stop="copyProjectId(project.id)" 
                  class="copy-table-btn"
                  :class="{ copied: copiedId === project.id }"
                  :title="copiedId === project.id ? '已复制!' : '复制完整ID'"
                >
                  {{ copiedId === project.id ? '✓' : '📋' }}
                </button>
              </td>
              <td>
                <span class="badge" :class="`status-${project.status}`">
                  <span class="status-dot"></span>
                  {{ statusLabels[project.status] || project.status }}
                </span>
              </td>
              <td>
                <span class="badge" :class="`priority-${project.priority}`">
                  {{ priorityLabels[project.priority] || project.priority }}
                </span>
              </td>
              <td class="text-secondary">{{ project.category || '-' }}</td>
              <td class="progress-cell">
                <div class="progress-cell-inner">
                  <div class="progress-bar-wrapper">
                    <div class="progress-bar" :style="{ width: `${project.progress}%` }"></div>
                  </div>
                  <span class="progress-text">{{ project.progress }}%</span>
                </div>
              </td>
              <td>
                <div class="tags-cell">
                  <span v-for="tag in project.tags" :key="tag" class="tag">{{ tag }}</span>
                  <span v-if="!project.tags || project.tags.length === 0" class="text-muted">-</span>
                </div>
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
import { ref, onMounted } from 'vue'
import { useProjectsStore } from '../stores/projects'
import { useToast } from '../composables/useToast'
import { storeToRefs } from 'pinia'
import type { Project, ProjectFormData } from '../api/types'
import TheHeader from '../components/TheHeader.vue'
import TheFilters from '../components/TheFilters.vue'
import ProjectCard from '../components/ProjectCard.vue'
import ProjectFormModal from '../components/ProjectFormModal.vue'
import StatsModal from '../components/StatsModal.vue'
import ProjectDetailModal from '../components/ProjectDetailModal.vue'
import OpsModal from '../components/OpsModal.vue'

const projectsStore = useProjectsStore()
const { projects, filteredProjects, loading, error, viewMode } = storeToRefs(projectsStore)
const { showToast } = useToast()

// Modal states
const showFormModal = ref(false)
const showStatsModal = ref(false)
const showOpsModal = ref(false)
const showDetailModal = ref(false)
const selectedProject = ref<Project | null>(null)
const editingProject = ref<Project | null>(null)
const copiedId = ref<string | null>(null)

// Labels
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

.empty-state .btn, .error-state .btn {
  margin-top: 24px;
}

/* Grid view */
.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  animation: fadeIn 0.4s ease-out;
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

.projects-table td {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
  font-size: 14px;
}

.projects-table tbody tr {
  transition: background 0.2s;
  cursor: pointer;
}

.projects-table tbody tr:hover {
  background: rgba(59, 130, 246, 0.05);
}

.projects-table tbody tr:last-child td {
  border-bottom: none;
}

.project-name-text {
  font-weight: 600;
  color: var(--text-primary);
}

.project-id-cell {
  font-family: 'SF Mono', 'Roboto Mono', monospace;
  min-width: 140px;
}

.table-project-id {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-color);
  padding: 3px 6px;
  border-radius: 3px;
  border: 1px solid var(--border-color);
  margin-right: 6px;
}

.copy-table-btn {
  background: none;
  border: 1px solid var(--border-color);
  padding: 2px 6px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 11px;
  color: var(--text-muted);
  transition: all 0.2s;
  line-height: 1;
}

.copy-table-btn:hover {
  background: var(--bg-color);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.copy-table-btn.copied {
  background: var(--success-color);
  border-color: var(--success-color);
  color: white;
}

/* Reuse Badge Styles (Consider extracting to component next time) */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: currentColor;
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

.text-secondary { color: var(--text-secondary); }
.text-muted { color: var(--text-muted); }

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
  background: var(--bg-color);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--primary-hover));
  border-radius: 3px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 12px;
  font-family: 'SF Mono', monospace;
  color: var(--text-secondary);
  width: 36px;
  text-align: right;
}

.tags-cell {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tag {
  padding: 2px 8px;
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-secondary);
}

/* Buttons (Global Override for this page if needed) */
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
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
}

.btn-primary:hover {
  background: var(--primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(59, 130, 246, 0.4);
}

.btn-secondary {
  background: white;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--bg-color);
  border-color: var(--primary-color);
  color: var(--primary-color);
}
</style>
