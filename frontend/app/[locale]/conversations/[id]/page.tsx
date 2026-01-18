'use client'

import { use, useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api/client'
import { ChevronLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ConversationDetail {
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
          <h1 className="text-3xl font-bold">{conversation.title || 'Conversation'}</h1>
          <span className="bg-primary/10 text-primary rounded px-3 py-1 text-sm">
            {conversation.channel_type}
          </span>
          {conversation.is_archived && (
            <span className="rounded bg-gray-500/10 px-3 py-1 text-sm text-gray-500">Archived</span>
          )}
        </div>
        <p className="text-muted-foreground mt-2">
          Created: {new Date(conversation.created_at).toLocaleString()}
        </p>
        {conversation.last_message_preview && (
          <p className="text-muted-foreground mt-1 text-sm italic">
            {conversation.last_message_preview}
          </p>
        )}
      </div>

      {/* Conversation Details */}
      <div className="bg-card rounded-lg border p-6">
        <h2 className="mb-4 text-lg font-semibold">Conversation Details</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">ID:</span>
            <span className="font-mono">{conversation.id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Agent ID:</span>
            <span className="font-mono">{conversation.agent_id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Channel:</span>
            <span>{conversation.channel_type}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Last Updated:</span>
            <span>{new Date(conversation.updated_at).toLocaleString()}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
