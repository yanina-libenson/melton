'use client'

import { useState } from 'react'
import { mockConversations, mockAgents } from '@/lib/mock-data'
import { Conversation } from '@/lib/types'

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))

  if (diffInHours < 1) return 'Just now'
  if (diffInHours < 24) return `${diffInHours} hours ago`
  if (diffInHours < 48) return 'Yesterday'

  const diffInDays = Math.floor(diffInHours / 24)
  if (diffInDays < 7) return `${diffInDays} days ago`

  return date.toLocaleDateString()
}

export default function ConversationsPage() {
  const [conversations] = useState<Conversation[]>(mockConversations)
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(
    conversations[0] || null
  )

  function getAgentName(agentId: string): string {
    const agent = mockAgents.find((a) => a.id === agentId)
    return agent?.name || 'Unknown Agent'
  }

  return (
    <div className="bg-background flex h-screen flex-col">
      {/* Header */}
      <div className="border-border border-b px-8 py-6">
        <div className="mx-auto max-w-7xl">
          <h1 className="text-foreground text-3xl font-semibold tracking-tight">Conversations</h1>
          <p className="text-muted-foreground mt-1 text-sm">Customer interactions</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <div className="mx-auto flex h-full max-w-7xl">
          {/* Conversations List */}
          <div className="border-border w-96 overflow-y-auto border-r">
            <div className="space-y-2 p-4">
              {conversations.map((conversation) => {
                const lastMessage = conversation.messages[conversation.messages.length - 1]
                const isSelected = selectedConversation?.id === conversation.id

                return (
                  <div
                    key={conversation.id}
                    className={`cursor-pointer rounded-xl p-4 transition-all duration-200 ease-out ${
                      isSelected
                        ? 'bg-primary/5 border-primary shadow-soft-sm border'
                        : 'border-border bg-card shadow-soft-xs hover:shadow-soft-sm border hover:-translate-y-0.5'
                    }`}
                    onClick={() => setSelectedConversation(conversation)}
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <p className="text-foreground text-sm font-medium">
                        {getAgentName(conversation.agentId)}
                      </p>
                      <p className="text-muted-foreground text-xs" suppressHydrationWarning>
                        {formatDate(conversation.createdAt)}
                      </p>
                    </div>
                    <p className="text-muted-foreground truncate text-xs">
                      {lastMessage?.content || 'No messages'}
                    </p>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Conversation Detail */}
          <div className="flex flex-1 flex-col">
            {selectedConversation ? (
              <>
                <div className="border-border border-b px-8 py-4">
                  <p className="text-muted-foreground text-sm" suppressHydrationWarning>
                    {getAgentName(selectedConversation.agentId)} •{' '}
                    {formatDate(selectedConversation.createdAt)}
                  </p>
                </div>
                <div className="flex-1 overflow-y-auto px-8">
                  <div className="mx-auto max-w-4xl">
                    <div className="space-y-6 py-8">
                      {selectedConversation.messages.map((message) => (
                        <div key={message.id}>
                          {message.role === 'system' ? (
                            <div className="flex justify-center">
                              <p className="text-muted-foreground text-xs font-light">
                                {message.content}
                              </p>
                            </div>
                          ) : (
                            <div
                              className={`flex ${
                                message.role === 'user' ? 'justify-end' : 'justify-start'
                              }`}
                            >
                              <div
                                className={`max-w-[70%] rounded-xl px-6 py-4 ${
                                  message.role === 'user'
                                    ? 'bg-primary text-primary-foreground shadow-soft-sm'
                                    : 'bg-card text-foreground border-border shadow-soft-xs border'
                                }`}
                              >
                                <p className="whitespace-pre-wrap">{message.content}</p>

                                {message.toolCalls && message.toolCalls.length > 0 && (
                                  <div className="border-border mt-4 border-t pt-4">
                                    {message.toolCalls.map((toolCall, idx) => (
                                      <div
                                        key={idx}
                                        className="bg-background text-foreground border-border mb-2 rounded border p-3 text-xs"
                                      >
                                        <p className="text-muted-foreground">
                                          Used {toolCall.toolName}
                                        </p>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex flex-1 items-center justify-center">
                <p className="text-muted-foreground font-light">Select a conversation</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
