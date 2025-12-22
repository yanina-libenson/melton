'use client'

import { useState, use, useEffect } from 'react'
import { useRouter } from 'next/navigation'
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
import { PLATFORM_INTEGRATIONS, PLATFORM_TOOLS } from '@/lib/platforms'
import { Tool, AuthenticationType, HttpMethod, CustomToolType } from '@/lib/types'
import { toast } from 'sonner'
import { mockAgents } from '@/lib/mock-data'
import Image from 'next/image'
import { useTranslations } from 'next-intl'
import { apiClient } from '@/lib/api/client'

export default function IntegrationConfigPage({
  params,
}: {
  params: Promise<{ id: string; platformId: string; locale: string }>
}) {
  const resolvedParams = use(params)
  const router = useRouter()
  const t = useTranslations('toolsIntegration')
  const tCommon = useTranslations('common')

  const platform = PLATFORM_INTEGRATIONS.find((p) => p.id === resolvedParams.platformId)
  const isCustomTool = resolvedParams.platformId === 'custom-tool'
  const isSubAgent = resolvedParams.platformId === 'sub-agent'

  // Pre-built integration tools or empty for custom
  const [tools, setTools] = useState<Tool[]>(
    isCustomTool || isSubAgent ? [] : PLATFORM_TOOLS[resolvedParams.platformId] || []
  )

  const [authData, setAuthData] = useState<Record<string, string>>({})
  const [enabledToolIds, setEnabledToolIds] = useState<string[]>(tools.map((t) => t.id))
  const [step, setStep] = useState<'type-selection' | 'auth' | 'tools' | 'config'>(
    isCustomTool ? 'type-selection' : isSubAgent ? 'config' : 'auth'
  )

  // Custom tool type selection
  const [customToolType, setCustomToolType] = useState<CustomToolType | null>(null)

  // Custom tool fields
  const [toolName, setToolName] = useState(platform?.name || '')
  const [toolDescription, setToolDescription] = useState(platform?.description || '')
  const [authType, setAuthType] = useState<AuthenticationType>('none')
  const [baseUrl, setBaseUrl] = useState('')

  // Sub-agent selection
  const [selectedSubAgentId, setSelectedSubAgentId] = useState<string>('')

  // OpenAPI Discovery
  const [openApiUrl, setOpenApiUrl] = useState('')
  const [isDiscovering, setIsDiscovering] = useState(false)
  const [discoveryMethod, setDiscoveryMethod] = useState<'openapi' | 'manual'>('openapi')

  // Tool configuration
  const [expandedToolId, setExpandedToolId] = useState<string | null>(null)
  const [toolConfigs, setToolConfigs] = useState<
    Record<
      string,
      {
        llmEnabled: boolean
        llmModel: string
        llmInstructions: string
        creativityLevel: 'low' | 'medium' | 'high'
      }
    >
  >({})

  // Manual endpoint creation
  const [showEndpointForm, setShowEndpointForm] = useState(false)
  const [newEndpoint, setNewEndpoint] = useState({
    name: '',
    description: '',
    method: 'GET' as HttpMethod,
    path: '',
  })

  // Tool schema configuration
  const [toolSchemas, setToolSchemas] = useState<
    Record<
      string,
      {
        inputFields: Array<{
          name: string
          type: 'text' | 'number' | 'boolean' | 'select'
          description: string
          required: boolean
          options?: string[]
        }>
        outputFields: Array<{
          name: string
          type: 'text' | 'number' | 'boolean'
          description: string
        }>
      }
    >
  >({})

  // Auto-expand first enabled tool when on tools step
  useEffect(() => {
    if (step === 'tools' && enabledToolIds.length > 0 && !expandedToolId) {
      const firstToolId = enabledToolIds[0]
      if (firstToolId) {
        setExpandedToolId(firstToolId)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, enabledToolIds])

  if (!platform) {
    return null
  }

  async function handleDiscoverEndpoints() {
    if (!openApiUrl.trim()) {
      toast.error(t('errorOpenApiUrlRequired'))
      return
    }

    setIsDiscovering(true)

    // Mock discovery - in production this would call the backend
    setTimeout(() => {
      const mockDiscoveredTools: Tool[] = [
        {
          id: 'discovered-1',
          name: 'Get Users',
          description: 'Retrieve a list of users',
          sourceId: 'custom-api',
        },
        {
          id: 'discovered-2',
          name: 'Create User',
          description: 'Create a new user',
          sourceId: 'custom-api',
        },
        {
          id: 'discovered-3',
          name: 'Get User by ID',
          description: 'Retrieve a specific user by ID',
          sourceId: 'custom-api',
        },
      ]

      setTools(mockDiscoveredTools)
      setEnabledToolIds([]) // Start with all unselected
      setIsDiscovering(false)
      toast.success(t('successEndpointsDiscovered', { count: mockDiscoveredTools.length }))
    }, 1500)
  }

  function handleAddEndpoint() {
    if (!newEndpoint.name.trim()) {
      toast.error(t('errorEndpointNameRequired'))
      return
    }
    if (!newEndpoint.path.trim()) {
      toast.error(t('errorEndpointPathRequired'))
      return
    }

    const endpoint: Tool = {
      id: `custom-${Date.now()}`,
      name: newEndpoint.name,
      description: newEndpoint.description,
      sourceId: 'custom-api',
    }

    setTools([...tools, endpoint])
    // Don't auto-enable - let user select it
    setNewEndpoint({ name: '', description: '', method: 'GET', path: '' })
    setShowEndpointForm(false)
    toast.success(t('successEndpointAdded'))
  }

  function handleToggleTool(toolId: string) {
    setEnabledToolIds((prev) => {
      const isCurrentlyEnabled = prev.includes(toolId)

      if (isCurrentlyEnabled) {
        // Disabling - collapse it
        if (expandedToolId === toolId) {
          setExpandedToolId(null)
        }
        return prev.filter((id) => id !== toolId)
      } else {
        // Enabling - auto-expand it
        setExpandedToolId(toolId)
        return [...prev, toolId]
      }
    })
  }

  function addInputField(toolId: string) {
    const schema = toolSchemas[toolId] || { inputFields: [], outputFields: [] }
    setToolSchemas({
      ...toolSchemas,
      [toolId]: {
        ...schema,
        inputFields: [
          ...schema.inputFields,
          { name: '', type: 'text', description: '', required: false },
        ],
      },
    })
  }

  function updateInputField(
    toolId: string,
    index: number,
    field: Partial<(typeof toolSchemas)[string]['inputFields'][0]>
  ) {
    const schema = toolSchemas[toolId]
    if (!schema) return

    const updatedFields = [...schema.inputFields]
    const existingField = updatedFields[index]
    if (!existingField) return

    updatedFields[index] = { ...existingField, ...field }

    setToolSchemas({
      ...toolSchemas,
      [toolId]: { ...schema, inputFields: updatedFields },
    })
  }

  function removeInputField(toolId: string, index: number) {
    const schema = toolSchemas[toolId]
    if (!schema) return

    setToolSchemas({
      ...toolSchemas,
      [toolId]: {
        ...schema,
        inputFields: schema.inputFields.filter((_, i) => i !== index),
      },
    })
  }

  function addOutputField(toolId: string) {
    const schema = toolSchemas[toolId] || { inputFields: [], outputFields: [] }
    setToolSchemas({
      ...toolSchemas,
      [toolId]: {
        ...schema,
        outputFields: [...schema.outputFields, { name: '', type: 'text', description: '' }],
      },
    })
  }

  function updateOutputField(
    toolId: string,
    index: number,
    field: Partial<(typeof toolSchemas)[string]['outputFields'][0]>
  ) {
    const schema = toolSchemas[toolId]
    if (!schema) return

    const updatedFields = [...schema.outputFields]
    const existingField = updatedFields[index]
    if (!existingField) return

    updatedFields[index] = { ...existingField, ...field }

    setToolSchemas({
      ...toolSchemas,
      [toolId]: { ...schema, outputFields: updatedFields },
    })
  }

  function removeOutputField(toolId: string, index: number) {
    const schema = toolSchemas[toolId]
    if (!schema) return

    setToolSchemas({
      ...toolSchemas,
      [toolId]: {
        ...schema,
        outputFields: schema.outputFields.filter((_, i) => i !== index),
      },
    })
  }

  function handleSelectToolType(type: CustomToolType) {
    setCustomToolType(type)

    // For LLM-only, go straight to config
    if (type === 'llm') {
      setStep('config')
    } else {
      // For API and API+LLM, go to auth
      setStep('auth')
    }
  }

  function handleNextToTools() {
    if (!platform) return

    // Validate custom tool fields that need API
    if (isCustomTool && customToolType === 'api') {
      if (!toolName.trim()) {
        toast.error(t('errorToolNameRequired'))
        return
      }
      if (!baseUrl.trim()) {
        toast.error(t('errorBaseUrlRequired'))
        return
      }
    }

    // Validate pre-built auth fields
    if (platform.requiresAuth && !isCustomTool && !isSubAgent) {
      const missingFields = platform.authFields.filter(
        (field) => field.required && !authData[field.name]?.trim()
      )

      if (missingFields.length > 0) {
        toast.error(t('errorFillRequiredFields'))
        return
      }
    }

    setStep('tools')
  }

  function handleNextFromConfig() {
    if (isSubAgent) {
      if (!selectedSubAgentId) {
        toast.error(t('errorSelectSubAgent'))
        return
      }
      // Create a tool from the selected agent
      const subAgent = mockAgents.find((a) => a.id === selectedSubAgentId)
      if (subAgent) {
        const tool: Tool = {
          id: `sub-agent-${selectedSubAgentId}`,
          name: subAgent.name,
          description: t('useAsToolDescription', { name: subAgent.name }),
          sourceId: 'sub-agent',
          toolType: 'sub-agent',
          subAgentId: selectedSubAgentId,
        }
        setTools([tool])
        setEnabledToolIds([tool.id])
        setExpandedToolId(tool.id)
      }
    } else if (isCustomTool && customToolType === 'llm') {
      if (!toolName.trim()) {
        toast.error(t('errorToolNameRequired'))
        return
      }
      const config = toolConfigs['llm-default'] || {
        llmModel: 'claude-sonnet-4-5-20250929',
        llmInstructions: '',
      }
      // Create an LLM-only tool
      const tool: Tool = {
        id: `llm-${Date.now()}`,
        name: toolName,
        description: toolDescription,
        sourceId: 'custom-tool',
        toolType: 'llm',
        llmModel: config.llmModel as
          | 'gpt-4o'
          | 'claude-sonnet-4-5-20250929'
          | 'claude-opus-4-5-20251101'
          | 'gemini-2.0-flash-exp',
        llmInstructions: config.llmInstructions,
      }
      setTools([tool])
      setEnabledToolIds([tool.id])
      setExpandedToolId(tool.id)
    }
    setStep('tools')
  }

  async function handleSave() {
    if (enabledToolIds.length === 0) {
      toast.error(t('errorAtLeastOneTool'))
      return
    }

    try {
      // Create integration
      const integrationConfig: Record<string, unknown> = {
        authentication: authType,
        ...authData,
      }

      if (baseUrl) {
        integrationConfig.baseUrl = baseUrl
      }

      const integrationData: {
        agent_id: string
        type: 'platform' | 'custom-tool' | 'sub-agent'
        name: string
        description?: string
        config: Record<string, unknown>
        platform_id?: string
      } = {
        agent_id: resolvedParams.id,
        type: isSubAgent ? 'sub-agent' : isCustomTool ? 'custom-tool' : 'platform',
        name: toolName || platform?.name || 'Integration',
        description: toolDescription,
        config: integrationConfig,
      }

      if (!isCustomTool) {
        integrationData.platform_id = resolvedParams.platformId
      }

      const integration = await apiClient.createIntegration(integrationData)

      // Create tools for the integration
      const enabledTools = tools.filter((t) => enabledToolIds.includes(t.id))
      for (const tool of enabledTools) {
        // For LLM tools, config is stored under 'llm-default' key
        const configKey = customToolType === 'llm' ? 'llm-default' : tool.id
        const toolConfig = toolConfigs[configKey] || {
          llmEnabled: false,
          llmModel: '',
          llmInstructions: '',
          creativityLevel: 'medium' as const,
        }
        const toolSchema = toolSchemas[tool.id] || { inputFields: [], outputFields: [] }

        const toolSchemaPayload: {
          name: string
          description: string
          input_schema: {
            type: string
            properties: Record<string, { type: string; description: string }>
            required: string[]
          }
          output_schema?: {
            type: string
            properties: Record<string, { type: string; description: string }>
            required: string[]
          }
        } = {
          name: tool.name.toLowerCase().replace(/\s+/g, '_'),
          description: tool.description || tool.name,
          input_schema: {
            type: 'object',
            properties: Object.fromEntries(
              toolSchema.inputFields.map((field) => [
                field.name,
                {
                  type:
                    field.type === 'number'
                      ? 'number'
                      : field.type === 'boolean'
                        ? 'boolean'
                        : 'string',
                  description: field.description,
                },
              ])
            ),
            required: toolSchema.inputFields.filter((f) => f.required).map((f) => f.name),
          },
        }

        // Add output schema if output fields are defined
        if (toolSchema.outputFields.length > 0) {
          toolSchemaPayload.output_schema = {
            type: 'object',
            properties: Object.fromEntries(
              toolSchema.outputFields.map((field) => [
                field.name,
                {
                  type:
                    field.type === 'number'
                      ? 'number'
                      : field.type === 'boolean'
                        ? 'boolean'
                        : 'string',
                  description: field.description,
                },
              ])
            ),
            required: toolSchema.outputFields.map((f) => f.name),
          }
        }

        await apiClient.createTool({
          integration_id: integration.id,
          name: tool.name,
          description: tool.description || '',
          tool_type: customToolType || 'api',
          tool_schema: toolSchemaPayload,
          config: {
            endpoint: tool.endpoint,
            method: tool.method,
            llm_enabled: toolConfig.llmEnabled || false,
            llm_model: toolConfig.llmModel,
            llm_instructions: toolConfig.llmInstructions,
            creativity_level: toolConfig.creativityLevel || 'medium',
          },
          is_enabled: true,
        })
      }

      toast.success(t('successToolAdded', { name: toolName || platform?.name || 'Tool' }))
      router.push(`/agents/${resolvedParams.id}`)
    } catch (error) {
      console.error('Failed to create integration:', error)
      toast.error('Failed to create integration. Please try again.')
    }
  }

  return (
    <div className="bg-background min-h-screen">
      <div className="mx-auto max-w-3xl px-8 py-16">
        {/* Back Button */}
        <button
          onClick={() => {
            if (step === 'type-selection') {
              router.push(`/agents/${resolvedParams.id}/tools/add`)
            } else if (step === 'config') {
              if (isCustomTool) {
                setStep('type-selection')
              } else {
                router.push(`/agents/${resolvedParams.id}/tools/add`)
              }
            } else if (step === 'auth') {
              if (isCustomTool) {
                setStep('type-selection')
              } else {
                router.push(`/agents/${resolvedParams.id}/tools/add`)
              }
            } else if (step === 'tools') {
              if (isSubAgent || (isCustomTool && customToolType === 'llm')) {
                setStep('config')
              } else if (isCustomTool && customToolType === 'api') {
                setStep('auth')
              } else {
                setStep('auth')
              }
            }
          }}
          className="text-muted-foreground hover:text-foreground mb-8 inline-flex items-center gap-1 transition-colors"
        >
          <span>←</span>
        </button>

        {/* Header */}
        <div className="mb-12">
          <div className="flex items-center gap-4">
            <Image
              src={platform.icon}
              alt={platform.name}
              width={48}
              height={48}
              className="h-12 w-12 object-contain"
            />
            <div>
              <h1 className="text-foreground text-3xl font-semibold tracking-tight">
                {platform.name}
              </h1>
              <p className="text-muted-foreground mt-1 text-sm">{platform.description}</p>
            </div>
          </div>
        </div>

        {/* Tool Type Selection Step (Custom Tool only) */}
        {step === 'type-selection' && isCustomTool && (
          <div className="mb-12">
            <Label className="text-foreground mb-4 block text-sm font-medium">
              {t('chooseToolType')}
            </Label>
            <div className="grid grid-cols-1 gap-3">
              <button
                onClick={() => handleSelectToolType('llm')}
                className="border-border bg-card shadow-soft-xs hover:shadow-soft-sm hover:border-border cursor-pointer rounded-xl border px-6 py-5 text-left transition-all duration-200 ease-out hover:-translate-y-0.5"
              >
                <p className="text-foreground mb-1 text-sm font-medium">{t('llmType')}</p>
                <p className="text-muted-foreground text-xs">{t('llmTypeDescription')}</p>
              </button>

              <button
                onClick={() => handleSelectToolType('api')}
                className="border-border bg-card shadow-soft-xs hover:shadow-soft-sm hover:border-border cursor-pointer rounded-xl border px-6 py-5 text-left transition-all duration-200 ease-out hover:-translate-y-0.5"
              >
                <p className="text-foreground mb-1 text-sm font-medium">{t('apiType')}</p>
                <p className="text-muted-foreground text-xs">{t('apiTypeDescription')}</p>
              </button>
            </div>
          </div>
        )}

        {/* Sub-Agent Configuration */}
        {step === 'config' && isSubAgent && (
          <div className="mb-12 space-y-8">
            <div>
              <Label className="text-foreground mb-3 block text-sm font-medium">
                {t('selectAgentLabel')}
              </Label>
              <Select value={selectedSubAgentId} onValueChange={setSelectedSubAgentId}>
                <SelectTrigger>
                  <SelectValue placeholder={t('selectAgentPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  {mockAgents
                    .filter((a) => a.id !== resolvedParams.id)
                    .map((agent) => (
                      <SelectItem key={agent.id} value={agent.id}>
                        {agent.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
              <p className="text-muted-foreground mt-2 text-xs">{t('selectAgentHelp')}</p>
            </div>
          </div>
        )}

        {/* LLM-Only Configuration */}
        {step === 'config' && isCustomTool && customToolType === 'llm' && (
          <div className="mb-12 space-y-8">
            <div>
              <Label className="text-foreground mb-3 block text-sm font-medium">
                {t('toolNameLabel')}
              </Label>
              <Input
                placeholder={t('toolNamePlaceholder')}
                value={toolName}
                onChange={(e) => setToolName(e.target.value)}
              />
            </div>

            <div>
              <Label className="text-foreground mb-3 block text-sm font-medium">
                {t('descriptionLabel')}
              </Label>
              <Textarea
                placeholder={t('descriptionPlaceholder')}
                value={toolDescription}
                onChange={(e) => setToolDescription(e.target.value)}
                rows={3}
              />
            </div>

            <div>
              <Label className="text-foreground mb-3 block text-sm font-medium">
                {t('modelLabel')}
              </Label>
              <Select
                value={toolConfigs['llm-default']?.llmModel || 'claude-sonnet-4-5-20250929'}
                onValueChange={(value) =>
                  setToolConfigs({
                    ...toolConfigs,
                    'llm-default': {
                      ...toolConfigs['llm-default'],
                      llmModel: value,
                      llmEnabled: true,
                      llmInstructions: toolConfigs['llm-default']?.llmInstructions || '',
                      creativityLevel: toolConfigs['llm-default']?.creativityLevel || 'medium',
                    },
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="claude-sonnet-4-5-20250929">Claude Sonnet 4.5</SelectItem>
                  <SelectItem value="claude-opus-4-5-20251101">Claude Opus 4.5</SelectItem>
                  <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                  <SelectItem value="gemini-2.0-flash-exp">Gemini 2.0 Flash</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-foreground mb-3 block text-sm font-medium">
                Creativity Level
              </Label>
              <Select
                value={toolConfigs['llm-default']?.creativityLevel || 'medium'}
                onValueChange={(value: 'low' | 'medium' | 'high') =>
                  setToolConfigs({
                    ...toolConfigs,
                    'llm-default': {
                      ...toolConfigs['llm-default'],
                      llmModel:
                        toolConfigs['llm-default']?.llmModel || 'claude-sonnet-4-5-20250929',
                      llmEnabled: true,
                      llmInstructions: toolConfigs['llm-default']?.llmInstructions || '',
                      creativityLevel: value,
                    },
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-muted-foreground mt-2 text-xs">
                Controls how varied the tool&apos;s responses are. Higher creativity produces more
                diverse outputs.
              </p>
            </div>

            <div>
              <Label className="text-foreground mb-3 block text-sm font-medium">
                {t('instructionsLabel')}
              </Label>
              <Textarea
                placeholder={t('instructionsPlaceholder')}
                value={toolConfigs['llm-default']?.llmInstructions || ''}
                onChange={(e) =>
                  setToolConfigs({
                    ...toolConfigs,
                    'llm-default': {
                      ...toolConfigs['llm-default'],
                      llmModel:
                        toolConfigs['llm-default']?.llmModel || 'claude-sonnet-4-5-20250929',
                      llmEnabled: true,
                      llmInstructions: e.target.value,
                      creativityLevel: toolConfigs['llm-default']?.creativityLevel || 'medium',
                    },
                  })
                }
                rows={6}
              />
            </div>
          </div>
        )}

        {/* Authentication/Configuration Step */}
        {step === 'auth' && (
          <div className="mb-12 space-y-8">
            {isCustomTool && customToolType === 'api' ? (
              <>
                {/* Custom Tool Configuration */}
                <div>
                  <Label className="text-foreground mb-3 block text-sm font-medium">
                    {t('toolNameLabel')}
                  </Label>
                  <Input
                    placeholder={t('toolNamePlaceholderApi')}
                    value={toolName}
                    onChange={(e) => setToolName(e.target.value)}
                  />
                </div>

                <div>
                  <Label className="text-foreground mb-3 block text-sm font-medium">
                    {t('descriptionLabel')}
                  </Label>
                  <Textarea
                    placeholder={t('descriptionPlaceholderApi')}
                    value={toolDescription}
                    onChange={(e) => setToolDescription(e.target.value)}
                    rows={3}
                  />
                </div>

                <div>
                  <Label className="text-foreground mb-3 block text-sm font-medium">
                    {t('baseUrlLabel')}
                  </Label>
                  <Input
                    type="url"
                    placeholder={t('baseUrlPlaceholder')}
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                  />
                </div>

                <div>
                  <Label className="text-foreground mb-3 block text-sm font-medium">
                    {t('authenticationLabel')}
                  </Label>
                  <Select
                    value={authType}
                    onValueChange={(value: AuthenticationType) => {
                      setAuthType(value)
                      setAuthData({})
                    }}
                  >
                    <SelectTrigger className="mb-4">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">{t('authTypeNone')}</SelectItem>
                      <SelectItem value="api-key">{t('authTypeApiKey')}</SelectItem>
                      <SelectItem value="bearer">{t('authTypeBearer')}</SelectItem>
                      <SelectItem value="basic">{t('authTypeBasic')}</SelectItem>
                    </SelectContent>
                  </Select>

                  {authType === 'api-key' && (
                    <div className="space-y-4">
                      <Input
                        placeholder={t('apiKeyHeaderPlaceholder')}
                        value={authData.apiKeyHeader || ''}
                        onChange={(e) => setAuthData({ ...authData, apiKeyHeader: e.target.value })}
                      />
                      <Input
                        type="password"
                        placeholder={t('apiKeyValuePlaceholder')}
                        value={authData.apiKeyValue || ''}
                        onChange={(e) => setAuthData({ ...authData, apiKeyValue: e.target.value })}
                      />
                    </div>
                  )}

                  {authType === 'bearer' && (
                    <Input
                      type="password"
                      placeholder={t('bearerTokenPlaceholder')}
                      value={authData.bearerToken || ''}
                      onChange={(e) => setAuthData({ ...authData, bearerToken: e.target.value })}
                    />
                  )}

                  {authType === 'basic' && (
                    <div className="space-y-4">
                      <Input
                        placeholder={t('usernamePlaceholder')}
                        value={authData.username || ''}
                        onChange={(e) => setAuthData({ ...authData, username: e.target.value })}
                      />
                      <Input
                        type="password"
                        placeholder={t('passwordPlaceholder')}
                        value={authData.password || ''}
                        onChange={(e) => setAuthData({ ...authData, password: e.target.value })}
                      />
                    </div>
                  )}
                </div>
              </>
            ) : (
              <>
                {/* Pre-built Tool Auth Fields */}
                {platform.authFields.map((field) => (
                  <div key={field.name}>
                    <Label className="text-foreground mb-3 block text-sm font-medium">
                      {field.label}
                      {field.required && (
                        <span className="text-destructive ml-1">{t('requiredField')}</span>
                      )}
                    </Label>
                    <Input
                      type={field.type}
                      placeholder={field.placeholder}
                      value={authData[field.name] || ''}
                      onChange={(e) => setAuthData({ ...authData, [field.name]: e.target.value })}
                    />
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {/* Tools Selection Step */}
        {step === 'tools' && (
          <div className="mb-12">
            {/* OpenAPI Discovery (only for API-based custom tools) */}
            {isCustomTool && customToolType === 'api' && (
              <>
                {/* Toggle between OpenAPI and Manual */}
                <div className="mb-8">
                  <div className="border-border bg-muted/50 inline-flex rounded-lg border p-1">
                    <button
                      onClick={() => setDiscoveryMethod('openapi')}
                      className={`rounded-md px-4 py-2 text-sm font-medium transition-all ${
                        discoveryMethod === 'openapi'
                          ? 'bg-background text-foreground shadow-sm'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {t('autoDiscover')}
                    </button>
                    <button
                      onClick={() => setDiscoveryMethod('manual')}
                      className={`rounded-md px-4 py-2 text-sm font-medium transition-all ${
                        discoveryMethod === 'manual'
                          ? 'bg-background text-foreground shadow-sm'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {t('addManually')}
                    </button>
                  </div>
                </div>

                {/* OpenAPI Discovery */}
                {discoveryMethod === 'openapi' && (
                  <div className="mb-8">
                    <p className="text-muted-foreground mb-4 text-sm">{t('openApiDescription')}</p>
                    <div className="flex gap-2">
                      <Input
                        placeholder={t('openApiUrlPlaceholder')}
                        value={openApiUrl}
                        onChange={(e) => setOpenApiUrl(e.target.value)}
                        disabled={isDiscovering}
                        className="flex-1"
                      />
                      <Button onClick={handleDiscoverEndpoints} disabled={isDiscovering}>
                        {isDiscovering ? t('discovering') : t('discover')}
                      </Button>
                    </div>
                  </div>
                )}

                {/* Manual Endpoint Creation */}
                {discoveryMethod === 'manual' && (
                  <div className="mb-8">
                    <div className="mb-4 flex items-center justify-between">
                      <p className="text-muted-foreground text-sm">
                        {t('manualEndpointsDescription')}
                      </p>
                      {!showEndpointForm && (
                        <Button onClick={() => setShowEndpointForm(true)} size="sm">
                          {t('addEndpoint')}
                        </Button>
                      )}
                    </div>

                    {showEndpointForm && (
                      <div className="border-border bg-card shadow-soft-xs space-y-4 rounded-xl border p-5">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label className="text-foreground mb-2 block text-xs font-medium">
                              {t('endpointNameLabel')}
                            </Label>
                            <Input
                              placeholder={t('endpointNamePlaceholder')}
                              value={newEndpoint.name}
                              onChange={(e) =>
                                setNewEndpoint({ ...newEndpoint, name: e.target.value })
                              }
                            />
                          </div>
                          <div>
                            <Label className="text-foreground mb-2 block text-xs font-medium">
                              {t('httpMethodLabel')}
                            </Label>
                            <Select
                              value={newEndpoint.method}
                              onValueChange={(value: HttpMethod) =>
                                setNewEndpoint({ ...newEndpoint, method: value })
                              }
                            >
                              <SelectTrigger className="h-10">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="GET">GET</SelectItem>
                                <SelectItem value="POST">POST</SelectItem>
                                <SelectItem value="PUT">PUT</SelectItem>
                                <SelectItem value="DELETE">DELETE</SelectItem>
                                <SelectItem value="PATCH">PATCH</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>

                        <div>
                          <Label className="text-foreground mb-2 block text-xs font-medium">
                            {t('pathLabel')}
                          </Label>
                          <Input
                            placeholder={t('pathPlaceholder')}
                            value={newEndpoint.path}
                            onChange={(e) =>
                              setNewEndpoint({ ...newEndpoint, path: e.target.value })
                            }
                          />
                        </div>

                        <div>
                          <Label className="text-foreground mb-2 block text-xs font-medium">
                            {t('descriptionLabel')}
                          </Label>
                          <Textarea
                            placeholder={t('endpointDescriptionPlaceholder')}
                            value={newEndpoint.description}
                            onChange={(e) =>
                              setNewEndpoint({ ...newEndpoint, description: e.target.value })
                            }
                            rows={2}
                            className="text-xs"
                          />
                        </div>

                        <div className="flex gap-2 pt-2">
                          <Button onClick={handleAddEndpoint} size="sm">
                            {tCommon('add')}
                          </Button>
                          <Button
                            onClick={() => {
                              setShowEndpointForm(false)
                              setNewEndpoint({ name: '', description: '', method: 'GET', path: '' })
                            }}
                            variant="ghost"
                            size="sm"
                          >
                            {tCommon('cancel')}
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}

            <div className="mb-6">
              <Label className="text-foreground mb-2 block text-sm font-medium">
                {isCustomTool || isSubAgent
                  ? isSubAgent
                    ? t('subAgent')
                    : customToolType === 'llm'
                      ? t('llmTool')
                      : t('apiEndpoints')
                  : t('selectTools')}
              </Label>
              <p className="text-muted-foreground text-xs">
                {t('toolsSelectedCount', { count: enabledToolIds.length, total: tools.length })}
              </p>
            </div>

            {tools.length === 0 && isCustomTool && customToolType === 'api' ? (
              <div className="border-border bg-card shadow-soft-xs rounded-xl border py-12 text-center">
                <p className="text-muted-foreground mb-2 text-sm">{t('noEndpointsYet')}</p>
                <p className="text-muted-foreground text-xs">{t('noEndpointsHelp')}</p>
              </div>
            ) : (
              <div className="space-y-2">
                {tools.map((tool) => {
                  const isExpanded = expandedToolId === tool.id
                  const isEnabled = enabledToolIds.includes(tool.id)
                  const config = toolConfigs[tool.id] || {
                    llmEnabled: false,
                    llmModel: 'claude-sonnet-4',
                    llmInstructions: '',
                    creativityLevel: 'medium' as const,
                  }

                  return (
                    <div
                      key={tool.id}
                      className={`rounded-xl border transition-all duration-200 ease-out ${
                        isEnabled
                          ? 'border-primary bg-primary/5 shadow-soft-sm'
                          : 'border-border bg-card shadow-soft-xs hover:shadow-soft-sm hover:border-border'
                      }`}
                    >
                      {/* Tool Header */}
                      <div className="px-5 py-4">
                        <div className="flex items-start gap-3">
                          <input
                            type="checkbox"
                            checked={isEnabled}
                            onChange={() => handleToggleTool(tool.id)}
                            className="mt-0.5 h-4 w-4 cursor-pointer"
                          />
                          <div className="flex-1">
                            <p className="text-foreground text-sm font-medium">{tool.name}</p>
                            <p className="text-muted-foreground mt-1 text-xs">{tool.description}</p>
                          </div>
                        </div>
                      </div>

                      {/* LLM Configuration (Expanded) - Optional for API custom tools */}
                      {isExpanded && isEnabled && isCustomTool && customToolType === 'api' && (
                        <div className="border-border border-t px-5 pt-4 pb-5">
                          <div className="bg-muted/30 border-border space-y-4 rounded-lg border p-4">
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="text-foreground text-sm font-medium">
                                  {t('enhanceWithLlm')}
                                </div>
                                <p className="text-muted-foreground mt-0.5 text-xs">
                                  {t('enhanceWithLlmDescription')}
                                </p>
                              </div>
                              <button
                                type="button"
                                onClick={() => {
                                  const newConfig = {
                                    llmEnabled: !config.llmEnabled,
                                    llmModel: config.llmModel,
                                    llmInstructions: config.llmInstructions,
                                    creativityLevel: config.creativityLevel,
                                  }
                                  setToolConfigs({
                                    ...toolConfigs,
                                    [tool.id]: newConfig,
                                  })
                                }}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                                  config.llmEnabled ? 'bg-primary' : 'bg-muted-foreground/30'
                                }`}
                              >
                                <span
                                  className={`bg-background inline-block h-4 w-4 transform rounded-full transition-transform ${
                                    config.llmEnabled ? 'translate-x-6' : 'translate-x-1'
                                  }`}
                                />
                              </button>
                            </div>

                            {config.llmEnabled && (
                              <div className="space-y-3 pt-2">
                                <div>
                                  <Label className="text-muted-foreground mb-2 block text-xs">
                                    {t('modelLabel')}
                                  </Label>
                                  <Select
                                    value={config.llmModel}
                                    onValueChange={(value) =>
                                      setToolConfigs({
                                        ...toolConfigs,
                                        [tool.id]: { ...config, llmModel: value },
                                      })
                                    }
                                  >
                                    <SelectTrigger className="bg-background h-9 text-xs">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="claude-sonnet-4">
                                        {t('modelClaudeSonnet4')}
                                      </SelectItem>
                                      <SelectItem value="claude-opus-4">
                                        {t('modelClaudeOpus4')}
                                      </SelectItem>
                                      <SelectItem value="gpt-4">{t('modelGpt4')}</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>

                                <div>
                                  <Label className="text-muted-foreground mb-2 block text-xs">
                                    {t('instructionsLabel')}
                                  </Label>
                                  <Textarea
                                    placeholder={t('llmInstructionsPlaceholder')}
                                    value={config.llmInstructions}
                                    onChange={(e) =>
                                      setToolConfigs({
                                        ...toolConfigs,
                                        [tool.id]: { ...config, llmInstructions: e.target.value },
                                      })
                                    }
                                    rows={3}
                                    className="bg-background text-xs"
                                  />
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Schema Configuration (Expanded) - For all custom tools and LLM tools */}
                      {isExpanded && isEnabled && (isCustomTool || tool.toolType === 'llm') && (
                        <div className="border-border space-y-10 border-t px-6 pt-4 pb-6">
                          {/* Input Fields */}
                          <div>
                            <div className="mb-6 flex items-center justify-between">
                              <div>
                                <h3 className="text-foreground mb-1 text-sm font-medium">
                                  {t('inputFieldsTitle')}
                                </h3>
                                <p className="text-muted-foreground text-sm">
                                  {t('inputFieldsDescription')}
                                </p>
                              </div>
                              <Button
                                onClick={() => addInputField(tool.id)}
                                variant="outline"
                                size="default"
                              >
                                {t('addField')}
                              </Button>
                            </div>

                            <div className="space-y-4">
                              {(toolSchemas[tool.id]?.inputFields || []).map((field, index) => (
                                <div
                                  key={index}
                                  className="border-border bg-card shadow-soft-xs space-y-4 rounded-xl border p-5"
                                >
                                  <div className="grid grid-cols-2 gap-4">
                                    <div>
                                      <Label className="text-muted-foreground mb-2 block text-xs">
                                        {t('fieldNameLabel')}
                                      </Label>
                                      <Input
                                        placeholder={t('fieldNamePlaceholder')}
                                        value={field.name}
                                        onChange={(e) =>
                                          updateInputField(tool.id, index, { name: e.target.value })
                                        }
                                      />
                                    </div>
                                    <div>
                                      <Label className="text-muted-foreground mb-2 block text-xs">
                                        {t('fieldTypeLabel')}
                                      </Label>
                                      <Select
                                        value={field.type}
                                        onValueChange={(
                                          value: 'text' | 'number' | 'boolean' | 'select'
                                        ) => updateInputField(tool.id, index, { type: value })}
                                      >
                                        <SelectTrigger>
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="text">{t('fieldTypeText')}</SelectItem>
                                          <SelectItem value="number">
                                            {t('fieldTypeNumber')}
                                          </SelectItem>
                                          <SelectItem value="boolean">
                                            {t('fieldTypeBoolean')}
                                          </SelectItem>
                                          <SelectItem value="select">
                                            {t('fieldTypeSelect')}
                                          </SelectItem>
                                        </SelectContent>
                                      </Select>
                                    </div>
                                  </div>

                                  <div>
                                    <Label className="text-muted-foreground mb-2 block text-xs">
                                      {t('fieldDescriptionLabel')}
                                    </Label>
                                    <Input
                                      placeholder={t('fieldDescriptionPlaceholder')}
                                      value={field.description}
                                      onChange={(e) =>
                                        updateInputField(tool.id, index, {
                                          description: e.target.value,
                                        })
                                      }
                                    />
                                    <p className="text-muted-foreground mt-1.5 text-xs">
                                      {t('fieldDescriptionHelp')}
                                    </p>
                                  </div>

                                  {field.type === 'select' && (
                                    <div>
                                      <Label className="text-muted-foreground mb-2 block text-xs">
                                        {t('optionsLabel')}
                                      </Label>
                                      <Input
                                        placeholder={t('optionsPlaceholder')}
                                        value={field.options?.join(', ') || ''}
                                        onChange={(e) =>
                                          updateInputField(tool.id, index, {
                                            options: e.target.value.split(',').map((o) => o.trim()),
                                          })
                                        }
                                      />
                                      <p className="text-muted-foreground mt-1.5 text-xs">
                                        {t('optionsHelp')}
                                      </p>
                                    </div>
                                  )}

                                  <div className="border-border flex items-center justify-between border-t pt-4">
                                    <label className="text-muted-foreground flex cursor-pointer items-center gap-2 text-xs">
                                      <input
                                        type="checkbox"
                                        checked={field.required}
                                        onChange={(e) =>
                                          updateInputField(tool.id, index, {
                                            required: e.target.checked,
                                          })
                                        }
                                        className="h-4 w-4"
                                      />
                                      {t('requiredFieldLabel')}
                                    </label>
                                    <button
                                      onClick={() => removeInputField(tool.id, index)}
                                      className="text-muted-foreground hover:text-foreground text-xs transition-colors"
                                    >
                                      {t('removeField')}
                                    </button>
                                  </div>
                                </div>
                              ))}

                              {(toolSchemas[tool.id]?.inputFields || []).length === 0 && (
                                <div className="border-border rounded-xl border-2 border-dashed py-12 text-center">
                                  <p className="text-muted-foreground text-sm">
                                    {t('noInputFieldsYet')}
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Output Configuration */}
                          <div>
                            <div className="mb-6 flex items-center justify-between">
                              <div>
                                <h3 className="text-foreground mb-1 text-sm font-medium">
                                  {t('outputFieldsTitle')}
                                </h3>
                                <p className="text-muted-foreground text-sm">
                                  {t('outputFieldsDescription')}
                                </p>
                              </div>
                              <Button
                                onClick={() => addOutputField(tool.id)}
                                variant="outline"
                                size="default"
                              >
                                {t('addField')}
                              </Button>
                            </div>

                            <div className="space-y-4">
                              {(toolSchemas[tool.id]?.outputFields || []).map((field, index) => (
                                <div
                                  key={index}
                                  className="border-border bg-card shadow-soft-xs space-y-4 rounded-xl border p-5"
                                >
                                  <div className="grid grid-cols-2 gap-4">
                                    <div>
                                      <Label className="text-muted-foreground mb-2 block text-xs">
                                        {t('fieldNameLabel')}
                                      </Label>
                                      <Input
                                        placeholder={t('outputFieldNamePlaceholder')}
                                        value={field.name}
                                        onChange={(e) =>
                                          updateOutputField(tool.id, index, {
                                            name: e.target.value,
                                          })
                                        }
                                      />
                                    </div>
                                    <div>
                                      <Label className="text-muted-foreground mb-2 block text-xs">
                                        {t('fieldTypeLabel')}
                                      </Label>
                                      <Select
                                        value={field.type}
                                        onValueChange={(value: 'text' | 'number' | 'boolean') =>
                                          updateOutputField(tool.id, index, { type: value })
                                        }
                                      >
                                        <SelectTrigger>
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="text">{t('fieldTypeText')}</SelectItem>
                                          <SelectItem value="number">
                                            {t('fieldTypeNumber')}
                                          </SelectItem>
                                          <SelectItem value="boolean">
                                            {t('fieldTypeBoolean')}
                                          </SelectItem>
                                        </SelectContent>
                                      </Select>
                                    </div>
                                  </div>
                                  <div>
                                    <Label className="text-muted-foreground mb-2 block text-xs">
                                      {t('fieldDescriptionLabel')}
                                    </Label>
                                    <Input
                                      placeholder={t('outputFieldDescriptionPlaceholder')}
                                      value={field.description}
                                      onChange={(e) =>
                                        updateOutputField(tool.id, index, {
                                          description: e.target.value,
                                        })
                                      }
                                    />
                                    <p className="text-muted-foreground mt-1.5 text-xs">
                                      {t('outputFieldDescriptionHelp')}
                                    </p>
                                  </div>
                                  <div className="border-border flex justify-end border-t pt-4">
                                    <button
                                      onClick={() => removeOutputField(tool.id, index)}
                                      className="text-muted-foreground hover:text-foreground text-xs transition-colors"
                                    >
                                      {t('removeField')}
                                    </button>
                                  </div>
                                </div>
                              ))}

                              {(toolSchemas[tool.id]?.outputFields || []).length === 0 && (
                                <div className="border-border rounded-xl border-2 border-dashed py-12 text-center">
                                  <p className="text-muted-foreground text-sm">
                                    {t('noOutputFieldsYet')}
                                  </p>
                                </div>
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
        )}

        {/* Actions */}
        <div className="border-border flex items-center justify-between border-t pt-8">
          <button
            onClick={() => {
              if (step === 'type-selection') {
                router.push(`/agents/${resolvedParams.id}/tools/add`)
              } else if (step === 'config') {
                if (isCustomTool) {
                  setStep('type-selection')
                } else {
                  router.push(`/agents/${resolvedParams.id}/tools/add`)
                }
              } else if (step === 'auth') {
                if (isCustomTool) {
                  setStep('type-selection')
                } else {
                  router.push(`/agents/${resolvedParams.id}/tools/add`)
                }
              } else if (step === 'tools') {
                if (isSubAgent || (isCustomTool && customToolType === 'llm')) {
                  setStep('config')
                } else if (isCustomTool && customToolType === 'api') {
                  setStep('auth')
                } else {
                  setStep('auth')
                }
              }
            }}
            className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
          >
            <span>←</span>
          </button>

          <div>
            {step === 'config' && (
              <Button onClick={handleNextFromConfig} size="lg">
                {t('next')}
              </Button>
            )}

            {step === 'auth' && (
              <Button onClick={handleNextToTools} size="lg">
                {t('next')}
              </Button>
            )}

            {step === 'tools' && (
              <Button onClick={handleSave} size="lg">
                {t('addButton', { name: toolName || platform.name })}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
