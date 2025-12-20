'use client'

import { useState, use, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { mockAgents } from '@/lib/mock-data'
import { Agent, Message } from '@/lib/types'
import { toast } from 'sonner'
import Link from 'next/link'
import Image from 'next/image'

export default function AgentPage({ params }: { params: Promise<{ id: string }> }) {
  const t = useTranslations('agentDetail')
  const tTest = useTranslations('test')
  const tCommon = useTranslations('common')
  const resolvedParams = use(params)
  const router = useRouter()
  const isNewAgent = resolvedParams.id === 'new'

  const [activeTab, setActiveTab] = useState<'configure' | 'test'>('configure')
  const [agent, setAgent] = useState<Agent>(() => {
    if (isNewAgent) {
      return {
        id: 'new',
        name: '',
        instructions: `You are a helpful assistant. Your role is to:\n\n- Assist customers with their questions\n- Be polite and professional\n- Provide accurate information`,
        status: 'draft',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        integrations: [],
      }
    }
    const foundAgent = mockAgents.find((a) => a.id === resolvedParams.id)
    if (foundAgent) return foundAgent

    // Fallback to first agent or create default
    return (
      mockAgents[0] || {
        id: resolvedParams.id,
        name: '',
        instructions: '',
        status: 'draft',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        integrations: [],
      }
    )
  })

  // Test/Playground state
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-welcome',
      role: 'system',
      content: tTest('welcomeMessage'),
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

  function handleSaveAgent() {
    if (!agent.name.trim()) {
      toast.error(t('errorNameRequired'))
      return
    }

    if (agent.instructions.length < 20) {
      toast.error(t('errorInstructionsTooShort'))
      return
    }

    toast.success(isNewAgent ? t('successCreated') : t('successSaved'))

    if (isNewAgent) {
      router.push('/agents')
    }
  }

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
        content: tTest('mockResponse', { agentName: agent?.name || 'Agent' }),
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

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="bg-background min-h-screen">
      <div className="mx-auto max-w-3xl px-8 py-16">
        {/* Back Button */}
        <Link
          href="/agents"
          className="text-muted-foreground hover:text-foreground mb-8 inline-flex items-center gap-1 transition-colors"
        >
          <span>←</span>
        </Link>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-foreground mb-2 text-4xl font-semibold tracking-tight">
            {isNewAgent ? t('newAgent') : agent.name}
          </h1>
          <p className="text-muted-foreground text-sm">
            {isNewAgent ? t('createSubtitle') : t('configureSubtitle')}
          </p>
        </div>

        {/* Tabs */}
        <div className="border-border mb-12 flex gap-6 border-b">
          <button
            onClick={() => setActiveTab('configure')}
            className={`pb-3 text-sm font-medium transition-colors ${
              activeTab === 'configure'
                ? 'text-foreground border-foreground border-b-2'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t('tabConfigure')}
          </button>
          <button
            onClick={() => setActiveTab('test')}
            className={`pb-3 text-sm font-medium transition-colors ${
              activeTab === 'test'
                ? 'text-foreground border-foreground border-b-2'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t('tabTest')}
          </button>
        </div>

        {/* Configure Tab */}
        {activeTab === 'configure' && (
          <div>
            {/* Agent Name */}
            <div className="mb-12">
              <Label className="text-foreground mb-3 block text-sm font-medium">
                {t('agentNameLabel')}
              </Label>
              <Input
                placeholder={t('agentNamePlaceholder')}
                value={agent.name}
                onChange={(e) => setAgent({ ...agent, name: e.target.value })}
              />
            </div>

            {/* Instructions */}
            <div className="mb-12">
              <Label className="text-foreground mb-3 block text-sm font-medium">
                {t('instructionsLabel')}
              </Label>
              <Textarea
                placeholder={t('instructionsPlaceholder')}
                value={agent.instructions}
                onChange={(e) => setAgent({ ...agent, instructions: e.target.value })}
                rows={12}
              />
            </div>

            {/* Tools */}
            <div className="mb-12">
              <Label className="text-foreground mb-4 block text-sm font-medium">
                {t('toolsLabel')}
              </Label>

              {agent.integrations.length === 0 ? (
                <Link href={`/agents/${resolvedParams.id}/tools/add`} className="group block">
                  <div className="border-border hover:border-primary/50 hover:bg-accent/30 cursor-pointer rounded-xl border-2 border-dashed py-16 text-center transition-all">
                    <p className="text-muted-foreground group-hover:text-foreground text-sm transition-colors">
                      {t('addTools')}
                    </p>
                  </div>
                </Link>
              ) : (
                <div className="space-y-2">
                  {agent.integrations.map((integration) => (
                    <Link
                      key={integration.id}
                      href={`/agents/${resolvedParams.id}/tools/${integration.id}`}
                      className="group block"
                    >
                      <div className="border-border bg-card shadow-soft-xs hover:shadow-soft-sm cursor-pointer rounded-xl border px-5 py-4 transition-all duration-200 ease-out hover:-translate-y-0.5">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Image
                              src={
                                integration.icon ||
                                (integration.type === 'custom-tool'
                                  ? 'https://api.iconify.design/lucide/wrench.svg?color=%23888888'
                                  : '')
                              }
                              alt={integration.name}
                              width={integration.icon ? 32 : 24}
                              height={integration.icon ? 32 : 24}
                              className={
                                integration.icon
                                  ? 'h-8 w-8 object-contain'
                                  : 'h-6 w-6 object-contain'
                              }
                            />
                            <div>
                              <h3 className="text-foreground text-sm font-medium">
                                {integration.name}
                              </h3>
                              <p className="text-muted-foreground mt-0.5 text-xs">
                                {t('toolCount', { count: integration.enabledToolIds.length })}
                              </p>
                            </div>
                          </div>
                          <span className="text-muted-foreground group-hover:text-foreground transition-colors">
                            →
                          </span>
                        </div>
                      </div>
                    </Link>
                  ))}
                  <Link href={`/agents/${resolvedParams.id}/tools/add`} className="group block">
                    <div className="border-border hover:border-primary/50 hover:bg-accent/30 cursor-pointer rounded-xl border-2 border-dashed px-5 py-4 text-center transition-all duration-200 ease-out">
                      <p className="text-muted-foreground group-hover:text-foreground text-sm transition-colors">
                        {t('addAnotherTool')}
                      </p>
                    </div>
                  </Link>
                </div>
              )}
            </div>

            {/* Connect */}
            <div className="mb-12">
              <Label className="text-foreground mb-4 block text-sm font-medium">
                {t('connectLabel')}
              </Label>

              <Link href={`/agents/${resolvedParams.id}/deploy`} className="group block">
                <div className="border-border hover:border-primary/50 hover:bg-accent/30 cursor-pointer rounded-xl border-2 border-dashed py-16 text-center transition-all">
                  <p className="text-muted-foreground group-hover:text-foreground text-sm transition-colors">
                    {t('connectToChannels')}
                  </p>
                </div>
              </Link>
            </div>

            {/* Actions */}
            <div className="border-border flex items-center justify-between border-t pt-8">
              <Link
                href="/agents"
                className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
              >
                <span>←</span>
              </Link>
              <Button onClick={handleSaveAgent} size="lg">
                {tCommon('save')}
              </Button>
            </div>
          </div>
        )}

        {/* Test Tab */}
        {activeTab === 'test' && (
          <div className="flex flex-col">
            {/* Chat Area */}
            <div className="mb-4 h-[380px] overflow-y-auto">
              <div className="space-y-6">
                {messages.map((message) => (
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
                          className={`max-w-[85%] rounded-xl px-5 py-3 ${
                            message.role === 'user'
                              ? 'bg-primary text-primary-foreground shadow-soft-sm'
                              : 'bg-card text-foreground border-border shadow-soft-xs border'
                          }`}
                        >
                          <p className="text-sm whitespace-pre-wrap">{message.content}</p>

                          {message.toolCalls && message.toolCalls.length > 0 && (
                            <div className="border-border mt-3 border-t pt-3">
                              {message.toolCalls.map((toolCall, idx) => (
                                <div
                                  key={idx}
                                  className="bg-background text-foreground border-border rounded border p-2 text-xs"
                                >
                                  <p className="text-muted-foreground">
                                    {tTest('usedTool', { toolName: toolCall.toolName })}
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

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-card border-border shadow-soft-xs rounded-xl border px-5 py-3">
                      <div className="flex items-center gap-1.5">
                        <div className="bg-muted-foreground/40 h-1.5 w-1.5 animate-bounce rounded-full" />
                        <div
                          className="bg-muted-foreground/40 h-1.5 w-1.5 animate-bounce rounded-full"
                          style={{ animationDelay: '0.1s' }}
                        />
                        <div
                          className="bg-muted-foreground/40 h-1.5 w-1.5 animate-bounce rounded-full"
                          style={{ animationDelay: '0.2s' }}
                        />
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Input Area */}
            <div className="border-border flex gap-3 border-t pt-4">
              <Input
                placeholder={tTest('messagePlaceholder')}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                className="flex-1"
              />
              <Button
                onClick={handleSendMessage}
                disabled={isLoading || !inputMessage.trim()}
                className="px-6"
              >
                {tCommon('send')}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
