// API Type Definitions for PilotDeck
// Based on server/mypm/domain/models.py

// ===== Project Types =====

export type ProjectStatus = 'planning' | 'in-progress' | 'paused' | 'completed' | 'cancelled'
export type ProjectPriority = 'low' | 'medium' | 'high' | 'urgent'

export interface CostRevenue {
  total: number
  [key: string]: any  // Allow additional keys
}

export type OrderStatus = 'pending' | 'confirmed' | 'delivered' | 'completed' | 'cancelled'

export interface OrderItem {
  id: string
  title: string
  customer: string
  amount: number
  cost: number
  status: OrderStatus
  createdAt: string
  dueDate?: string
  note?: string
}

export interface Project {
  id: string
  name: string
  description: string
  notes: string
  status: ProjectStatus
  priority: ProjectPriority
  progress: number  // 0-100
  tags: string[]
  cost: CostRevenue
  revenue: CostRevenue
  budget: number
  actualCost: number
  createdAt: string  // ISO 8601
  updatedAt: string  // ISO 8601
  github?: string
  workspace?: string
  orders?: OrderItem[]
  [key: string]: any  // Allow additional fields
}

// ===== Agent Types =====

export type AgentRunStatus = 'running' | 'completed' | 'failed' | 'cancelled'
export type AgentEventLevel = 'debug' | 'info' | 'warn' | 'error'
export type AgentEventType = 'note' | 'action' | 'result' | 'error' | 'milestone'

export interface AgentRun {
  id: string
  projectId: string | null
  agentId: string | null
  title: string | null
  summary: string | null
  status: AgentRunStatus
  createdAt: string
  updatedAt: string
  startedAt: string
  finishedAt: string | null
  links: string[]
  tags: string[]
  metrics: Record<string, any>
  meta: Record<string, any>
}

export interface AgentEvent {
  id: string | null
  ts: string | null  // timestamp
  type: AgentEventType
  level: AgentEventLevel
  projectId: string | null
  runId: string | null
  agentId: string | null
  title: string | null
  message: string | null
  data: any
}

// ===== Stats Types =====

export interface StatusStats {
  [status: string]: number
}

export interface PriorityStats {
  [priority: string]: number
}

export interface CategoryStats {
  [category: string]: number
}

export interface FinancialStats {
  totalCost: number
  totalRevenue: number
  netProfit: number
}

export interface Stats {
  total: number
  byStatus: StatusStats
  byPriority: PriorityStats
  financial: FinancialStats
}

// ===== API Response Types =====

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface ApiErrorResponse {
  success: false
  error: string
  message?: string
  output?: string
  exitCode?: number
}

// ===== Ops/Admin Types =====

export interface OpsLogResponse {
  success: boolean
  lines: string[]
}

export interface DeployStartResponse {
  success: boolean
  jobId: string
  method?: string
  unit?: string | null
  pid?: number | null
  logFile?: string
}

export interface DeployStatusData {
  state: 'running' | 'success' | 'failed' | 'unknown'
  method?: string
  unit?: string | null
  pid?: number | null
  exitCode?: number | null
  message?: string
  startedAt?: string
  updatedAt?: string
}

export interface DeployStatusResponse {
  success: boolean
  data: DeployStatusData
}

export interface MetaInfo {
  service: string
  version: string
  [key: string]: any
}

export interface HealthCheck {
  status: string
  [key: string]: any
}

// ===== Filter & View Types =====

export interface ProjectFilters {
  status?: ProjectStatus | ''
  priority?: ProjectPriority | ''
  category?: string
  search?: string
}

export type ViewMode = 'card' | 'list'
export type SortMode = 'manual' | 'priority'

// ===== Form Types =====

export interface ProjectFormData {
  name: string
  description?: string
  notes?: string
  status: ProjectStatus
  priority: ProjectPriority
  category?: string
  progress: number
  costTotal: number
  revenueTotal: number
  github?: string
  workspace?: string
  tags?: string[]
  orders?: OrderItem[]
}

// ===== Auth Types =====

export interface User {
  id: string
  username: string
  role: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface AuthResponse {
  success: boolean
  data?: {
    user: User
  }
  error?: string
}
