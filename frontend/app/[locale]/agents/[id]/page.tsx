'use client'

import { useState, use, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useAgent, useAgentMutations } from '@/lib/hooks/useAgents'
import { usePlayground } from '@/lib/hooks/usePlayground'
import { Agent, Message } from '@/lib/types'
import { toast } from 'sonner'
import Link from 'next/link'
import Image from 'next/image'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function AgentPage({ params }: { params: Promise<{ id: string }> }) {
  const t = useTranslations('agentDetail')
  const tTest = useTranslations('test')
  const tCommon = useTranslations('common')
  const resolvedParams = use(params)
  const router = useRouter()
  const isNewAgent = resolvedParams.id === 'new'

  // Fetch agent data from API (skip if new agent)
  const {
    agent: fetchedAgent,
    isLoading,
    isError,
    mutate,
  } = useAgent(isNewAgent ? null : resolvedParams.id)

  const { createAgent, updateAgent } = useAgentMutations()

  const [activeTab, setActiveTab] = useState<'configure' | 'test'>('configure')

  // Local state for editing
  const [agent, setAgent] = useState<Agent | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  // Initialize agent state when data is fetched or for new agent
  useEffect(() => {
    if (isNewAgent) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAgent({
        id: 'new',
        userId: '550e8400-e29b-41d4-a716-446655440000',
        organizationId: '550e8400-e29b-41d4-a716-446655440001',
        name: '',
        instructions: `You are a helpful assistant. Your role is to:\n\n- Assist customers with their questions\n- Be polite and professional\n- Provide accurate information`,
        status: 'draft',
        model_config: {
          provider: 'anthropic',
          model: 'claude-sonnet-4-5-20250929',
          temperature: 0.7,
          max_tokens: 4096,
        },
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        integrations: [],
      })
      setHasUnsavedChanges(true) // New agents always have unsaved changes
    } else if (fetchedAgent) {
      setAgent(fetchedAgent)
      setHasUnsavedChanges(false)
    }
  }, [isNewAgent, fetchedAgent])

  // Detect changes to agent
  useEffect(() => {
    if (!agent || !fetchedAgent || isNewAgent) return

    const hasChanges =
      agent.name !== fetchedAgent.name ||
      agent.instructions !== fetchedAgent.instructions ||
      agent.status !== fetchedAgent.status

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHasUnsavedChanges(hasChanges)
  }, [agent, fetchedAgent, isNewAgent])

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
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // WebSocket playground connection (only when on test tab and not new agent)
  const playground = usePlayground({
    agentId: !isNewAgent ? resolvedParams.id : '',
    enabled: !isNewAgent && activeTab === 'test',
    onMessage: (message) => {
      setMessages((prev) => [...prev, message])
    },
    onError: (error, settingsUrl) => {
      if (settingsUrl) {
        toast.error(error, {
          action: {
            label: 'Go to Settings',
            onClick: () => router.push('/settings'),
          },
        })
      } else {
        toast.error(error)
      }
    },
  })

  function scrollToBottom() {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, playground.currentResponse])

  async function handleSaveAgent() {
    if (!agent || !agent.name.trim()) {
      toast.error(t('errorNameRequired'))
      return
    }

    if (agent.instructions.length < 20) {
      toast.error(t('errorInstructionsTooShort'))
      return
    }

    if (isNewAgent) {
      const result = await createAgent({
        name: agent.name,
        instructions: agent.instructions,
        status: agent.status,
        model_config: {
          provider: 'anthropic',
          model: 'claude-sonnet-4-5-20250929',
          temperature: 0.7,
          max_tokens: 4096,
        },
      })

      if (result.success) {
        toast.success(t('successCreated'))
        router.push('/agents')
      } else {
        toast.error(result.error || 'Failed to create agent')
      }
    } else {
      const result = await updateAgent(agent.id, {
        name: agent.name,
        instructions: agent.instructions,
        status: agent.status,
      })

      if (result.success) {
        toast.success(t('successSaved'))
        mutate() // Revalidate agent data
        setHasUnsavedChanges(false)
      } else {
        toast.error(result.error || 'Failed to update agent')
      }
    }
  }

  function handleSendMessage() {
    if (!inputMessage.trim() || playground.isStreaming || isNewAgent) return

    playground.sendMessage(inputMessage)
    setInputMessage('')
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // Loading state
  if (!isNewAgent && isLoading) {
    return (
      <div className="bg-background min-h-screen">
        <div className="mx-auto max-w-3xl px-8 py-16">
          <div className="py-32 text-center">
            <p className="text-muted-foreground text-sm">Loading agent...</p>
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (!isNewAgent && isError) {
    return (
      <div className="bg-background min-h-screen">
        <div className="mx-auto max-w-3xl px-8 py-16">
          <div className="py-32 text-center">
            <p className="mb-4 text-sm text-red-500">Error loading agent</p>
            <Button onClick={() => router.push('/agents')}>Back to Agents</Button>
          </div>
        </div>
      </div>
    )
  }

  // No agent data
  if (!agent) {
    return null
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
            <span className="flex items-center gap-1.5">
              {t('tabConfigure')}
              {hasUnsavedChanges && (
                <span className="text-xs text-yellow-600 dark:text-yellow-500">●</span>
              )}
            </span>
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

              {!agent.integrations || agent.integrations.length === 0 ? (
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
                                {t('toolCount', { count: integration.availableTools?.length || 0 })}
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
            {/* Unsaved Changes Warning */}
            {hasUnsavedChanges && (
              <div className="mb-6 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-yellow-800 dark:border-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-200">
                <div className="flex items-start gap-3">
                  <span className="text-lg">⚠️</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium">You have unsaved changes</p>
                    <p className="text-muted-foreground mt-1 text-xs">
                      The playground is testing the last saved version of your agent. Save your
                      changes on the Configure tab to test them.
                    </p>
                  </div>
                  <button
                    onClick={() => setActiveTab('configure')}
                    className="rounded px-3 py-1 text-xs font-medium transition-colors hover:bg-yellow-100 dark:hover:bg-yellow-900/40"
                  >
                    Go to Configure
                  </button>
                </div>
              </div>
            )}

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
                          <div className="prose prose-sm dark:prose-invert max-w-none text-sm">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {message.content}
                            </ReactMarkdown>
                          </div>

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

                {/* Streaming response */}
                {playground.currentResponse && (
                  <div className="flex justify-start">
                    <div className="bg-card text-foreground border-border shadow-soft-xs max-w-[85%] rounded-xl border px-5 py-3">
                      <div className="prose prose-sm dark:prose-invert max-w-none text-sm">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {playground.currentResponse}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>
                )}

                {playground.isStreaming && !playground.currentResponse && (
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
                disabled={playground.isStreaming || isNewAgent}
                className="flex-1"
              />
              <Button
                onClick={handleSendMessage}
                disabled={playground.isStreaming || !inputMessage.trim() || isNewAgent}
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
