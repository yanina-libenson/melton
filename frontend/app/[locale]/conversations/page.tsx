'use client'

import { use, useEffect, useState } from 'react'
import Link from 'next/link'
import { apiClient } from '@/lib/api/client'

interface Conversation {
  id: string
  agent_id: string
  agent_name: string
  channel_type: string
  message_count: number
  preview: string
  created_at: string
  updated_at: string
}

export default function ConversationsPage({ params }: { params: Promise<{ locale: string }> }) {
  const resolvedParams = use(params)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadConversations()
  }, [])

  async function loadConversations() {
    try {
      const data = await apiClient.getConversations()
      setConversations(data.conversations)
    } catch (error) {
      console.error('Failed to load conversations:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-muted-foreground">Loading conversations...</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-6xl p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Conversations</h1>
        <p className="text-muted-foreground mt-2">Debug and view all agent conversations</p>
      </div>

      {conversations.length === 0 ? (
        <div className="bg-muted rounded-lg border p-12 text-center">
          <p className="text-muted-foreground">No conversations yet</p>
        </div>
      ) : (
        <div className="space-y-4">
          {conversations.map((conv) => (
            <Link
              key={conv.id}
              href={`/${resolvedParams.locale}/conversations/${conv.id}`}
              className="bg-card hover:bg-accent block rounded-lg border p-6 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="font-medium">{conv.agent_name}</h3>
                    <span className="bg-primary/10 text-primary rounded px-2 py-0.5 text-xs">
                      {conv.channel_type}
                    </span>
                    <span className="text-muted-foreground text-xs">
                      {conv.message_count} messages
                    </span>
                  </div>
                  <p className="text-muted-foreground mt-2 text-sm">{conv.preview}</p>
                  <p className="text-muted-foreground mt-2 text-xs">
                    {new Date(conv.updated_at).toLocaleString()}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
