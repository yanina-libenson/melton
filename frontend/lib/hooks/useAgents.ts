/**
 * React hooks for agent data management
 * Uses SWR for caching and revalidation
 */

'use client'

import useSWR from 'swr'
import { apiClient, APIError } from '@/lib/api/client'
import type { Agent } from '@/lib/types'

export function useAgents(shouldFetch: boolean = true) {
  const { data, error, isLoading, mutate } = useSWR<Agent[]>(
    shouldFetch ? '/agents' : null,
    () => apiClient.getAgents(),
    {
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
    }
  )

  return {
    agents: data,
    isLoading,
    isError: error,
    mutate,
  }
}

export function useAgent(agentId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<Agent>(
    agentId ? `/agents/${agentId}` : null,
    agentId ? () => apiClient.getAgent(agentId) : null,
    {
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
    }
  )

  return {
    agent: data,
    isLoading,
    isError: error,
    mutate,
  }
}

export function useAgentMutations() {
  async function createAgent(data: {
    name: string
    instructions: string
    status: 'active' | 'inactive' | 'draft'
    model_config: {
      provider: 'anthropic' | 'openai' | 'google'
      model: string
      temperature: number
      max_tokens: number
    }
  }) {
    try {
      const agent = await apiClient.createAgent(data)
      return { success: true, data: agent }
    } catch (error) {
      if (error instanceof APIError) {
        return { success: false, error: error.message }
      }
      return { success: false, error: 'Failed to create agent' }
    }
  }

  async function updateAgent(
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
  ) {
    try {
      const agent = await apiClient.updateAgent(agentId, data)
      return { success: true, data: agent }
    } catch (error) {
      if (error instanceof APIError) {
        return { success: false, error: error.message }
      }
      return { success: false, error: 'Failed to update agent' }
    }
  }

  async function deleteAgent(agentId: string) {
    try {
      await apiClient.deleteAgent(agentId)
      return { success: true }
    } catch (error) {
      if (error instanceof APIError) {
        return { success: false, error: error.message }
      }
      return { success: false, error: 'Failed to delete agent' }
    }
  }

  return {
    createAgent,
    updateAgent,
    deleteAgent,
  }
}
