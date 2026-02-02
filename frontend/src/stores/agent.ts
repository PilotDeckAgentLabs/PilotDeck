// Agent Store - Pinia store for agent runs and events
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AgentRun, AgentEvent } from '../api/types'
import * as api from '../api/client'

export const useAgentStore = defineStore('agent', () => {
  // ===== State =====
  const runs = ref<AgentRun[]>([])
  const events = ref<AgentEvent[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ===== Getters =====
  const runsByProject = computed(() => {
    return (projectId: string) =>
      runs.value.filter((r) => r.projectId === projectId)
  })

  const eventsByProject = computed(() => {
    return (projectId: string) =>
      events.value.filter((e) => e.projectId === projectId)
  })

  const eventsByRun = computed(() => {
    return (runId: string) =>
      events.value.filter((e) => e.runId === runId)
  })

  const runById = computed(() => {
    return (runId: string) => runs.value.find((r) => r.id === runId)
  })

  // ===== Actions =====
  async function fetchRuns(projectId?: string) {
    loading.value = true
    error.value = null

    try {
      const data = await api.getAgentRuns(projectId)
      runs.value = data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch runs'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchEvents(projectId?: string, runId?: string) {
    loading.value = true
    error.value = null

    try {
      const data = await api.getAgentEvents(projectId, runId)
      events.value = data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch events'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchProjectTimeline(projectId: string) {
    // Fetch both runs and events for a project
    loading.value = true
    error.value = null

    try {
      const [runsData, eventsData] = await Promise.all([
        api.getAgentRuns(projectId),
        api.getAgentEvents(projectId),
      ])
      
      runs.value = runsData
      events.value = eventsData
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch timeline'
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  function clearData() {
    runs.value = []
    events.value = []
  }

  // ===== Return =====
  return {
    // State
    runs,
    events,
    loading,
    error,

    // Getters
    runsByProject,
    eventsByProject,
    eventsByRun,
    runById,

    // Actions
    fetchRuns,
    fetchEvents,
    fetchProjectTimeline,
    clearError,
    clearData,
  }
})
