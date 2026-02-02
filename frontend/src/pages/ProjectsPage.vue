<template>
  <div class="projects-page">
    <!-- Header with actions -->
    <TheHeader
      @add-project="openAddModal"
      @show-stats="showStatsModal = true"
      @show-ops="showOpsModal = true"
      @refresh="loadProjects"
    />

    <!-- Filters bar -->
    <TheFilters />

    <main class="container">
      <!-- Loading state -->
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
        <button @click="loadProjects" class="btn btn-secondary">重试</button>
      </div>

      <!-- Empty state -->
      <div v-else-if="filteredProjects.length === 0" class="empty-state">
        <p>{{ projects.length === 0 ? '还没有项目' : '没有符合条件的项目' }}</p>
        <button v-if="projects.length === 0" @click="openAddModal" class="btn btn-primary">
          创建第一个项目
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
              <td class="project-name">{{ project.name }}</td>
              <td>
                <span class="badge" :class="`status-${project.status}`">
                  {{ statusLabels[project.status] || project.status }}
                </span>
              </td>
              <td>
                <span class="badge" :class="`priority-${project.priority}`">
                  {{ priorityLabels[project.priority] || project.priority }}
                </span>
              </td>
              <td>{{ project.category || '-' }}</td>
              <td>
                <div class="progress-bar-wrapper">
                  <div class="progress-bar" :style="{ width: `${project.progress}%` }"></div>
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
      :project="editingProject"
      @close="closeFormModal"
      @save="handleSaveProject"
    />

    <StatsModal
      v-if="showStatsModal"
      @close="showStatsModal = false"
    />

    <!-- Simple detail modal (placeholder for now) -->
    <div v-if="showDetailModal && selectedProject" class="modal-overlay" @click.self="closeDetailModal">
      <div class="modal-content detail-modal">
        <div class="modal-header">
          <h2>{{ selectedProject.name }}</h2>
          <button @click="closeDetailModal" class="btn-close">×</button>
        </div>
        <div class="modal-body">
          <div class="detail-section">
            <label>描述</label>
            <p>{{ selectedProject.description || '无描述' }}</p>
          </div>
          <div class="detail-row">
            <div class="detail-section">
              <label>状态</label>
              <span class="badge" :class="`status-${selectedProject.status}`">
                {{ statusLabels[selectedProject.status] }}
              </span>
            </div>
            <div class="detail-section">
              <label>优先级</label>
              <span class="badge" :class="`priority-${selectedProject.priority}`">
                {{ priorityLabels[selectedProject.priority] }}
              </span>
            </div>
          </div>
          <div class="detail-row">
            <div class="detail-section">
              <label>分类</label>
              <p>{{ selectedProject.category || '-' }}</p>
            </div>
            <div class="detail-section">
              <label>进度</label>
              <p>{{ selectedProject.progress }}%</p>
            </div>
          </div>
          <div class="detail-section">
            <label>标签</label>
            <div class="tags">
              <span v-for="tag in selectedProject.tags" :key="tag" class="tag">{{ tag }}</span>
              <span v-if="!selectedProject.tags || selectedProject.tags.length === 0">-</span>
            </div>
          </div>
          <div class="detail-row">
            <div class="detail-section">
              <label>创建时间</label>
              <p>{{ formatDate(selectedProject.created_at) }}</p>
            </div>
            <div class="detail-section">
              <label>更新时间</label>
              <p>{{ formatDate(selectedProject.updated_at) }}</p>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="openEditModal(selectedProject)" class="btn btn-primary">编辑</button>
          <button @click="handleDeleteProject(selectedProject.id)" class="btn btn-danger">删除</button>
        </div>
      </div>
    </div>

    <!-- Ops modal placeholder -->
    <div v-if="showOpsModal" class="modal-overlay" @click.self="showOpsModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>运维操作</h2>
          <button @click="showOpsModal = false" class="btn-close">×</button>
        </div>
        <div class="modal-body">
          <p class="text-muted">运维功能开发中...</p>
        </div>
      </div>
    </div>
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
  if (!confirm('确定要删除这个项目吗？')) return
  
  try {
    await projectsStore.deleteProject(id)
    showToast('项目已删除', 'success')
    closeDetailModal()
  } catch (err) {
    console.error('Failed to delete project:', err)
    showToast('删除项目失败', 'error')
  }
}

// Utility
function formatDate(date: string): string {
  return new Date(date).toLocaleString('zh-CN')
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
.projects-page {
  min-height: 100vh;
  background: var(--bg-gradient);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px;
}

.loading,
.error-state,
.empty-state {
  text-align: center;
  padding: 60px 20px;
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

.empty-state .btn {
  margin-top: 16px;
}

/* Grid view */
.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

/* Table view */
.projects-table-wrapper {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  overflow: hidden;
  box-shadow: var(--shadow);
}

.projects-table {
  width: 100%;
  border-collapse: collapse;
}

.projects-table th {
  background: var(--header-bg);
  color: var(--text-primary);
  font-weight: 600;
  text-align: left;
  padding: 12px 16px;
  font-size: 14px;
  border-bottom: 2px solid var(--border-color);
}

.projects-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
}

.projects-table tbody tr.clickable-row {
  cursor: pointer;
  transition: background 0.2s;
}

.projects-table tbody tr.clickable-row:hover {
  background: var(--hover-bg);
}

.project-name {
  font-weight: 500;
  color: var(--primary-color);
}

.progress-bar-wrapper {
  position: relative;
  width: 100%;
  height: 20px;
  background: var(--bg-secondary);
  border-radius: 10px;
  overflow: hidden;
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
  font-size: 11px;
  font-weight: 500;
  color: var(--text-primary);
}

.tags-cell {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.tag {
  padding: 2px 8px;
  background: var(--tag-bg);
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-secondary);
}

.text-muted {
  color: var(--text-secondary);
}

/* Badges */
.badge {
  display: inline-block;
  padding: 4px 8px;
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

/* Buttons */
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

/* Detail modal */
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
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow: auto;
}

.detail-modal {
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
}

.tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
</style>
