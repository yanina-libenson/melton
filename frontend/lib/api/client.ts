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

  // Integration endpoints (to be implemented)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  async getIntegrations(_agentId: string): Promise<IntegrationSource[]> {
    // TODO: Implement when backend endpoint is ready
    return []
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  async createIntegration(_data: {
    agent_id: string
    type: 'platform' | 'custom-tool' | 'sub-agent'
    name: string
    description?: string
    config: Record<string, unknown>
  }): Promise<IntegrationSource> {
    // TODO: Implement when backend endpoint is ready
    throw new Error('Not implemented')
  }

  // Tool endpoints (to be implemented)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  async getTools(_integrationId: string): Promise<Tool[]> {
    // TODO: Implement when backend endpoint is ready
    return []
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
}

// Export singleton instance
export const apiClient = new APIClient(API_BASE_URL)
export { APIError }
