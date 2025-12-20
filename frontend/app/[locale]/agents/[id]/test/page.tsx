'use client'

import { useState, use, useRef, useEffect } from 'react'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { mockAgents } from '@/lib/mock-data'
import { Agent, Message } from '@/lib/types'

export default function TestPlaygroundPage({ params }: { params: Promise<{ id: string }> }) {
  const t = useTranslations('test')
  const tCommon = useTranslations('common')
  const resolvedParams = use(params)
  const [agent] = useState<Agent | null>(() => {
    return mockAgents.find((a) => a.id === resolvedParams.id) || null
  })

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-welcome',
      role: 'system',
      content: t('welcomeMessage'),
      timestamp: new Date().toISOString(),
    },
  ])

  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  function scrollToBottom() {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  async function handleSendMessage() {
    if (!inputMessage.trim() || isLoading) return

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    setTimeout(() => {
      const agentResponse: Message = {
        id: `msg-${Date.now()}-response`,
        role: 'agent',
        content: t('mockResponse', { agentName: agent?.name || 'Agent' }),
        timestamp: new Date().toISOString(),
      }

      const allEnabledTools =
        agent?.integrations.flatMap((integration) =>
          integration.availableTools.filter((tool) => integration.enabledToolIds.includes(tool.id))
        ) || []

      if (allEnabledTools.length > 0 && Math.random() > 0.5) {
        const randomTool = allEnabledTools[0]
        if (randomTool) {
          agentResponse.toolCalls = [
            {
              toolId: randomTool.id,
              toolName: randomTool.name,
              input: { example: 'parameter' },
              output: { status: 'success', data: 'Mock API response' },
              success: true,
            },
          ]
        }
      }

      setMessages((prev) => [...prev, agentResponse])
      setIsLoading(false)
    }, 1000)
  }

  function handleKeyPress(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  if (!agent) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-muted-foreground font-light">{t('agentNotFound')}</p>
      </div>
    )
  }

  return (
    <div className="bg-background flex h-screen flex-col">
      {/* Header */}
      <div className="border-border border-b px-8 py-6">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div>
            <h1 className="text-foreground text-3xl font-semibold tracking-tight">
              {t('title', { agentName: agent.name })}
            </h1>
            <p className="text-muted-foreground mt-1 text-sm">{t('subtitle')}</p>
          </div>
          <Link href={`/agents/${agent.id}`}>
            <Button variant="ghost">{tCommon('back')}</Button>
          </Link>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto px-8">
          <div className="mx-auto max-w-4xl">
            <div className="space-y-6 py-8">
              {messages.map((message) => (
                <div key={message.id}>
                  {message.role === 'system' ? (
                    <div className="flex justify-center">
                      <p className="text-muted-foreground text-xs font-light">{message.content}</p>
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

                        {/* Tool Calls */}
                        {message.toolCalls && message.toolCalls.length > 0 && (
                          <div className="border-border mt-4 border-t pt-4">
                            {message.toolCalls.map((toolCall, idx) => (
                              <div
                                key={idx}
                                className="bg-background text-foreground border-border mb-2 rounded border p-3 text-xs"
                              >
                                <div className="text-muted-foreground mb-2 flex items-center gap-2">
                                  <span>{t('usedTool', { toolName: toolCall.toolName })}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-card border-border shadow-soft-xs rounded-xl border px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="bg-muted-foreground/40 h-2 w-2 animate-bounce rounded-full" />
                      <div
                        className="bg-muted-foreground/40 h-2 w-2 animate-bounce rounded-full"
                        style={{ animationDelay: '0.1s' }}
                      />
                      <div
                        className="bg-muted-foreground/40 h-2 w-2 animate-bounce rounded-full"
                        style={{ animationDelay: '0.2s' }}
                      />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>
        </div>

        {/* Input Area */}
        <div className="border-border border-t px-8 py-6">
          <div className="mx-auto flex max-w-4xl gap-4">
            <Input
              placeholder={t('messagePlaceholder')}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
              className="flex-1 text-base"
            />
            <Button
              onClick={handleSendMessage}
              disabled={isLoading || !inputMessage.trim()}
              size="lg"
              className="px-8"
            >
              {tCommon('send')}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
