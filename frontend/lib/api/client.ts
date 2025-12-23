/**
 * API Client for Dr. Melton Backend
 * Provides typed methods for all backend endpoints
 */

import type { Agent, IntegrationSource, Tool } from '@/lib/types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_VERSION = '/api/v1'

class APIError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    super(`API Error: ${status} ${statusText}`)
    this.name = 'APIError'
  }
}

class APIClient {
  private baseURL: string
  private token: string | null = null

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  setToken(token: string) {
    this.token = token
  }

  clearToken() {
    this.token = null
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => null)
      throw new APIError(response.status, response.statusText, errorData)
    }

    if (response.status === 204) {
      return null as T
    }

    return response.json()
  }

  // Agent endpoints
  async getAgents(): Promise<Agent[]> {
    return this.request(`${API_VERSION}/agents`)
  }

  async getAgent(agentId: string): Promise<Agent> {
    return this.request(`${API_VERSION}/agents/${agentId}`)
  }

  async createAgent(data: {
    name: string
    instructions: string
    status: 'active' | 'inactive' | 'draft'
    model_config: {
      provider: 'anthropic' | 'openai' | 'google'
      model: string
      temperature: number
      max_tokens: number
    }
  }): Promise<Agent> {
    return this.request(`${API_VERSION}/agents`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateAgent(
    agentId: string,
    data: Partial<{
      name: string
      instructions: string
      status: 'active' | 'inactive' | 'draft'
      model_config: {
        provider: 'anthropic' | 'openai' | 'google'
        model: string
        temperature: number
        max_tokens: number
      }
    }>
  ): Promise<Agent> {
    return this.request(`${API_VERSION}/agents/${agentId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async deleteAgent(agentId: string): Promise<void> {
    return this.request(`${API_VERSION}/agents/${agentId}`, {
      method: 'DELETE',
    })
  }

  // Integration endpoints
  async getIntegrations(agentId: string): Promise<IntegrationSource[]> {
    return this.request(`${API_VERSION}/agents/${agentId}/integrations`)
  }

  async createIntegration(data: {
    agent_id: string
    type: 'platform' | 'custom-tool' | 'sub-agent'
    name: string
    description?: string
    config: Record<string, unknown>
  }): Promise<IntegrationSource> {
    return this.request(`${API_VERSION}/integrations`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateIntegration(
    integrationId: string,
    data: Partial<{
      name: string
      description: string
      config: Record<string, unknown>
    }>
  ): Promise<IntegrationSource> {
    return this.request(`${API_VERSION}/integrations/${integrationId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async deleteIntegration(integrationId: string): Promise<void> {
    return this.request(`${API_VERSION}/integrations/${integrationId}`, {
      method: 'DELETE',
    })
  }

  // Tool endpoints
  async getTools(integrationId: string): Promise<Tool[]> {
    return this.request(`${API_VERSION}/integrations/${integrationId}/tools`)
  }

  async getTool(toolId: string): Promise<Tool> {
    return this.request(`${API_VERSION}/tools/${toolId}`)
  }

  async createTool(data: {
    integration_id: string
    name: string
    description?: string
    tool_type?: 'api' | 'llm' | 'sub-agent'
    tool_schema?: Record<string, unknown>
    config?: Record<string, unknown>
    is_enabled?: boolean
  }): Promise<Tool> {
    return this.request(`${API_VERSION}/tools`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateTool(
    toolId: string,
    data: Partial<{
      name: string
      description: string
      tool_schema: Record<string, unknown>
      config: Record<string, unknown>
      is_enabled: boolean
    }>
  ): Promise<Tool> {
    return this.request(`${API_VERSION}/tools/${toolId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async deleteTool(toolId: string): Promise<void> {
    return this.request(`${API_VERSION}/tools/${toolId}`, {
      method: 'DELETE',
    })
  }

  async testTool(data: {
    endpoint: string
    method: string
    authentication: string
    authConfig: Record<string, string>
    testInput: Record<string, string>
    outputMode: string
    outputMapping: Record<string, string>
    llmConfig?: { instructions: string }
  }): Promise<{
    success: boolean
    output: unknown
    error?: string
    debugInfo?: {
      executionTimeMs: number
      statusCode: number
      urlCalled: string
      rawResponse?: unknown
    }
  }> {
    return this.request(`${API_VERSION}/tools/test`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // User API Keys endpoints
  async getUserApiKeys(): Promise<{
    openai: { provider: string; is_configured: boolean; masked_key: string | null }
    anthropic: { provider: string; is_configured: boolean; masked_key: string | null }
    google: { provider: string; is_configured: boolean; masked_key: string | null }
  }> {
    return this.request(`${API_VERSION}/user-settings/api-keys`)
  }

  async updateUserApiKeys(data: {
    openai?: string | null
    anthropic?: string | null
    google?: string | null
  }): Promise<{
    openai: { provider: string; is_configured: boolean; masked_key: string | null }
    anthropic: { provider: string; is_configured: boolean; masked_key: string | null }
    google: { provider: string; is_configured: boolean; masked_key: string | null }
  }> {
    return this.request(`${API_VERSION}/user-settings/api-keys`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async deleteUserApiKey(provider: 'openai' | 'anthropic' | 'google'): Promise<{
    success: boolean
    message: string
  }> {
    return this.request(`${API_VERSION}/user-settings/api-keys/${provider}`, {
      method: 'DELETE',
    })
  }

  // Playground WebSocket
  createPlaygroundConnection(agentId: string): WebSocket {
    const wsURL = this.baseURL.replace('http', 'ws')
    return new WebSocket(`${wsURL}${API_VERSION}/playground/${agentId}`)
  }

  // Conversations endpoints
  async getConversations(
    limit = 50,
    offset = 0
  ): Promise<{
    conversations: Array<{
      id: string
      agent_id: string
      agent_name: string
      channel_type: string
      message_count: number
      preview: string
      created_at: string
      updated_at: string
    }>
    total: number
  }> {
    return this.request(`${API_VERSION}/conversations?limit=${limit}&offset=${offset}`)
  }

  async getConversation(conversationId: string): Promise<{
    id: string
    agent_id: string
    agent_name: string
    agent_instructions: string
    agent_model_config: Record<string, unknown>
    channel_type: string
    created_at: string
    updated_at: string
    messages: Array<{
      id: string
      role: string
      content: string
      tool_calls: Array<{
        tool_name: string
        input: Record<string, unknown>
        output: Record<string, unknown>
      }>
      created_at: string
    }>
  }> {
    return this.request(`${API_VERSION}/conversations/${conversationId}`)
  }

  // Generic GET method for custom endpoints
  async get<T = unknown>(endpoint: string): Promise<T> {
    return this.request(`${API_VERSION}${endpoint}`)
  }
}

// Export singleton instance
export const apiClient = new APIClient(API_BASE_URL)
export { APIError }
