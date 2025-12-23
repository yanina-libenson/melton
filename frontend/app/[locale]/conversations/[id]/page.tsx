'use client'

import { use, useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api/client'
import { ChevronLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Message {
  id: string
  role: string
  content: string
  tool_calls: Array<{
    tool_name: string
    input: Record<string, unknown>
    output: Record<string, unknown>
  }>
  created_at: string
}

interface ConversationDetail {
  id: string
  agent_id: string
  agent_name: string
  agent_instructions: string
  agent_model_config: Record<string, unknown>
  channel_type: string
  created_at: string
  updated_at: string
  messages: Message[]
}

export default function ConversationDetailPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>
}) {
  const router = useRouter()
  const resolvedParams = use(params)
  const [conversation, setConversation] = useState<ConversationDetail | null>(null)
  const [loading, setLoading] = useState(true)

  const loadConversation = useCallback(async () => {
    try {
      const data = await apiClient.getConversation(resolvedParams.id)
      setConversation(data)
    } catch (error) {
      console.error('Failed to load conversation:', error)
    } finally {
      setLoading(false)
    }
  }, [resolvedParams.id])

  useEffect(() => {
    loadConversation()
  }, [loadConversation])

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-muted-foreground">Loading conversation...</div>
      </div>
    )
  }

  if (!conversation) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-muted-foreground">Conversation not found</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-6xl p-6">
      {/* Header */}
      <div className="mb-8">
        <Button
          variant="ghost"
          onClick={() => router.push(`/${resolvedParams.locale}/conversations`)}
          className="mb-4"
        >
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back to Conversations
        </Button>

        <div className="flex items-center gap-4">
          <h1 className="text-3xl font-bold">{conversation.agent_name}</h1>
          <span className="bg-primary/10 text-primary rounded px-3 py-1 text-sm">
            {conversation.channel_type}
          </span>
        </div>
        <p className="text-muted-foreground mt-2">
          {new Date(conversation.created_at).toLocaleString()}
        </p>
      </div>

      {/* Agent System Prompt */}
      <div className="bg-card mb-8 rounded-lg border p-6">
        <h2 className="mb-4 text-lg font-semibold">Agent System Prompt</h2>
        <pre className="bg-muted rounded p-4 text-sm whitespace-pre-wrap">
          {conversation.agent_instructions}
        </pre>

        <h3 className="mt-4 mb-2 font-medium">Model Configuration</h3>
        <pre className="bg-muted rounded p-4 text-xs">
          {JSON.stringify(conversation.agent_model_config, null, 2)}
        </pre>
      </div>

      {/* Messages */}
      <div className="space-y-6">
        <h2 className="text-lg font-semibold">Messages</h2>

        {conversation.messages.map((message) => (
          <div
            key={message.id}
            className={`bg-card rounded-lg border p-6 ${
              message.role === 'user' ? 'border-blue-500/50' : 'border-green-500/50'
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
                {message.tool_calls.map((toolCall, idx) => (
                  <div key={idx} className="bg-muted rounded-lg p-4">
                    <div className="mb-2 text-sm font-medium">🔧 {toolCall.tool_name}</div>

                    <div className="space-y-2">
                      <div>
                        <div className="text-muted-foreground mb-1 text-xs">Input:</div>
                        <pre className="bg-background rounded p-2 text-xs">
                          {JSON.stringify(toolCall.input, null, 2)}
                        </pre>
                      </div>

                      <div>
                        <div className="text-muted-foreground mb-1 text-xs">Output:</div>
                        <pre className="bg-background max-h-40 overflow-auto rounded p-2 text-xs">
                          {JSON.stringify(toolCall.output, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
