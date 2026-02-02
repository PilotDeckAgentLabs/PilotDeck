<template>
  <div class="projects-page">
    <header class="page-header">
      <div class="container">
        <h1>我的项目管理系统 (Vue 3)</h1>
        <div class="header-actions">
          <button @click="toggleTheme" class="btn-icon" title="切换主题">
            {{ currentTheme === 'dark' ? '🌙' : '☀️' }}
          </button>
          <button @click="loadProjects" class="btn btn-primary">刷新</button>
        </div>
      </div>
    </header>

    <main class="container">
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
        <button @click="loadProjects" class="btn btn-secondary">重试</button>
      </div>

      <div v-else-if="projects.length === 0" class="empty-state">
        <p>还没有项目</p>
      </div>

      <div v-else class="projects-list">
        <div v-for="project in projects" :key="project.id" class="project-card">
          <h3>{{ project.name }}</h3>
          <p class="project-desc">{{ project.description || '无描述' }}</p>
          <div class="project-meta">
            <span class="badge" :class="`status-${project.status}`">
              {{ statusLabels[project.status] || project.status }}
            </span>
            <span class="badge" :class="`priority-${project.priority}`">
              {{ priorityLabels[project.priority] || project.priority }}
            </span>
            <span class="progress">进度: {{ project.progress }}%</span>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useProjectsStore } from '../stores/projects'
import { useTheme } from '../composables/useTheme'
import { storeToRefs } from 'pinia'

const projectsStore = useProjectsStore()
const { projects, loading, error } = storeToRefs(projectsStore)
const { currentTheme, toggleTheme } = useTheme()

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

async function loadProjects() {
  try {
    await projectsStore.fetchProjects()
  } catch (err) {
    console.error('Failed to load projects:', err)
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
}

.page-header {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.9), rgba(37, 99, 235, 0.85));
  color: white;
  padding: 20px 0;
}

.page-header .container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.btn-icon {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 18px;
  transition: background 0.2s;
}

.btn-icon:hover {
  background: rgba(255, 255, 255, 0.25);
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
  background: var(--secondary-color);
  color: white;
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

.projects-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.project-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 20px;
  box-shadow: var(--shadow);
  transition: transform 0.2s, box-shadow 0.2s;
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.project-card h3 {
  margin: 0 0 8px 0;
  color: var(--text-primary);
}

.project-desc {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0 0 12px 0;
}

.project-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.badge {
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

.progress {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
