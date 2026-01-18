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

  getToken(): string | null {
    return this.token
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'ngrok-skip-browser-warning': 'true', // Bypass ngrok browser warning page
      ...(options.headers as Record<string, string>),
    }

    // Use token from instance, or fall back to localStorage (resilient to hot reload)
    const token =
      this.token ||
      (typeof window !== 'undefined' ? localStorage.getItem('melton_auth_token') : null)
    if (token) {
      headers['Authorization'] = `Bearer ${token}`

      // If token was from localStorage, sync it to instance
      if (!this.token && token) {
        console.log('[APIClient] Token recovered from localStorage')
        this.token = token
      }
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

  // Auth endpoints
  async register(data: {
    email: string
    password: string
    full_name?: string
  }): Promise<{ access_token: string; token_type: string }> {
    return this.request(`${API_VERSION}/auth/register`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async login(data: {
    email: string
    password: string
  }): Promise<{ access_token: string; token_type: string }> {
    return this.request(`${API_VERSION}/auth/login`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getCurrentUser(): Promise<{
    id: string
    email: string
    subdomain: string | null
    full_name: string | null
    is_active: boolean
    created_at: string
    updated_at: string
  }> {
    return this.request(`${API_VERSION}/auth/me`)
  }

  async claimSubdomain(subdomain: string): Promise<{
    id: string
    email: string
    subdomain: string | null
    full_name: string | null
    is_active: boolean
    created_at: string
    updated_at: string
  }> {
    return this.request(`${API_VERSION}/auth/subdomain/claim`, {
      method: 'POST',
      body: JSON.stringify({ subdomain }),
    })
  }

  async checkSubdomainAvailability(subdomain: string): Promise<{
    subdomain: string
    available: boolean
    reason: string | null
  }> {
    return this.request(`${API_VERSION}/auth/subdomain/check/${subdomain}`)
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

  async getIntegration(integrationId: string): Promise<IntegrationSource> {
    return this.request(`${API_VERSION}/integrations/${integrationId}`)
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

  // LLM Models endpoints
  async getLLMModels(): Promise<import('@/lib/types').LLMModel[]> {
    return this.request(`${API_VERSION}/llm-models`)
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

  // Upload endpoints
  async uploadImage(formData: FormData): Promise<{
    success: boolean
    url: string
    filename: string
    size: number
  }> {
    const url = `${this.baseURL}${API_VERSION}/uploads/image`

    const headers: Record<string, string> = {
      'ngrok-skip-browser-warning': 'true', // Bypass ngrok browser warning page
    }

    // Use token from instance, or fall back to localStorage (resilient to hot reload)
    const token =
      this.token ||
      (typeof window !== 'undefined' ? localStorage.getItem('melton_auth_token') : null)
    if (token) {
      headers['Authorization'] = `Bearer ${token}`

      // If token was from localStorage, sync it to instance
      if (!this.token && token) {
        console.log('[APIClient] Token recovered from localStorage (uploadImage)')
        this.token = token
      }
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => null)
      throw new APIError(response.status, response.statusText, errorData)
    }

    return response.json()
  }

  // Playground WebSocket
  createPlaygroundConnection(agentId: string): WebSocket {
    const wsURL = this.baseURL.replace('http', 'ws')
    const token = this.token || this.getToken()
    if (!token) {
      throw new Error('Authentication required for playground')
    }
    return new WebSocket(
      `${wsURL}${API_VERSION}/playground/${agentId}?token=${encodeURIComponent(token)}`
    )
  }

  // Conversations endpoints
  async getConversations(
    includeArchived = false,
    limit = 50
  ): Promise<
    Array<{
      id: string
      agent_id: string
      user_id: string | null
      channel_type: string
      title: string | null
      is_archived: boolean
      last_message_preview: string | null
      created_at: string
      updated_at: string
    }>
  > {
    return this.request(
      `${API_VERSION}/conversations?include_archived=${includeArchived}&limit=${limit}`
    )
  }

  async getConversation(conversationId: string): Promise<{
    id: string
    agent_id: string
    user_id: string | null
    channel_type: string
    title: string | null
    is_archived: boolean
    last_message_preview: string | null
    created_at: string
    updated_at: string
  }> {
    return this.request(`${API_VERSION}/conversations/${conversationId}`)
  }

  async getConversationMessages(
    conversationId: string,
    limit = 50
  ): Promise<{
    messages: Array<{
      role: string
      content: string
    }>
  }> {
    return this.request(`${API_VERSION}/conversations/${conversationId}/messages?limit=${limit}`)
  }

  async updateConversation(
    conversationId: string,
    updates: { title?: string; is_archived?: boolean }
  ): Promise<{
    id: string
    agent_id: string
    user_id: string | null
    channel_type: string
    title: string | null
    is_archived: boolean
    last_message_preview: string | null
    created_at: string
    updated_at: string
  }> {
    return this.request(`${API_VERSION}/conversations/${conversationId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    })
  }

  async deleteConversation(conversationId: string): Promise<{ message: string }> {
    return this.request(`${API_VERSION}/conversations/${conversationId}`, {
      method: 'DELETE',
    })
  }

  async getAuditTrail(limit = 100): Promise<{ conversations: unknown[] }> {
    return this.request(`${API_VERSION}/conversations/audit/all?limit=${limit}`)
  }

  // Permission endpoints
  async grantPermission(
    agentId: string,
    userEmail: string,
    permissionType: 'use' | 'admin'
  ): Promise<{
    user_id: string
    email: string
    full_name: string | null
    permission_type: string
    granted_at: string
    granted_by: string
  }> {
    return this.request(`${API_VERSION}/agents/${agentId}/permissions`, {
      method: 'POST',
      body: JSON.stringify({ user_email: userEmail, permission_type: permissionType }),
    })
  }

  async listAgentPermissions(agentId: string): Promise<
    Array<{
      user_id: string
      email: string
      full_name: string | null
      permission_type: string
      granted_at: string
      granted_by: string
    }>
  > {
    return this.request(`${API_VERSION}/agents/${agentId}/permissions`)
  }

  async revokePermission(agentId: string, userId: string): Promise<void> {
    return this.request(`${API_VERSION}/agents/${agentId}/permissions/${userId}`, {
      method: 'DELETE',
    })
  }

  async generateShareCode(agentId: string): Promise<{
    share_code: string
    share_url: string
  }> {
    return this.request(`${API_VERSION}/agents/${agentId}/share-code`, {
      method: 'POST',
    })
  }

  async revokeShareCode(agentId: string): Promise<void> {
    return this.request(`${API_VERSION}/agents/${agentId}/share-code`, {
      method: 'DELETE',
    })
  }

  async acceptShareCode(shareCode: string): Promise<{
    agent_id: string
    agent_name: string
    message: string
  }> {
    return this.request(`${API_VERSION}/share/accept`, {
      method: 'POST',
      body: JSON.stringify({ share_code: shareCode }),
    })
  }

  async listSharedAgents(): Promise<Array<import('@/lib/types').Agent>> {
    return this.request(`${API_VERSION}/shared/agents`)
  }

  async getUserPermission(agentId: string): Promise<{
    has_permission: boolean
    permission_type: 'admin' | 'use' | null
  }> {
    return this.request(`${API_VERSION}/agents/${agentId}/my-permission`)
  }

  // Generic GET method for custom endpoints
  async get<T = unknown>(endpoint: string): Promise<T> {
    return this.request(`${API_VERSION}${endpoint}`)
  }
}

// Export singleton instance
export const apiClient = new APIClient(API_BASE_URL)
export { APIError }
