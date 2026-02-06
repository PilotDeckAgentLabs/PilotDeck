// Typed API Client for PilotDeck
import type {
  Project,
  AgentRun,
  AgentEvent,
  Stats,
  MetaInfo,
  HealthCheck,
  ApiResponse,
  ApiErrorResponse,
  ProjectFilters,
  ProjectFormData,
  OpsLogResponse,
  DeployStartResponse,
  DeployStatusResponse,
  User,
  LoginRequest,
  AuthResponse,
} from './types'

const API_BASE_URL = '/api'

// ===== Error Handling =====

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

// ===== Fetch Wrapper =====

async function apiFetch<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`
  
  try {
    const res = await fetch(url, {
      credentials: 'include',  // Include cookies for session
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    })

    const text = await res.text()
    let json: any = null
    
    try {
      json = text ? JSON.parse(text) : null
    } catch (e) {
      json = null
    }

    if (!res.ok) {
      const errMsg = (json && (json.error || json.message)) || `HTTP ${res.status}`
      const output = (json && json.output) ? String(json.output || '') : ''
      const exitCode = (json && json.exitCode) ? ` (exit ${json.exitCode})` : ''
      
      // Show last 100 lines for debugging
      const out = output
        ? output.split('\n').slice(-100).join('\n').trim()
        : ''
      
      const fullMsg = out
        ? `${errMsg}${exitCode}\n\n=== 详细输出（最后100行） ===\n${out}`
        : `${errMsg}${exitCode}`
      
      throw new ApiError(fullMsg, res.status, json)
    }

    return json as T
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    throw new ApiError(error instanceof Error ? error.message : 'Network error')
  }
}

// ===== Ops Fetch (with token) =====

async function opsFetch<T = any>(
  path: string,
  token: string,
  options: RequestInit = {}
): Promise<T> {
  if (!token) {
    throw new ApiError('请先填写管理口令（PM_ADMIN_TOKEN）')
  }

  return apiFetch<T>(path, {
    ...options,
    headers: {
      ...(options.headers || {}),
      'X-PM-Token': token,
    },
  })
}

async function opsFetchBlob(
  path: string,
  token: string,
  options: RequestInit = {}
): Promise<{ blob: Blob; filename: string }>
{
  if (!token) {
    throw new ApiError('请先填写管理口令（PM_ADMIN_TOKEN）')
  }

  const url = `${API_BASE_URL}${path}`
  const res = await fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      'X-PM-Token': token,
    },
  })

  if (!res.ok) {
    const text = await res.text()
    let json: any = null
    try {
      json = text ? JSON.parse(text) : null
    } catch {
      json = null
    }
    const errMsg = (json && (json.error || json.message)) || `HTTP ${res.status}`
    throw new ApiError(String(errMsg), res.status, json)
  }

  const dispo = res.headers.get('Content-Disposition') || ''
  const m = dispo.match(/filename=([^;]+)/i)
  const filename = m ? String(m[1]).replace(/^"|"$/g, '') : `pm_backup_${Date.now()}.db`
  const blob = await res.blob()
  return { blob, filename }
}

// ===== Projects API =====

export async function getProjects(filters?: ProjectFilters): Promise<Project[]> {
  const params = new URLSearchParams()
  
  if (filters?.status) params.append('status', filters.status)
  if (filters?.priority) params.append('priority', filters.priority)
  if (filters?.category) params.append('category', filters.category)
  
  const query = params.toString()
  const path = query ? `/projects?${query}` : '/projects'
  
  const response = await apiFetch<ApiResponse<Project[]>>(path)
  return response.data || []
}

export async function getProject(id: string): Promise<Project> {
  const response = await apiFetch<ApiResponse<Project>>(`/projects/${id}`)
  if (!response.data) {
    throw new ApiError('Project not found', 404)
  }
  return response.data
}

export async function createProject(data: ProjectFormData): Promise<Project> {
  const projectData = {
    name: data.name,
    description: data.description || '',
    notes: data.notes || '',
    status: data.status,
    priority: data.priority,
    progress: data.progress,
    cost: { total: data.costTotal },
    revenue: { total: data.revenueTotal },
    tags: data.tags || [],
    ...(data.github && { github: data.github }),
    ...(data.workspace && { workspace: data.workspace }),
  }

  const response = await apiFetch<ApiResponse<Project>>('/projects', {
    method: 'POST',
    body: JSON.stringify(projectData),
  })

  if (!response.data) {
    throw new ApiError('Failed to create project')
  }
  
  return response.data
}

export async function updateProject(
  id: string,
  data: Partial<ProjectFormData>
): Promise<Project> {
  const projectData: any = {
    ...(data.name !== undefined && { name: data.name }),
    ...(data.description !== undefined && { description: data.description }),
    ...(data.notes !== undefined && { notes: data.notes }),
    ...(data.status !== undefined && { status: data.status }),
    ...(data.priority !== undefined && { priority: data.priority }),
    ...(data.progress !== undefined && { progress: data.progress }),
    ...(data.tags !== undefined && { tags: data.tags }),
    ...(data.github !== undefined && { github: data.github }),
    ...(data.workspace !== undefined && { workspace: data.workspace }),
  }

  if (data.costTotal !== undefined) {
    projectData.cost = { total: data.costTotal }
  }
  if (data.revenueTotal !== undefined) {
    projectData.revenue = { total: data.revenueTotal }
  }

  const response = await apiFetch<ApiResponse<Project>>(`/projects/${id}`, {
    method: 'PUT',
    body: JSON.stringify(projectData),
  })

  if (!response.data) {
    throw new ApiError('Failed to update project')
  }

  return response.data
}

export async function deleteProject(id: string): Promise<void> {
  await apiFetch(`/projects/${id}`, {
    method: 'DELETE',
  })
}

export async function reorderProjects(projectIds: string[]): Promise<Project[]> {
  const response = await apiFetch<ApiResponse<Project[]>>('/projects/reorder', {
    method: 'POST',
    body: JSON.stringify({ order: projectIds }),
  })

  return response.data || []
}

// ===== Stats API =====

export async function getStats(): Promise<Stats> {
  const response = await apiFetch<ApiResponse<Stats>>('/stats')
  return response.data || {
    total: 0,
    byStatus: {},
    byPriority: {},
    financial: { totalCost: 0, totalRevenue: 0, netProfit: 0 },
  }
}

// ===== Agent API =====

export async function getAgentRuns(projectId?: string): Promise<AgentRun[]> {
  const path = projectId ? `/agent/runs?projectId=${projectId}` : '/agent/runs'
  const response = await apiFetch<ApiResponse<AgentRun[]>>(path)
  return response.data || []
}

export async function getAgentEvents(
  projectId?: string,
  runId?: string
): Promise<AgentEvent[]> {
  const params = new URLSearchParams()
  if (projectId) params.append('projectId', projectId)
  if (runId) params.append('runId', runId)
  
  const query = params.toString()
  const path = query ? `/agent/events?${query}` : '/agent/events'
  
  const response = await apiFetch<ApiResponse<AgentEvent[]>>(path)
  return response.data || []
}

// ===== Meta & Health API =====

export async function getMeta(): Promise<MetaInfo> {
  return apiFetch<MetaInfo>('/meta')
}

export async function getHealth(): Promise<HealthCheck> {
  return apiFetch<HealthCheck>('/health')
}

// ===== Ops/Admin API =====

export async function opsPullRestart(token: string): Promise<DeployStartResponse> {
  // Backend route: POST /api/admin/deploy
  return opsFetch<DeployStartResponse>('/admin/deploy', token, { method: 'POST' })
}

export async function opsDownloadBackup(token: string): Promise<{ blob: Blob; filename: string }> {
  return opsFetchBlob('/admin/backup', token, { method: 'GET' })
}

export async function opsRestoreFromBackup(token: string, file: File): Promise<any> {
  const form = new FormData()
  form.append('file', file)
  // NOTE: Do not set Content-Type manually for multipart.
  return opsFetch('/admin/restore', token, { method: 'POST', body: form, headers: {} })
}

export async function opsGetDeployLog(token: string): Promise<OpsLogResponse> {
  // Backend route: GET /api/admin/deploy/log
  return opsFetch<OpsLogResponse>('/admin/deploy/log', token)
}

export async function opsGetDeployStatus(token: string): Promise<DeployStatusResponse> {
  // Backend route: GET /api/admin/deploy/status
  return opsFetch<DeployStatusResponse>('/admin/deploy/status', token)
}

// ===== Auth API =====

export async function login(credentials: LoginRequest): Promise<User> {
  const response = await apiFetch<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  })
  
  if (!response.success || !response.data?.user) {
    throw new ApiError(response.error || 'Login failed')
  }
  
  return response.data.user
}

export async function checkAuth(): Promise<User | null> {
  try {
    const response = await apiFetch<AuthResponse>('/auth/me')
    if (response.success && response.data?.user) {
      return response.data.user
    }
    return null
  } catch (error) {
    // Not authenticated
    return null
  }
}

export async function logout(): Promise<void> {
  await apiFetch('/auth/logout', {
    method: 'POST',
  })
}

