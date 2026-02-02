// Projects Store - Pinia store for project state management
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Project,
  ProjectFilters,
  ProjectFormData,
  ViewMode,
  SortMode,
} from '../api/types'
import * as api from '../api/client'

export const useProjectsStore = defineStore('projects', () => {
  // ===== State =====
  const projects = ref<Project[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // Filters
  const filters = ref<ProjectFilters>({
    status: '',
    priority: '',
    category: '',
    search: '',
  })
  
  // View & Sort modes (persisted to localStorage)
  const viewMode = ref<ViewMode>(
    (localStorage.getItem('viewMode') as ViewMode) || 'card'
  )
  const sortMode = ref<SortMode>(
    (localStorage.getItem('sortMode') as SortMode) || 'manual'
  )

  // ===== Getters =====
  const filteredProjects = computed(() => {
    let result = [...projects.value]

    // Apply filters
    if (filters.value.status) {
      result = result.filter((p) => p.status === filters.value.status)
    }
    if (filters.value.priority) {
      result = result.filter((p) => p.priority === filters.value.priority)
    }
    if (filters.value.category) {
      result = result.filter((p) =>
        p.tags?.includes(filters.value.category || '')
      )
    }
    if (filters.value.search) {
      const search = filters.value.search.toLowerCase()
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(search) ||
          p.description?.toLowerCase().includes(search) ||
          p.notes?.toLowerCase().includes(search)
      )
    }

    // Apply sorting
    if (sortMode.value === 'priority') {
      const priorityOrder: Record<string, number> = {
        urgent: 0,
        high: 1,
        medium: 2,
        low: 3,
      }
      result.sort((a, b) => {
        const pa = priorityOrder[a.priority] ?? 999
        const pb = priorityOrder[b.priority] ?? 999
        return pa - pb
      })
    }
    // Manual sort keeps the order from API (which reflects user's manual ordering)

    return result
  })

  const projectById = computed(() => {
    return (id: string) => projects.value.find((p) => p.id === id)
  })

  // ===== Actions =====
  async function fetchProjects() {
    loading.value = true
    error.value = null

    try {
      // Don't pass filters to API for now - filter client-side
      // This keeps drag-drop order intact from server
      const data = await api.getProjects()
      projects.value = data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch projects'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createProject(formData: ProjectFormData): Promise<Project> {
    loading.value = true
    error.value = null

    try {
      const project = await api.createProject(formData)
      await fetchProjects() // Refresh list
      return project
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create project'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateProject(
    id: string,
    formData: Partial<ProjectFormData>
  ): Promise<Project> {
    loading.value = true
    error.value = null

    try {
      const project = await api.updateProject(id, formData)
      await fetchProjects() // Refresh list
      return project
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update project'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteProject(id: string): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await api.deleteProject(id)
      await fetchProjects() // Refresh list
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete project'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function reorderProjects(projectIds: string[]): Promise<void> {
    // Optimistic update
    const oldProjects = [...projects.value]
    projects.value = projectIds
      .map((id) => projects.value.find((p) => p.id === id))
      .filter((p): p is Project => p !== undefined)

    try {
      await api.reorderProjects(projectIds)
    } catch (err) {
      // Revert on error
      projects.value = oldProjects
      error.value = err instanceof Error ? err.message : 'Failed to reorder projects'
      throw err
    }
  }

  function setFilters(newFilters: Partial<ProjectFilters>) {
    filters.value = {
      ...filters.value,
      ...newFilters,
    }
  }

  function setSortMode(mode: SortMode) {
    sortMode.value = mode
    localStorage.setItem('sortMode', mode)
  }

  function setViewMode(mode: ViewMode) {
    viewMode.value = mode
    localStorage.setItem('viewMode', mode)
  }

  function clearError() {
    error.value = null
  }

  // ===== Return =====
  return {
    // State
    projects,
    loading,
    error,
    filters,
    viewMode,
    sortMode,

    // Getters
    filteredProjects,
    projectById,

    // Actions
    fetchProjects,
    createProject,
    updateProject,
    deleteProject,
    reorderProjects,
    setFilters,
    setSortMode,
    setViewMode,
    clearError,
  }
})
