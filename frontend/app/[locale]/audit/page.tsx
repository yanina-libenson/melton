'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api/client'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useAuth } from '@/lib/contexts/auth-context'

interface ExecutionTrace {
  id: string
  step_type: string
  step_data: Record<string, unknown>
  duration_ms: number | null
  created_at: string
}

interface ToolCall {
  name?: string
  toolName?: string
  input?: Record<string, unknown>
  parameters?: Record<string, unknown>
  output?: unknown
}

interface Message {
  id: string
  role: string
  content: string
  tool_calls: ToolCall[]
  metadata: Record<string, unknown> | null
  traces: ExecutionTrace[]
  created_at: string
}

interface AuditConversation {
  conversation_id: string
  agent_id: string
  agent_name: string | null
  agent_instructions: string | null
  agent_model_config: Record<string, unknown> | null
  channel_type: string
  title: string | null
  user: {
    user_id: string
    email: string
    full_name: string | null
  } | null
  messages: Message[]
  message_count: number
  created_at: string
  updated_at: string
  is_archived: boolean
}

export default function AuditPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const [conversations, setConversations] = useState<AuditConversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedConversations, setExpandedConversations] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/auth')
    }
  }, [isAuthenticated, authLoading, router])

  useEffect(() => {
    if (isAuthenticated) {
      loadAuditTrail()
    }
  }, [isAuthenticated])

  const loadAuditTrail = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getAuditTrail()
      setConversations(response.conversations as AuditConversation[])
      setError(null)
    } catch (err) {
      console.error('Failed to load audit trail:', err)
      setError('Failed to load audit trail')
    } finally {
      setLoading(false)
    }
  }

  const toggleConversation = (conversationId: string) => {
    const newExpanded = new Set(expandedConversations)
    if (newExpanded.has(conversationId)) {
      newExpanded.delete(conversationId)
    } else {
      newExpanded.add(conversationId)
    }
    setExpandedConversations(newExpanded)
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-muted-foreground">Loading audit trail...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-destructive">{error}</div>
      </div>
    )
  }

  return (
    <div className="bg-background min-h-screen">
      <div className="mx-auto max-w-7xl px-8 py-16">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-foreground mb-2 text-4xl font-semibold tracking-tight">
            Audit Trail
          </h1>
          <p className="text-muted-foreground text-sm">
            Monitor all conversations across your agents
          </p>
        </div>

        {conversations.length === 0 ? (
          <div className="border-border bg-card rounded-xl border p-12 text-center">
            <p className="text-muted-foreground">No conversations to audit</p>
            <p className="text-muted-foreground mt-2 text-xs">
              Conversations from agents you own or manage will appear here
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {conversations.map((conv) => {
              const isExpanded = expandedConversations.has(conv.conversation_id)
              return (
                <div
                  key={conv.conversation_id}
                  className="border-border bg-card overflow-hidden rounded-xl border"
                >
                  {/* Conversation Header */}
                  <div
                    onClick={() => toggleConversation(conv.conversation_id)}
                    className="hover:bg-muted/50 flex cursor-pointer items-center justify-between p-6 transition-colors"
                  >
                    <div className="flex-1">
                      <div className="mb-2 flex items-center gap-3">
                        {isExpanded ? (
                          <ChevronDown className="text-muted-foreground h-5 w-5" />
                        ) : (
                          <ChevronRight className="text-muted-foreground h-5 w-5" />
                        )}
                        <h3 className="text-foreground text-lg font-semibold">
                          {conv.title || 'Untitled Conversation'}
                        </h3>
                        <span className="bg-primary/10 text-primary rounded-full px-2 py-0.5 text-xs">
                          {conv.message_count} messages
                        </span>
                      </div>
                      <div className="ml-8 flex items-center gap-4 text-sm">
                        <span className="text-muted-foreground">
                          <span className="font-medium">Agent:</span> {conv.agent_name}
                        </span>
                        {conv.user && (
                          <span className="text-muted-foreground">
                            <span className="font-medium">User:</span> {conv.user.email}
                          </span>
                        )}
                        <span className="text-muted-foreground">
                          {new Date(conv.updated_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Expanded Conversation - Original Format */}
                  {isExpanded && (
                    <div className="border-border bg-muted/20 border-t">
                      <div className="p-6">
                        {/* Agent System Prompt */}
                        <div className="bg-card mb-8 rounded-lg border p-6">
                          <h2 className="mb-4 text-lg font-semibold">Agent System Prompt</h2>
                          <pre className="bg-muted rounded p-4 text-sm whitespace-pre-wrap">
                            {conv.agent_instructions || 'No instructions'}
                          </pre>

                          <h3 className="mt-4 mb-2 font-medium">Model Configuration</h3>
                          <pre className="bg-muted rounded p-4 text-xs">
                            {JSON.stringify(conv.agent_model_config, null, 2)}
                          </pre>
                        </div>

                        {/* Messages */}
                        <div className="space-y-6">
                          <h2 className="text-lg font-semibold">Messages</h2>

                          {conv.messages.length === 0 ? (
                            <p className="text-muted-foreground text-sm">
                              No messages in this conversation
                            </p>
                          ) : (
                            conv.messages.map((message) => (
                              <div
                                key={message.id}
                                className={`bg-card rounded-lg border p-6 ${
                                  message.role === 'user'
                                    ? 'border-blue-500/50'
                                    : 'border-green-500/50'
                                }`}
                              >
                                <div className="mb-3 flex items-center justify-between">
                                  <div className="flex items-center gap-3">
                                    <span
                                      className={`rounded px-2 py-1 text-xs font-medium ${
                                        message.role === 'user'
                                          ? 'bg-blue-500/10 text-blue-500'
                                          : 'bg-green-500/10 text-green-500'
                                      }`}
                                    >
                                      {message.role}
                                    </span>
                                    <span className="text-muted-foreground text-xs">
                                      {new Date(message.created_at).toLocaleTimeString()}
                                    </span>
                                  </div>
                                </div>

                                {/* Message Content */}
                                {message.content && (
                                  <div className="mb-4">
                                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                                  </div>
                                )}

                                {/* Tool Calls */}
                                {message.tool_calls && message.tool_calls.length > 0 && (
                                  <div className="space-y-3">
                                    <h4 className="text-muted-foreground text-xs font-medium uppercase">
                                      Tool Calls ({message.tool_calls.length})
                                    </h4>
                                    {message.tool_calls.map((toolCall, idx: number) => (
                                      <div key={idx} className="bg-muted rounded-lg p-4">
                                        <div className="mb-2 text-sm font-medium">
                                          🔧 {toolCall.name || toolCall.toolName || 'Tool'}
                                        </div>

                                        <div className="space-y-2">
                                          <div>
                                            <div className="text-muted-foreground mb-1 text-xs">
                                              Input:
                                            </div>
                                            <pre className="bg-background rounded p-2 text-xs">
                                              {JSON.stringify(
                                                toolCall.input || toolCall.parameters || toolCall,
                                                null,
                                                2
                                              )}
                                            </pre>
                                          </div>

                                          {toolCall.output !== undefined && (
                                            <div>
                                              <div className="text-muted-foreground mb-1 text-xs">
                                                Output:
                                              </div>
                                              <pre className="bg-background max-h-40 overflow-auto rounded p-2 text-xs">
                                                {JSON.stringify(toolCall.output, null, 2) || ''}
                                              </pre>
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {/* Execution Traces */}
                                {message.traces && message.traces.length > 0 && (
                                  <div className="mt-4 space-y-3">
                                    <h4 className="text-muted-foreground text-xs font-medium uppercase">
                                      Execution Traces ({message.traces.length})
                                    </h4>
                                    {message.traces.map((trace) => (
                                      <div key={trace.id} className="bg-muted rounded-lg p-4">
                                        <div className="mb-2 flex items-center justify-between">
                                          <div className="text-sm font-medium">
                                            {trace.step_type}
                                          </div>
                                          {trace.duration_ms && (
                                            <span className="text-muted-foreground text-xs">
                                              {trace.duration_ms}ms
                                            </span>
                                          )}
                                        </div>

                                        <div>
                                          <div className="text-muted-foreground mb-1 text-xs">
                                            Step Data:
                                          </div>
                                          <pre className="bg-background max-h-40 overflow-auto rounded p-2 text-xs">
                                            {JSON.stringify(trace.step_data, null, 2)}
                                          </pre>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
