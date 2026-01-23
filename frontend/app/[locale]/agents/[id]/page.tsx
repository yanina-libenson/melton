'use client'

import { useState, use, useRef, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAgent, useAgentMutations } from '@/lib/hooks/useAgents'
import { usePlayground } from '@/lib/hooks/usePlayground'
import { Agent, Message, FileAttachment, LLMModel } from '@/lib/types'
import useSWR from 'swr'
import { PLATFORM_INTEGRATIONS } from '@/lib/platforms'
import { apiClient } from '@/lib/api/client'
import { toast } from 'sonner'
import Link from 'next/link'
import Image from 'next/image'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { AgentPermissions } from '@/components/agent-permissions'
import { AgentShareLink } from '@/components/agent-share-link'
import { useAuth } from '@/lib/contexts/auth-context'

export default function AgentPage({ params }: { params: Promise<{ id: string; locale: string }> }) {
  const t = useTranslations('agentDetail')
  const tTest = useTranslations('test')
  const tCommon = useTranslations('common')
  const resolvedParams = use(params)
  const router = useRouter()
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const isNewAgent = resolvedParams.id === 'new'

  // Redirect to auth if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/auth')
    }
  }, [isAuthenticated, authLoading, router])

  // Redirect to Agent Builder if user is creating a new agent
  useEffect(() => {
    if (isNewAgent) {
      // Fetch all agents to find the Agent Builder
      apiClient.getAgents().then((agents: Agent[]) => {
        const agentBuilder = agents.find((a) => a.name === 'Agent Builder')
        if (agentBuilder) {
          // Redirect to Agent Builder chat
          router.push(`/${resolvedParams.locale}/agents/${agentBuilder.id}?tab=test`)
        }
      })
    }
  }, [isNewAgent, router, resolvedParams.locale])

  // Fetch agent data from API (skip if new agent)
  const {
    agent: fetchedAgent,
    isLoading,
    isError,
    mutate,
  } = useAgent(isNewAgent ? null : resolvedParams.id)

  const { createAgent, updateAgent } = useAgentMutations()

  // Fetch user's permission for this agent
  const { data: userPermission } = useSWR(
    isNewAgent ? null : `/agents/${resolvedParams.id}/my-permission`,
    () => apiClient.getUserPermission(resolvedParams.id)
  )

  // For new agents, the creator should be treated as admin
  // For existing agents, check the permission API response
  const isAdmin = isNewAgent || userPermission?.permission_type === 'admin'
  const hasUsePermission = userPermission?.permission_type === 'use'

  // Fetch available LLM models
  const { data: llmModels, isLoading: modelsLoading } = useSWR<LLMModel[]>('/llm-models', () =>
    apiClient.getLLMModels()
  )

  // Get initial tab from URL query param
  const searchParams = new URLSearchParams(
    typeof window !== 'undefined' ? window.location.search : ''
  )
  const mode = searchParams.get('mode') // 'use' mode from shared agents page
  const conversationId = searchParams.get('conversation_id') // Resume existing conversation
  const initialTab = searchParams.get('tab') === 'test' || mode === 'use' ? 'test' : 'configure'
  const [activeTab, setActiveTab] = useState<'configure' | 'test'>(initialTab)
  const forceUseMode = mode === 'use' // Force use mode even if user is admin

  // If user only has 'use' permission OR forceUseMode is true, force them to 'test' tab
  useEffect(() => {
    if ((hasUsePermission && !isAdmin) || forceUseMode) {
      setActiveTab('test')
    }
  }, [hasUsePermission, isAdmin, forceUseMode])

  // Local state for editing
  const [agent, setAgent] = useState<Agent | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  // Initialize agent state when data is fetched or for new agent
  useEffect(() => {
    if (isNewAgent) {
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
      agent.status !== fetchedAgent.status ||
      agent.model_config?.model !== fetchedAgent.model_config?.model

    setHasUnsavedChanges(hasChanges)
  }, [agent, fetchedAgent, isNewAgent])

  // Test/Playground state
  // Initial welcome message - different for use mode vs admin mode
  const getWelcomeMessage = useCallback(() => {
    if ((hasUsePermission && !isAdmin) || forceUseMode) {
      return 'Iniciá una conversación enviando un mensaje.'
    }
    return tTest('welcomeMessage')
  }, [hasUsePermission, isAdmin, forceUseMode, tTest])

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-welcome',
      role: 'system',
      content: getWelcomeMessage(),
      timestamp: new Date().toISOString(),
    },
  ])

  // Load conversation history if conversation_id is provided
  useEffect(() => {
    if (conversationId) {
      apiClient
        .getConversationMessages(conversationId)
        .then((data) => {
          const historyMessages: Message[] = data.messages.map((msg, index) => ({
            id: `msg-${index}`,
            role: (msg.role === 'assistant' ? 'agent' : msg.role) as 'user' | 'agent' | 'system',
            content: msg.content,
            timestamp: new Date().toISOString(),
          }))
          setMessages(historyMessages)
        })
        .catch((error) => {
          console.error('Failed to load conversation history:', error)
          // Fall back to welcome message on error
          setMessages([
            {
              id: 'msg-welcome',
              role: 'system',
              content: getWelcomeMessage(),
              timestamp: new Date().toISOString(),
            },
          ])
        })
    } else {
      // No conversation ID, show welcome message
      setMessages([
        {
          id: 'msg-welcome',
          role: 'system',
          content: getWelcomeMessage(),
          timestamp: new Date().toISOString(),
        },
      ])
    }
  }, [conversationId, getWelcomeMessage])
  const [inputMessage, setInputMessage] = useState('')
  const [attachedFiles, setAttachedFiles] = useState<FileAttachment[]>([])
  const [isUploadingFiles, setIsUploadingFiles] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
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
        model_config: agent.model_config,
      })

      if (result.success) {
        toast.success(t('successCreated'))
        router.push('/agents')
      } else {
        toast.error(result.error || 'Failed to create agent')
      }
    } else {
      const updateData = {
        name: agent.name,
        instructions: agent.instructions,
        status: agent.status,
        model_config: agent.model_config,
      }
      console.log('📤 Frontend sending update:', JSON.stringify(updateData, null, 2))

      const result = await updateAgent(agent.id, updateData)

      if (result.success) {
        toast.success(t('successSaved'))
        mutate() // Revalidate agent data
        setHasUnsavedChanges(false)
      } else {
        toast.error(result.error || 'Failed to update agent')
      }
    }
  }

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files
    if (!files || files.length === 0) return

    setIsUploadingFiles(true)
    const newAttachments: FileAttachment[] = []

    try {
      for (const file of Array.from(files)) {
        // Only allow images
        if (!file.type.startsWith('image/')) {
          toast.error(`${file.name} is not an image file`)
          continue
        }

        // Convert to data URL for preview
        const reader = new FileReader()
        const dataUrl = await new Promise<string>((resolve, reject) => {
          reader.onload = () => resolve(reader.result as string)
          reader.onerror = reject
          reader.readAsDataURL(file)
        })

        // Upload to backend
        const formData = new FormData()
        formData.append('file', file)

        const uploadResponse = await apiClient.uploadImage(formData)

        if (uploadResponse.success) {
          newAttachments.push({
            id: uploadResponse.filename || `${Date.now()}-${Math.random()}`,
            name: file.name,
            type: file.type,
            size: file.size,
            url: dataUrl, // For preview
            publicUrl: uploadResponse.url, // For API calls
          })
        } else {
          console.error('Upload failed:', uploadResponse)
          toast.error(`Failed to upload ${file.name}`)
        }
      }

      if (newAttachments.length > 0) {
        setAttachedFiles((prev) => [...prev, ...newAttachments])
        toast.success(
          `${newAttachments.length} image${newAttachments.length > 1 ? 's' : ''} uploaded`
        )
      }
    } catch (error: unknown) {
      console.error('Failed to upload files:', error)
      const errorMessage =
        (error as { data?: { detail?: string }; message?: string })?.data?.detail ||
        (error as { message?: string })?.message ||
        'Failed to upload images'
      toast.error(errorMessage)
    } finally {
      setIsUploadingFiles(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  function handleRemoveFile(fileId: string) {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId))
  }

  function handleSendMessage() {
    if (
      (!inputMessage.trim() && attachedFiles.length === 0) ||
      playground.isStreaming ||
      isNewAgent
    )
      return

    playground.sendMessage(inputMessage, attachedFiles, conversationId || undefined)
    setInputMessage('')
    setAttachedFiles([])
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
          href={(hasUsePermission && !isAdmin) || forceUseMode ? '/shared-agents' : '/agents'}
          className="text-muted-foreground hover:text-foreground mb-8 inline-flex items-center gap-1 transition-colors"
        >
          <span>←</span>
        </Link>

        {/* Header - Hide subtitle in use mode */}
        {!((hasUsePermission && !isAdmin) || forceUseMode) && (
          <div className="mb-8">
            <h1 className="text-foreground mb-2 text-4xl font-semibold tracking-tight">
              {isNewAgent ? t('newAgent') : agent.name}
            </h1>
            <p className="text-muted-foreground text-sm">
              {isNewAgent ? t('createSubtitle') : t('configureSubtitle')}
            </p>
          </div>
        )}

        {/* Tabs - Hide for users with only 'use' permission OR when in force use mode */}
        {!hasUsePermission && !forceUseMode && (
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
        )}

        {/* Live Chat Header for users with 'use' permission OR when in force use mode */}
        {((hasUsePermission && !isAdmin) || forceUseMode) && (
          <div className="mb-8">
            <h2 className="text-foreground text-2xl font-semibold">Live Chat</h2>
            <p className="text-muted-foreground mt-1 text-sm">
              Chat with {agent?.name || 'this agent'}
            </p>
          </div>
        )}

        {/* Configure Tab - Only for admin users and not in force use mode */}
        {activeTab === 'configure' && isAdmin && !forceUseMode && (
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

            {/* Model Selection */}
            <div className="mb-12">
              <Label className="text-foreground mb-3 block text-sm font-medium">Model</Label>
              <Select
                value={agent.model_config?.model || 'claude-sonnet-4-5-20250929'}
                onValueChange={(value) => {
                  const selectedModel = llmModels?.find((m) => m.modelId === value)
                  setAgent({
                    ...agent,
                    model_config: {
                      ...agent.model_config,
                      provider: selectedModel?.provider || 'anthropic',
                      model: value,
                      temperature: agent.model_config?.temperature || 0.7,
                      max_tokens: agent.model_config?.max_tokens || 4096,
                    },
                  })
                }}
                disabled={modelsLoading}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={modelsLoading ? 'Loading models...' : 'Select a model'}
                  />
                </SelectTrigger>
                <SelectContent>
                  {llmModels && !modelsLoading ? (
                    <>
                      {/* Anthropic Models */}
                      {llmModels.filter((m) => m.provider === 'anthropic').length > 0 && (
                        <>
                          <div className="text-muted-foreground px-2 py-1.5 text-xs font-semibold">
                            Anthropic
                          </div>
                          {llmModels
                            .filter((m) => m.provider === 'anthropic')
                            .map((model) => (
                              <SelectItem key={model.id} value={model.modelId}>
                                {model.displayName}
                              </SelectItem>
                            ))}
                        </>
                      )}

                      {/* OpenAI Models */}
                      {llmModels.filter((m) => m.provider === 'openai').length > 0 && (
                        <>
                          <div className="text-muted-foreground px-2 py-1.5 text-xs font-semibold">
                            OpenAI
                          </div>
                          {llmModels
                            .filter((m) => m.provider === 'openai')
                            .map((model) => (
                              <SelectItem key={model.id} value={model.modelId}>
                                {model.displayName}
                              </SelectItem>
                            ))}
                        </>
                      )}

                      {/* Google Models */}
                      {llmModels.filter((m) => m.provider === 'google').length > 0 && (
                        <>
                          <div className="text-muted-foreground px-2 py-1.5 text-xs font-semibold">
                            Google
                          </div>
                          {llmModels
                            .filter((m) => m.provider === 'google')
                            .map((model) => (
                              <SelectItem key={model.id} value={model.modelId}>
                                {model.displayName}
                              </SelectItem>
                            ))}
                        </>
                      )}
                    </>
                  ) : (
                    <div className="text-muted-foreground px-2 py-4 text-center text-sm">
                      Loading models...
                    </div>
                  )}
                </SelectContent>
              </Select>
              <p className="text-muted-foreground mt-2 text-xs">
                Claude Sonnet 4.5 is recommended for complex tasks and tool calling
              </p>
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
                                  : integration.platformId
                                    ? PLATFORM_INTEGRATIONS.find(
                                        (p) => p.id === integration.platformId
                                      )?.icon ||
                                      'https://api.iconify.design/lucide/box.svg?color=%23888888'
                                    : 'https://api.iconify.design/lucide/box.svg?color=%23888888')
                              }
                              alt={integration.name}
                              width={32}
                              height={32}
                              className="h-8 w-8 object-contain"
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

            {/* Sharing & Permissions - Only show for existing agents with admin permission and not in force use mode */}
            {!isNewAgent && isAdmin && !forceUseMode && (
              <>
                <div className="mb-12">
                  <AgentPermissions agentId={resolvedParams.id} />
                </div>

                <div className="mb-12">
                  <AgentShareLink agentId={resolvedParams.id} />
                </div>
              </>
            )}

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
            {/* Unsaved Changes Warning - Only for admin users not in use mode */}
            {hasUnsavedChanges && !((hasUsePermission && !isAdmin) || forceUseMode) && (
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
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={{
                                a: ({ ...props }) => (
                                  <a
                                    {...props}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary font-medium hover:underline"
                                  />
                                ),
                                img: ({ ...props }) => (
                                  // eslint-disable-next-line @next/next/no-img-element
                                  <img
                                    {...props}
                                    alt={props.alt || 'Image'}
                                    className="my-4 h-auto max-w-full rounded-lg"
                                    loading="lazy"
                                  />
                                ),
                              }}
                            >
                              {message.content}
                            </ReactMarkdown>
                          </div>

                          {/* Show attached images */}
                          {message.attachments && message.attachments.length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {message.attachments.map((attachment) => (
                                <div
                                  key={attachment.id}
                                  className={`relative overflow-hidden rounded-lg border ${
                                    message.role === 'user'
                                      ? 'border-primary-foreground/20'
                                      : 'border-border'
                                  }`}
                                >
                                  <Image
                                    src={attachment.url}
                                    alt={attachment.name}
                                    width={200}
                                    height={200}
                                    className="h-32 w-32 object-cover"
                                  />
                                </div>
                              ))}
                            </div>
                          )}

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
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            a: ({ ...props }) => (
                              <a
                                {...props}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary font-medium hover:underline"
                              />
                            ),
                            img: ({ ...props }) => (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img
                                {...props}
                                alt={props.alt || 'Image'}
                                className="my-4 h-auto max-w-full rounded-lg"
                                loading="lazy"
                              />
                            ),
                          }}
                        >
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
            <div className="border-border space-y-3 border-t pt-4">
              {/* Upload Status */}
              {isUploadingFiles && (
                <div className="text-muted-foreground flex items-center gap-2 text-sm">
                  <svg
                    className="h-4 w-4 animate-spin"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  <span>Uploading images...</span>
                </div>
              )}

              {/* Attached Files Preview */}
              {attachedFiles.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {attachedFiles.map((file) => (
                    <div
                      key={file.id}
                      className="bg-muted relative flex items-center gap-2 rounded-lg border p-2"
                    >
                      <Image
                        src={file.url}
                        alt={file.name}
                        width={48}
                        height={48}
                        className="h-12 w-12 rounded object-cover"
                      />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm">{file.name}</p>
                        <p className="text-muted-foreground text-xs">
                          {(file.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveFile(file.id)}
                        className="h-6 w-6 p-0"
                      >
                        ✕
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              {/* Input Row */}
              <div className="flex gap-3">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={playground.isStreaming || isNewAgent || isUploadingFiles}
                  title="Attach images"
                >
                  {isUploadingFiles ? (
                    <svg
                      className="h-5 w-5 animate-spin"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                  ) : (
                    '📎'
                  )}
                </Button>
                <Input
                  placeholder={
                    (hasUsePermission && !isAdmin) || forceUseMode
                      ? 'Escribí un mensaje...'
                      : tTest('messagePlaceholder')
                  }
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={playground.isStreaming || isNewAgent}
                  className="flex-1"
                />
                <Button
                  onClick={handleSendMessage}
                  disabled={
                    playground.isStreaming ||
                    (!inputMessage.trim() && attachedFiles.length === 0) ||
                    isNewAgent
                  }
                  className="px-6"
                >
                  {tCommon('send')}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
