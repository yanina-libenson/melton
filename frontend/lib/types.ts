// Core data types for the application

export type AgentStatus = 'active' | 'inactive' | 'draft'

export type AuthenticationType = 'none' | 'api-key' | 'bearer' | 'basic' | 'oauth'

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'

export type IntegrationSourceType = 'platform' | 'custom-tool' | 'sub-agent'

export type CustomToolType = 'api' | 'llm'

export interface LLMModel {
  id: string
  modelId: string
  provider: 'anthropic' | 'openai' | 'google'
  displayName: string
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface Agent {
  id: string
  userId: string
  organizationId: string
  name: string
  instructions: string
  status: AgentStatus
  model_config: {
    provider: 'anthropic' | 'openai' | 'google'
    model: string
    temperature: number
    max_tokens: number
    top_p?: number | null
  }
  createdAt: string
  updatedAt: string
  integrations: IntegrationSource[]
}

export interface IntegrationSource {
  id: string
  agentId: string
  name: string
  type: IntegrationSourceType
  description: string | null
  icon?: string
  platformId?: string | null
  config: Record<string, unknown>
  createdAt: string
  updatedAt: string
  availableTools: Tool[]
}

export interface Tool {
  id: string
  name: string
  description?: string | null
  sourceId: string
  toolType?: CustomToolType | 'sub-agent' | null
  toolSchema?: Record<string, unknown>
  config?: Record<string, unknown>
  isEnabled?: boolean
  createdAt?: string
  updatedAt?: string
  // LLM configuration (for llm and api-llm types)
  llmModel?:
    | 'gpt-4o'
    | 'claude-sonnet-4-5-20250929'
    | 'claude-opus-4-5-20251101'
    | 'gemini-2.0-flash-exp'
  llmInstructions?: string
  // Sub-agent configuration
  subAgentId?: string
  // API configuration (for api and api-llm types)
  endpoint?: string
  method?: HttpMethod
}

export interface IntegrationConfig {
  authentication?: AuthenticationType
  authConfig?: AuthenticationConfig
  endpoint?: string
  method?: HttpMethod
  parameters?: ApiParameter[]
  mcpServerUrl?: string
  mcpAuthToken?: string
}

export interface AuthenticationConfig {
  apiKeyHeader?: string
  apiKeyValue?: string
  bearerToken?: string
  username?: string
  password?: string
  oauthClientId?: string
  oauthClientSecret?: string
  oauthTokenUrl?: string
}

export interface ApiParameter {
  id: string
  name: string
  type: 'string' | 'number' | 'boolean'
  required: boolean
  description?: string
}

export interface PlatformIntegration {
  id: string
  name: string
  description: string
  icon: string
  category: string
  requiresAuth: boolean
  authType?: 'oauth' | 'manual'
  authFields: AuthField[]
}

export interface AuthField {
  name: string
  label: string
  type: 'text' | 'password' | 'url'
  placeholder: string
  required: boolean
}

export interface FileAttachment {
  id: string
  name: string
  type: string // MIME type
  size: number
  url: string // Data URL for preview
  publicUrl?: string // Public URL for API calls
}

export interface Message {
  id: string
  role: 'user' | 'agent' | 'system'
  content: string
  attachments?: FileAttachment[]
  toolCalls?: ToolCall[]
  timestamp: string
}

export interface ToolCall {
  toolId: string
  toolName: string
  input: Record<string, unknown>
  output?: unknown
  success: boolean
  error?: string
}
