/**
 * React hook for playground WebSocket connection
 * Handles streaming responses and tool calls
 */

'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { apiClient } from '@/lib/api/client'
import type { Message } from '@/lib/types'

interface PlaygroundEvent {
  type: string
  [key: string]: unknown
}

interface UsePlaygroundOptions {
  agentId: string
  enabled?: boolean
  onMessage?: (message: Message) => void
  onError?: (error: string, settingsUrl?: string) => void
}

export function usePlayground({
  agentId,
  enabled = true,
  onMessage,
  onError,
}: UsePlaygroundOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentResponse, setCurrentResponse] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const currentResponseRef = useRef<string>('')

  const connect = useCallback(() => {
    if (!enabled || !agentId) {
      return
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const ws = apiClient.createPlaygroundConnection(agentId)

      ws.onopen = () => {
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const data: PlaygroundEvent = JSON.parse(event.data)

          switch (data.type) {
            case 'agent_loaded':
              console.log('Agent loaded:', data.agent_id)
              break

            case 'conversation_started':
              console.log('Conversation started:', data.conversation_id)
              setConversationId(data.conversation_id as string)
              break

            case 'content_delta':
              setIsStreaming(true)
              const newContent = currentResponseRef.current + (data.delta as string)
              currentResponseRef.current = newContent
              setCurrentResponse(newContent)
              break

            case 'tool_use_start':
              console.log('Tool call started:', data.tool_name)
              break

            case 'tool_use_complete':
              console.log('Tool call completed:', data.tool_name, data.result)
              break

            case 'message_complete':
              setIsStreaming(false)
              if (onMessage && currentResponseRef.current) {
                const message: Message = {
                  id: data.message_id as string,
                  role: 'agent',
                  content: currentResponseRef.current,
                  timestamp: new Date().toISOString(),
                }
                onMessage(message)
              }
              currentResponseRef.current = ''
              setCurrentResponse('')
              break

            case 'error':
              setIsStreaming(false)
              if (onError) {
                onError(data.error as string, data.settings_url as string | undefined)
              }
              break
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setIsConnected(false)
      }

      ws.onclose = (event) => {
        setIsConnected(false)
        setIsStreaming(false)

        // Only show error if connection closed unexpectedly (not a clean close)
        if (!event.wasClean && onError) {
          onError('Connection error')
        }
      }

      wsRef.current = ws
    } catch (err) {
      console.error('Failed to create WebSocket connection:', err)
      if (onError) {
        onError('Failed to connect')
      }
    }
  }, [enabled, agentId, onMessage, onError])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
    setIsStreaming(false)
    setConversationId(null)
    currentResponseRef.current = ''
    setCurrentResponse('')
  }, [])

  const sendMessage = useCallback(
    (content: string, explicitConversationId?: string) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        if (onError) {
          onError('Not connected')
        }
        return
      }

      const message = {
        type: 'user_message',
        content,
        conversation_id: explicitConversationId || conversationId || null,
      }

      wsRef.current.send(JSON.stringify(message))

      // Create user message for UI
      if (onMessage) {
        onMessage({
          id: `msg-${Date.now()}`,
          role: 'user',
          content,
          timestamp: new Date().toISOString(),
        })
      }
    },
    [conversationId, onMessage, onError]
  )

  // Auto-connect on mount (only if enabled)
  useEffect(() => {
    if (enabled && agentId) {
      connect()
    }
    return () => {
      disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, agentId])

  return {
    isConnected,
    isStreaming,
    currentResponse,
    sendMessage,
    connect,
    disconnect,
  }
}
