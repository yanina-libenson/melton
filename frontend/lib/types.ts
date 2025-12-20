// Core data types for the application

export type AgentStatus = 'active' | 'inactive' | 'draft'

export type AuthenticationType = 'none' | 'api-key' | 'bearer' | 'basic' | 'oauth'

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'

export type IntegrationSourceType = 'platform' | 'custom-tool' | 'sub-agent'

export type CustomToolType = 'api' | 'llm'

export interface Agent {
  id: string
  name: string
  instructions: string
  status: AgentStatus
  createdAt: string
  updatedAt: string
  integrations: IntegrationSource[]
}

export interface IntegrationSource {
  id: string
  name: string
  type: IntegrationSourceType
  description: string
  icon?: string
  platformId?: string
  config: IntegrationConfig
  availableTools: Tool[]
  enabledToolIds: string[]
}

export interface Tool {
  id: string
  name: string
  description: string
  sourceId: string
  toolType?: CustomToolType | 'sub-agent'
  // LLM configuration (for llm and api-llm types)
  llmModel?: 'gpt-4' | 'claude-sonnet-4' | 'claude-opus-4'
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
  authFields: AuthField[]
}

export interface AuthField {
  name: string
  label: string
  type: 'text' | 'password' | 'url'
  placeholder: string
  required: boolean
}

export interface Message {
  id: string
  role: 'user' | 'agent' | 'system'
  content: string
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
