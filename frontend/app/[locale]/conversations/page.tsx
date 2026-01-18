'use client'

import { use, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { apiClient } from '@/lib/api/client'
import useSWR from 'swr'
import type { Agent } from '@/lib/types'
import { useAuth } from '@/lib/contexts/auth-context'

interface Conversation {
  id: string
  agent_id: string
  user_id: string | null
  channel_type: string
  title: string | null
  is_archived: boolean
  last_message_preview: string | null
  created_at: string
  updated_at: string
}

interface ConversationWithAgent extends Conversation {
  agent?: Agent
}

export default function ConversationsPage({ params }: { params: Promise<{ locale: string }> }) {
  const router = useRouter()
  const resolvedParams = use(params)
  const { isAuthenticated, isLoading: authLoading } = useAuth()

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/auth')
    }
  }, [isAuthenticated, authLoading, router])

  // Fetch conversations
  const {
    data: conversations,
    error,
    isLoading,
  } = useSWR<Conversation[]>('/conversations', () => apiClient.getConversations(false))

  // Fetch agents for each conversation
  const { data: agents } = useSWR<Agent[]>('/agents', () => apiClient.getAgents())

  // Merge conversations with agent data
  const conversationsWithAgents: ConversationWithAgent[] =
    conversations?.map((conv) => ({
      ...conv,
      agent: agents?.find((agent) => agent.id === conv.agent_id),
    })) || []

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-muted-foreground">Loading conversations...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-destructive">Failed to load conversations</div>
      </div>
    )
  }

  return (
    <div className="bg-background min-h-screen">
      <div className="mx-auto max-w-5xl px-8 py-16">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-foreground mb-2 text-4xl font-semibold tracking-tight">
            Conversations
          </h1>
          <p className="text-muted-foreground text-sm">View and manage your agent conversations</p>
        </div>

        {conversationsWithAgents.length === 0 ? (
          <div className="border-border bg-card rounded-xl border p-12 text-center">
            <p className="text-muted-foreground">No conversations yet</p>
            <p className="text-muted-foreground mt-2 text-xs">
              Start chatting with your agents to see your conversation history
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {conversationsWithAgents.map((conv) => (
              <Link
                key={conv.id}
                href={`/${resolvedParams.locale}/agents/${conv.agent_id}?mode=use&conversation_id=${conv.id}`}
                className="border-border bg-card hover:shadow-soft-lg group block rounded-xl border p-6 transition-all duration-200"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="mb-2 flex items-center gap-3">
                      <h3 className="text-foreground group-hover:text-primary text-lg font-semibold transition-colors">
                        {conv.title || 'New Conversation'}
                      </h3>
                    </div>
                    {conv.agent && (
                      <p className="text-muted-foreground mb-3 text-sm">with {conv.agent.name}</p>
                    )}
                    <div className="flex items-center gap-3">
                      <span className="text-muted-foreground text-xs">
                        {new Date(conv.updated_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
