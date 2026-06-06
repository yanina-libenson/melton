/**
 * React hook for audit event streaming via Server-Sent Events (SSE)
 * Provides real-time tool call and conversation updates for the audit page
 */

'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { apiClient } from '@/lib/api/client'

export interface AuditEvent {
  event: string
  data: {
    conversation_id: string
    agent_id: string
    agent_name: string | null
    timestamp: string
    tool_name?: string
    tool_description?: string | null
    tool_input?: Record<string, unknown>
    tool_success?: boolean
    duration_ms?: number
    tool_calls_count?: number
  }
}

export interface ActiveToolExecution {
  conversationId: string
  agentId: string
  agentName: string | null
  toolName: string
  toolDescription: string | null
  startedAt: string
}

interface UseAuditStreamOptions {
  enabled?: boolean
  onToolStart?: (event: AuditEvent) => void
  onToolComplete?: (event: AuditEvent) => void
  onConversationStart?: (event: AuditEvent) => void
  onMessageComplete?: (event: AuditEvent) => void
  onError?: (error: string) => void
}

export function useAuditStream({
  enabled = true,
  onToolStart,
  onToolComplete,
  onConversationStart,
  onMessageComplete,
  onError,
}: UseAuditStreamOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [activeTools, setActiveTools] = useState<Map<string, ActiveToolExecution>>(new Map())
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5

  const connect = useCallback(() => {
    if (!enabled) {
      return
    }

    // Get token from apiClient
    const token = apiClient.getToken()
    if (!token) {
      console.error('[AuditStream] No auth token available')
      onError?.('Authentication required for audit streaming')
      return
    }

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const url = `${baseUrl}/api/v1/audit/stream?token=${encodeURIComponent(token)}`

    try {
      const eventSource = new EventSource(url)
      eventSourceRef.current = eventSource

      eventSource.onopen = () => {
        console.log('[AuditStream] Connected')
        setIsConnected(true)
        reconnectAttemptsRef.current = 0
      }

      eventSource.onerror = (error) => {
        console.error('[AuditStream] Error:', error)
        setIsConnected(false)

        // Attempt reconnection with exponential backoff
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
          reconnectAttemptsRef.current++

          console.log(
            `[AuditStream] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`
          )

          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, delay)
        } else {
          onError?.('Lost connection to audit stream. Please refresh the page.')
        }
      }

      // Handle conversation_started events
      eventSource.addEventListener('conversation_started', (event) => {
        try {
          const data = JSON.parse(event.data)
          const auditEvent: AuditEvent = { event: 'conversation_started', data }
          onConversationStart?.(auditEvent)
        } catch (err) {
          console.error('[AuditStream] Error parsing conversation_started event:', err)
        }
      })

      // Handle tool_use_start events
      eventSource.addEventListener('tool_use_start', (event) => {
        try {
          const data = JSON.parse(event.data)
          const auditEvent: AuditEvent = { event: 'tool_use_start', data }

          // Track active tool execution
          const key = `${data.conversation_id}-${data.tool_name}`
          setActiveTools((prev) => {
            const next = new Map(prev)
            next.set(key, {
              conversationId: data.conversation_id,
              agentId: data.agent_id,
              agentName: data.agent_name,
              toolName: data.tool_name,
              toolDescription: data.tool_description || null,
              startedAt: data.timestamp,
            })
            return next
          })

          onToolStart?.(auditEvent)
        } catch (err) {
          console.error('[AuditStream] Error parsing tool_use_start event:', err)
        }
      })

      // Handle tool_use_complete events
      eventSource.addEventListener('tool_use_complete', (event) => {
        try {
          const data = JSON.parse(event.data)
          const auditEvent: AuditEvent = { event: 'tool_use_complete', data }

          // Remove from active tools
          const key = `${data.conversation_id}-${data.tool_name}`
          setActiveTools((prev) => {
            const next = new Map(prev)
            next.delete(key)
            return next
          })

          onToolComplete?.(auditEvent)
        } catch (err) {
          console.error('[AuditStream] Error parsing tool_use_complete event:', err)
        }
      })

      // Handle message_complete events
      eventSource.addEventListener('message_complete', (event) => {
        try {
          const data = JSON.parse(event.data)
          const auditEvent: AuditEvent = { event: 'message_complete', data }
          onMessageComplete?.(auditEvent)
        } catch (err) {
          console.error('[AuditStream] Error parsing message_complete event:', err)
        }
      })
    } catch (err) {
      console.error('[AuditStream] Failed to create EventSource:', err)
      onError?.('Failed to connect to audit stream')
    }
  }, [enabled, onToolStart, onToolComplete, onConversationStart, onMessageComplete, onError])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }

    setIsConnected(false)
    setActiveTools(new Map())
    reconnectAttemptsRef.current = 0
  }, [])

  // Auto-connect on mount
  useEffect(() => {
    if (enabled) {
      connect()
    }

    return () => {
      disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled])

  return {
    isConnected,
    activeTools: Array.from(activeTools.values()),
    connect,
    disconnect,
  }
}
