'use client'

import { useState, use } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
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
import { toast } from 'sonner'
import { apiClient } from '@/lib/api/client'

type OutputMode = 'full' | 'extract' | 'llm'
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
type AuthType = 'none' | 'api-key' | 'bearer' | 'basic'

interface InputField {
  name: string
  type: 'string' | 'number' | 'boolean'
  description: string
  required: boolean
}

interface OutputField {
  name: string
  jsonpath: string
  description: string
}

interface TestResult {
  success: boolean
  output: unknown
  error?: string
  debugInfo?: {
    executionTimeMs: number
    statusCode: number
    urlCalled: string
    rawResponse?: unknown
  }
}

export default function AddApiToolPage({
  params,
}: {
  params: Promise<{ id: string; locale: string }>
}) {
  const resolvedParams = use(params)
  const router = useRouter()

  // 1. Tool Information
  const [toolName, setToolName] = useState('')
  const [toolDescription, setToolDescription] = useState('')

  // 2. API Configuration
  const [endpoint, setEndpoint] = useState('')
  const [method, setMethod] = useState<HttpMethod>('GET')
  const [authType, setAuthType] = useState<AuthType>('none')
  const [authConfig, setAuthConfig] = useState<Record<string, string>>({})

  // 3. Tool Input
  const [inputFields, setInputFields] = useState<InputField[]>([])

  // 4. Tool Output
  const [outputMode, setOutputMode] = useState<OutputMode>('full')
  const [outputFields, setOutputFields] = useState<OutputField[]>([])
  const [llmInstructions, setLlmInstructions] = useState('')

  // Test Tool
  const [testInput, setTestInput] = useState<Record<string, string>>({})
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [isTesting, setIsTesting] = useState(false)

  // Add input field
  function addInputField() {
    setInputFields([...inputFields, { name: '', type: 'string', description: '', required: false }])
  }

  // Remove input field
  function removeInputField(index: number) {
    setInputFields(inputFields.filter((_, i) => i !== index))
  }

  // Update input field
  function updateInputField(index: number, updates: Partial<InputField>) {
    const updated = [...inputFields]
    const existing = updated[index]
    if (!existing) return
    updated[index] = { ...existing, ...updates }
    setInputFields(updated)
  }

  // Add output field (for extract mode)
  function addOutputField() {
    setOutputFields([...outputFields, { name: '', jsonpath: '', description: '' }])
  }

  // Remove output field
  function removeOutputField(index: number) {
    setOutputFields(outputFields.filter((_, i) => i !== index))
  }

  // Update output field
  function updateOutputField(index: number, updates: Partial<OutputField>) {
    const updated = [...outputFields]
    const existing = updated[index]
    if (!existing) return
    updated[index] = { ...existing, ...updates }
    setOutputFields(updated)
  }

  // Test the tool
  async function handleTestTool() {
    setIsTesting(true)
    setTestResult(null)

    try {
      const outputMapping: Record<string, string> = {}
      outputFields.forEach((field) => {
        if (field.name && field.jsonpath) {
          outputMapping[field.name] = field.jsonpath
        }
      })

      const response = await apiClient.testTool({
        endpoint,
        method,
        authentication: authType,
        authConfig,
        testInput,
        outputMode,
        outputMapping,
        llmConfig: outputMode === 'llm' ? { instructions: llmInstructions } : undefined,
      })

      setTestResult(response)

      if (response.success) {
        toast.success('Tool tested successfully!')
      } else {
        toast.error(response.error || 'Test failed')
      }
    } catch (error) {
      console.error('Test failed:', error)
      toast.error('Failed to test tool')
      setTestResult({
        success: false,
        output: null,
        error: error instanceof Error ? error.message : 'Unknown error',
      })
    } finally {
      setIsTesting(false)
    }
  }

  // Save the tool
  async function handleSave() {
    if (!toolName.trim()) {
      toast.error('Please enter a tool name')
      return
    }

    if (!endpoint.trim()) {
      toast.error('Please enter an endpoint URL')
      return
    }

    try {
      // 1. Create integration
      const integrationConfig: Record<string, unknown> = {
        authentication: authType,
        baseUrl: endpoint,
        method,
        ...authConfig,
      }

      const integration = await apiClient.createIntegration({
        agent_id: resolvedParams.id,
        type: 'custom-tool',
        name: toolName,
        description: toolDescription || undefined,
        config: integrationConfig,
      })

      // 2. Build tool schema
      const inputProperties: Record<string, { type: string; description: string }> = {}
      const requiredFields: string[] = []

      inputFields.forEach((field) => {
        inputProperties[field.name] = {
          type: field.type,
          description: field.description,
        }
        if (field.required) {
          requiredFields.push(field.name)
        }
      })

      const toolSchema = {
        name: toolName.toLowerCase().replace(/\s+/g, '_'),
        input_schema: {
          type: 'object',
          properties: inputProperties,
          required: requiredFields,
        },
      }

      // 3. Build tool config
      const outputMapping: Record<string, string> = {}
      outputFields.forEach((field) => {
        if (field.name && field.jsonpath) {
          outputMapping[field.name] = field.jsonpath
        }
      })

      const toolConfig: Record<string, unknown> = {
        output_mode: outputMode,
      }

      if (outputMode === 'extract') {
        toolConfig.output_mapping = outputMapping
      } else if (outputMode === 'llm') {
        toolConfig.llm_instructions = llmInstructions
      }

      // 4. Create tool
      await apiClient.createTool({
        integration_id: integration.id,
        name: toolName,
        description: toolDescription || undefined,
        tool_type: 'api',
        tool_schema: toolSchema,
        config: toolConfig,
        is_enabled: true,
      })

      toast.success('Tool saved successfully!')
      router.push(`/${resolvedParams.locale}/agents/${resolvedParams.id}`)
    } catch (error) {
      console.error('Failed to save tool:', error)
      toast.error('Failed to save tool')
    }
  }

  return (
    <div className="bg-background min-h-screen">
      <div className="mx-auto max-w-4xl px-8 py-16">
        {/* Back Button */}
        <Link
          href={`/${resolvedParams.locale}/agents/${resolvedParams.id}`}
          className="text-muted-foreground hover:text-foreground mb-8 inline-flex items-center gap-1 transition-colors"
        >
          <span>←</span> Back
        </Link>

        {/* Header */}
        <div className="mb-12">
          <h1 className="text-foreground mb-2 text-3xl font-semibold tracking-tight">
            Add API Tool
          </h1>
          <p className="text-muted-foreground text-sm">
            Connect to any REST API endpoint and configure how your agent interacts with it
          </p>
        </div>

        {/* 1. Tool Information */}
        <section className="border-border bg-card mb-8 rounded-xl border p-6 shadow-sm">
          <h2 className="text-foreground mb-4 text-lg font-medium">1. Tool Information</h2>

          <div className="space-y-4">
            <div>
              <Label className="text-foreground mb-2 block text-sm">Tool Name</Label>
              <Input
                placeholder="Get Weather"
                value={toolName}
                onChange={(e) => setToolName(e.target.value)}
              />
            </div>

            <div>
              <Label className="text-foreground mb-2 block text-sm">Description</Label>
              <Textarea
                placeholder="Get current weather information for a city"
                value={toolDescription}
                onChange={(e) => setToolDescription(e.target.value)}
                rows={2}
              />
            </div>
          </div>
        </section>

        {/* 2. API Configuration */}
        <section className="border-border bg-card mb-8 rounded-xl border p-6 shadow-sm">
          <h2 className="text-foreground mb-4 text-lg font-medium">2. API Configuration</h2>

          <div className="space-y-4">
            <div>
              <Label className="text-foreground mb-2 block text-sm">
                Endpoint URL
                <span className="text-muted-foreground ml-2 font-normal">
                  (use {'{variable}'} for parameters)
                </span>
              </Label>
              <Input
                placeholder="https://wttr.in/{city}?format=j1"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-foreground mb-2 block text-sm">HTTP Method</Label>
                <Select value={method} onValueChange={(v) => setMethod(v as HttpMethod)}>
                  <SelectTrigger>
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

              <div>
                <Label className="text-foreground mb-2 block text-sm">Authentication</Label>
                <Select value={authType} onValueChange={(v) => setAuthType(v as AuthType)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    <SelectItem value="api-key">API Key</SelectItem>
                    <SelectItem value="bearer">Bearer Token</SelectItem>
                    <SelectItem value="basic">Basic Auth</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Auth Config Fields */}
            {authType === 'api-key' && (
              <div className="space-y-3 pt-2">
                <Input
                  placeholder="Header name (e.g., X-API-Key)"
                  value={authConfig.apiKeyHeader || ''}
                  onChange={(e) => setAuthConfig({ ...authConfig, apiKeyHeader: e.target.value })}
                />
                <Input
                  type="password"
                  placeholder="API Key value"
                  value={authConfig.apiKeyValue || ''}
                  onChange={(e) => setAuthConfig({ ...authConfig, apiKeyValue: e.target.value })}
                />
              </div>
            )}

            {authType === 'bearer' && (
              <Input
                type="password"
                placeholder="Bearer token"
                value={authConfig.bearerToken || ''}
                onChange={(e) => setAuthConfig({ ...authConfig, bearerToken: e.target.value })}
              />
            )}

            {authType === 'basic' && (
              <div className="grid grid-cols-2 gap-3 pt-2">
                <Input
                  placeholder="Username"
                  value={authConfig.username || ''}
                  onChange={(e) => setAuthConfig({ ...authConfig, username: e.target.value })}
                />
                <Input
                  type="password"
                  placeholder="Password"
                  value={authConfig.password || ''}
                  onChange={(e) => setAuthConfig({ ...authConfig, password: e.target.value })}
                />
              </div>
            )}
          </div>
        </section>

        {/* 3. Tool Input */}
        <section className="border-border bg-card mb-8 rounded-xl border p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-foreground text-lg font-medium">
              3. Tool Input (what the agent provides)
            </h2>
            <Button onClick={addInputField} size="sm" variant="outline">
              + Add Field
            </Button>
          </div>

          {inputFields.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              No input fields yet. Click &ldquo;Add Field&rdquo; to define parameters the agent will
              provide.
            </p>
          ) : (
            <div className="space-y-3">
              {inputFields.map((field, index) => (
                <div
                  key={index}
                  className="border-border flex items-start gap-3 rounded-lg border p-3"
                >
                  <div className="grid flex-1 grid-cols-4 gap-3">
                    <Input
                      placeholder="Field name"
                      value={field.name}
                      onChange={(e) => updateInputField(index, { name: e.target.value })}
                    />
                    <Select
                      value={field.type}
                      onValueChange={(v) =>
                        updateInputField(index, {
                          type: v as 'string' | 'number' | 'boolean',
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="string">Text</SelectItem>
                        <SelectItem value="number">Number</SelectItem>
                        <SelectItem value="boolean">Boolean</SelectItem>
                      </SelectContent>
                    </Select>
                    <Input
                      placeholder="Description"
                      value={field.description}
                      onChange={(e) => updateInputField(index, { description: e.target.value })}
                    />
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={field.required}
                        onChange={(e) => updateInputField(index, { required: e.target.checked })}
                        className="h-4 w-4"
                      />
                      <span className="text-sm">Required</span>
                    </div>
                  </div>
                  <button
                    onClick={() => removeInputField(index)}
                    className="text-muted-foreground hover:text-destructive mt-2"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 4. Tool Output */}
        <section className="border-border bg-card mb-8 rounded-xl border p-6 shadow-sm">
          <h2 className="text-foreground mb-4 text-lg font-medium">
            4. Tool Output (what the agent receives)
          </h2>

          {/* Output Mode Selection */}
          <div className="mb-4 space-y-3">
            <label className="flex items-start gap-3">
              <input
                type="radio"
                checked={outputMode === 'full'}
                onChange={() => setOutputMode('full')}
                className="mt-1"
              />
              <div>
                <div className="text-foreground font-medium">Return full API response</div>
                <div className="text-muted-foreground text-sm">
                  Return the complete response from the API (good for testing)
                </div>
              </div>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="radio"
                checked={outputMode === 'extract'}
                onChange={() => setOutputMode('extract')}
                className="mt-1"
              />
              <div>
                <div className="text-foreground font-medium">Extract specific fields</div>
                <div className="text-muted-foreground text-sm">
                  Use JSONPath to extract only the fields you need
                </div>
              </div>
            </label>

            <label className="flex items-start gap-3">
              <input
                type="radio"
                checked={outputMode === 'llm'}
                onChange={() => setOutputMode('llm')}
                className="mt-1"
              />
              <div>
                <div className="text-foreground font-medium">Transform with LLM</div>
                <div className="text-muted-foreground text-sm">
                  Use AI to transform or summarize the response
                </div>
              </div>
            </label>
          </div>

          {/* Extract Mode: Field Mapping */}
          {outputMode === 'extract' && (
            <div className="border-border mt-4 rounded-lg border p-4">
              <div className="mb-3 flex items-center justify-between">
                <Label className="text-sm font-medium">Field Mapping</Label>
                <Button onClick={addOutputField} size="sm" variant="outline">
                  + Add Field
                </Button>
              </div>

              {outputFields.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  No fields defined. Test the tool first to see the API response, then add fields.
                </p>
              ) : (
                <div className="space-y-2">
                  {outputFields.map((field, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <Input
                        placeholder="Output name (e.g., temperature)"
                        value={field.name}
                        onChange={(e) => updateOutputField(index, { name: e.target.value })}
                        className="flex-1"
                      />
                      <span className="text-muted-foreground">→</span>
                      <Input
                        placeholder="JSONPath (e.g., current_condition[0].temp_C)"
                        value={field.jsonpath}
                        onChange={(e) => updateOutputField(index, { jsonpath: e.target.value })}
                        className="flex-[2]"
                      />
                      <button
                        onClick={() => removeOutputField(index)}
                        className="text-muted-foreground hover:text-destructive"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* LLM Mode: Instructions */}
          {outputMode === 'llm' && (
            <div className="border-border mt-4 rounded-lg border p-4">
              <Label className="text-foreground mb-2 block text-sm">
                LLM Transformation Instructions
              </Label>
              <Textarea
                placeholder="Extract the temperature and weather condition in a human-readable format..."
                value={llmInstructions}
                onChange={(e) => setLlmInstructions(e.target.value)}
                rows={3}
              />
            </div>
          )}
        </section>

        {/* Test Tool Section */}
        <section className="border-border bg-card mb-8 rounded-xl border p-6 shadow-sm">
          <h2 className="text-foreground mb-4 text-lg font-medium">Test Tool</h2>

          {/* Test Input Fields */}
          {inputFields.length > 0 && (
            <div className="mb-4 space-y-3">
              <Label className="text-sm">Input Values</Label>
              {inputFields.map((field, index) => (
                <div key={index} className="flex items-center gap-3">
                  <span className="text-muted-foreground w-32 text-sm">{field.name}:</span>
                  <Input
                    placeholder={`Enter ${field.name}`}
                    value={testInput[field.name] || ''}
                    onChange={(e) => setTestInput({ ...testInput, [field.name]: e.target.value })}
                  />
                </div>
              ))}
            </div>
          )}

          <Button onClick={handleTestTool} disabled={isTesting} className="mb-4">
            {isTesting ? 'Testing...' : 'Test Tool →'}
          </Button>

          {/* Test Result */}
          {testResult && (
            <div className="border-border rounded-lg border p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-medium">
                  {testResult.success ? '✓ Success' : '✗ Failed'}
                </span>
                {testResult.debugInfo && (
                  <span className="text-muted-foreground text-xs">
                    {testResult.debugInfo.executionTimeMs}ms · {testResult.debugInfo.statusCode}
                  </span>
                )}
              </div>

              {testResult.success ? (
                <pre className="bg-muted text-foreground max-h-96 overflow-auto rounded p-3 text-xs">
                  {JSON.stringify(testResult.output, null, 2) as string}
                </pre>
              ) : (
                <div className="text-destructive text-sm">{testResult.error}</div>
              )}

              {/* Show raw response for extract mode */}
              {testResult.success &&
              outputMode === 'extract' &&
              testResult.debugInfo?.rawResponse ? (
                <details className="mt-3">
                  <summary className="text-muted-foreground cursor-pointer text-xs">
                    Show raw API response
                  </summary>
                  <pre className="bg-muted text-foreground mt-2 max-h-64 overflow-auto rounded p-3 text-xs">
                    {JSON.stringify(testResult.debugInfo.rawResponse, null, 2) as string}
                  </pre>
                </details>
              ) : null}
            </div>
          )}
        </section>

        {/* Save/Cancel Actions */}
        <div className="flex items-center justify-between">
          <Link
            href={`/${resolvedParams.locale}/agents/${resolvedParams.id}`}
            className="text-muted-foreground hover:text-foreground"
          >
            Cancel
          </Link>
          <Button onClick={handleSave} size="lg">
            Save Tool
          </Button>
        </div>
      </div>
    </div>
  )
}
