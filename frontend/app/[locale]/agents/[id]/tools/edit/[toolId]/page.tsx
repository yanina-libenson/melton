'use client'

import { useState, use, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { toast } from 'sonner'
import { apiClient } from '@/lib/api/client'

interface ToolSchema {
  input_schema?: {
    properties?: Record<string, { type: string; description: string }>
    required?: string[]
  }
  output_schema?: {
    properties?: Record<string, { type: string; description: string }>
    required?: string[]
  }
  name?: string
}

interface Tool {
  id: string
  sourceId: string
  name: string
  description?: string | null
  toolType?: 'llm' | 'api' | 'sub-agent' | null
  toolSchema?: ToolSchema
  config?: Record<string, unknown>
  isEnabled?: boolean
}

export default function EditToolPage({
  params,
}: {
  params: Promise<{ id: string; toolId: string; locale: string }>
}) {
  const resolvedParams = use(params)
  const router = useRouter()

  const [tool, setTool] = useState<Tool | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  // Form state
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [llmModel, setLlmModel] = useState('')
  const [llmInstructions, setLlmInstructions] = useState('')
  const [creativityLevel, setCreativityLevel] = useState<'low' | 'medium' | 'high'>('medium')
  const [inputFields, setInputFields] = useState<
    { name: string; type: string; description: string; required: boolean }[]
  >([])
  const [outputFields, setOutputFields] = useState<
    { name: string; type: string; description: string }[]
  >([])

  useEffect(() => {
    async function loadTool() {
      try {
        setIsLoading(true)
        const toolData = await apiClient.getTool(resolvedParams.toolId)
        setTool(toolData)

        // Populate form
        setName(toolData.name)
        setDescription(toolData.description || '')
        setLlmModel((toolData.config?.llm_model as string) || '')
        setLlmInstructions((toolData.config?.llm_instructions as string) || '')
        setCreativityLevel(
          (toolData.config?.creativity_level as 'low' | 'medium' | 'high') || 'medium'
        )

        // Parse input fields
        const inputSchema = toolData.toolSchema?.input_schema as
          | {
              properties?: Record<string, { type: string; description: string }>
              required?: string[]
            }
          | undefined
        const inputProps = inputSchema?.properties || {}
        const requiredFields = inputSchema?.required || []
        setInputFields(
          Object.entries(inputProps).map(([name, prop]) => ({
            name,
            type: prop.type,
            description: prop.description,
            required: requiredFields.includes(name),
          }))
        )

        // Parse output fields
        const outputSchema = toolData.toolSchema?.output_schema as
          | { properties?: Record<string, { type: string; description: string }> }
          | undefined
        const outputProps = outputSchema?.properties || {}
        setOutputFields(
          Object.entries(outputProps).map(([name, prop]) => ({
            name,
            type: prop.type,
            description: prop.description,
          }))
        )
      } catch (error) {
        console.error('Failed to load tool:', error)
        toast.error('Failed to load tool')
      } finally {
        setIsLoading(false)
      }
    }

    loadTool()
  }, [resolvedParams.toolId])

  async function handleSave() {
    if (!tool) return

    setIsSaving(true)
    try {
      // Build tool schema payload
      const toolSchemaPayload = {
        name: tool.toolSchema?.name || tool.name.toLowerCase().replace(/\s+/g, '_'),
        description: description,
        input_schema: {
          type: 'object',
          properties: Object.fromEntries(
            inputFields.map((field) => [
              field.name,
              {
                type: field.type,
                description: field.description,
              },
            ])
          ),
          required: inputFields.filter((f) => f.required).map((f) => f.name),
        },
        output_schema:
          outputFields.length > 0
            ? {
                type: 'object',
                properties: Object.fromEntries(
                  outputFields.map((field) => [
                    field.name,
                    {
                      type: field.type,
                      description: field.description,
                    },
                  ])
                ),
                required: outputFields.map((f) => f.name),
              }
            : undefined,
      }

      // Build config payload
      const configPayload: Record<string, unknown> = {
        ...(tool.config || {}),
      }

      if (tool.toolType === 'llm') {
        configPayload.llm_model = llmModel
        configPayload.llm_instructions = llmInstructions
        configPayload.creativity_level = creativityLevel
      }

      await apiClient.updateTool(resolvedParams.toolId, {
        name,
        description,
        tool_schema: toolSchemaPayload,
        config: configPayload,
        is_enabled: tool.isEnabled ?? true,
      })

      toast.success('Tool updated successfully')
      router.push(`/${resolvedParams.locale}/agents/${resolvedParams.id}`)
    } catch (error) {
      console.error('Failed to update tool:', error)
      toast.error('Failed to update tool')
    } finally {
      setIsSaving(false)
    }
  }

  async function handleDelete() {
    if (!tool) return

    if (confirm(`Are you sure you want to delete "${tool.name}"?`)) {
      try {
        await apiClient.deleteTool(resolvedParams.toolId)
        toast.success('Tool deleted successfully')
        router.push(`/${resolvedParams.locale}/agents/${resolvedParams.id}`)
      } catch (error) {
        console.error('Failed to delete tool:', error)
        toast.error('Failed to delete tool')
      }
    }
  }

  function addInputField() {
    setInputFields([...inputFields, { name: '', type: 'string', description: '', required: false }])
  }

  function removeInputField(index: number) {
    setInputFields(inputFields.filter((_, i) => i !== index))
  }

  function updateInputField(
    index: number,
    field: Partial<{ name: string; type: string; description: string; required: boolean }>
  ) {
    setInputFields(inputFields.map((f, i) => (i === index ? { ...f, ...field } : f)))
  }

  function addOutputField() {
    setOutputFields([...outputFields, { name: '', type: 'string', description: '' }])
  }

  function removeOutputField(index: number) {
    setOutputFields(outputFields.filter((_, i) => i !== index))
  }

  function updateOutputField(
    index: number,
    field: Partial<{ name: string; type: string; description: string }>
  ) {
    setOutputFields(outputFields.map((f, i) => (i === index ? { ...f, ...field } : f)))
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground text-sm">Loading...</p>
      </div>
    )
  }

  if (!tool) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground text-sm">Tool not found</p>
      </div>
    )
  }

  return (
    <div className="bg-background min-h-screen">
      <div className="mx-auto max-w-3xl px-8 py-16">
        {/* Back Button */}
        <Link
          href={`/agents/${resolvedParams.id}`}
          className="text-muted-foreground hover:text-foreground mb-8 inline-flex items-center gap-1 transition-colors"
        >
          <span>←</span>
        </Link>

        {/* Header */}
        <div className="mb-12">
          <h1 className="text-foreground mb-2 text-4xl font-semibold tracking-tight">Edit Tool</h1>
          <p className="text-muted-foreground text-sm">Configure your {tool.toolType} tool</p>
        </div>

        {/* Basic Info */}
        <div className="mb-12">
          <div className="mb-6">
            <Label htmlFor="name" className="text-foreground mb-2 block text-sm font-medium">
              Tool Name
            </Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Tool"
            />
          </div>

          <div className="mb-6">
            <Label htmlFor="description" className="text-foreground mb-2 block text-sm font-medium">
              Description
            </Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this tool do?"
              rows={3}
            />
          </div>
        </div>

        {/* LLM Configuration (only for LLM tools) */}
        {tool.toolType === 'llm' && (
          <div className="mb-12">
            <h2 className="text-foreground mb-6 text-xl font-semibold">LLM Configuration</h2>

            <div className="mb-6">
              <Label htmlFor="llmModel" className="text-foreground mb-2 block text-sm font-medium">
                Model
              </Label>
              <select
                id="llmModel"
                value={llmModel}
                onChange={(e) => setLlmModel(e.target.value)}
                className="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
              >
                <option value="claude-sonnet-4-5-20250929">Claude Sonnet 4.5</option>
                <option value="claude-opus-4-5-20251101">Claude Opus 4.5</option>
                <option value="gpt-4o">GPT-4o</option>
                <option value="gpt-4o-mini">GPT-4o Mini</option>
                <option value="o1">OpenAI o1</option>
                <option value="o1-mini">OpenAI o1-mini</option>
                <option value="gemini-2.0-flash-exp">Gemini 2.0 Flash</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
              </select>
            </div>

            <div className="mb-6">
              <Label
                htmlFor="creativityLevel"
                className="text-foreground mb-2 block text-sm font-medium"
              >
                Creativity Level
              </Label>
              <select
                id="creativityLevel"
                value={creativityLevel}
                onChange={(e) => setCreativityLevel(e.target.value as 'low' | 'medium' | 'high')}
                className="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
              >
                <option value="low">Low (More Deterministic)</option>
                <option value="medium">Medium (Balanced)</option>
                <option value="high">High (More Creative)</option>
              </select>
            </div>

            <div className="mb-6">
              <Label
                htmlFor="llmInstructions"
                className="text-foreground mb-2 block text-sm font-medium"
              >
                Instructions
              </Label>
              <Textarea
                id="llmInstructions"
                value={llmInstructions}
                onChange={(e) => setLlmInstructions(e.target.value)}
                placeholder="Detailed instructions for the LLM..."
                rows={6}
              />
            </div>
          </div>
        )}

        {/* Input Fields */}
        <div className="mb-12">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-foreground text-xl font-semibold">Input Fields</h2>
            <Button onClick={addInputField} variant="outline" size="sm">
              + Add Field
            </Button>
          </div>

          <div className="space-y-4">
            {inputFields.map((field, index) => (
              <div key={index} className="border-border rounded-lg border p-4">
                <div className="mb-4 grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-foreground mb-2 block text-sm font-medium">
                      Field Name
                    </Label>
                    <Input
                      value={field.name}
                      onChange={(e) => updateInputField(index, { name: e.target.value })}
                      placeholder="field_name"
                    />
                  </div>
                  <div>
                    <Label className="text-foreground mb-2 block text-sm font-medium">Type</Label>
                    <select
                      value={field.type}
                      onChange={(e) => updateInputField(index, { type: e.target.value })}
                      className="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
                    >
                      <option value="string">String</option>
                      <option value="number">Number</option>
                      <option value="boolean">Boolean</option>
                    </select>
                  </div>
                </div>
                <div className="mb-4">
                  <Label className="text-foreground mb-2 block text-sm font-medium">
                    Description
                  </Label>
                  <Input
                    value={field.description}
                    onChange={(e) => updateInputField(index, { description: e.target.value })}
                    placeholder="What is this field for?"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={field.required}
                      onChange={(e) => updateInputField(index, { required: e.target.checked })}
                      className="h-4 w-4"
                    />
                    <span className="text-foreground text-sm">Required</span>
                  </label>
                  <button
                    onClick={() => removeInputField(index)}
                    className="text-muted-foreground hover:text-destructive text-sm transition-colors"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Output Fields */}
        <div className="mb-12">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-foreground text-xl font-semibold">Output Fields</h2>
            <Button onClick={addOutputField} variant="outline" size="sm">
              + Add Field
            </Button>
          </div>

          <div className="space-y-4">
            {outputFields.map((field, index) => (
              <div key={index} className="border-border rounded-lg border p-4">
                <div className="mb-4 grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-foreground mb-2 block text-sm font-medium">
                      Field Name
                    </Label>
                    <Input
                      value={field.name}
                      onChange={(e) => updateOutputField(index, { name: e.target.value })}
                      placeholder="field_name"
                    />
                  </div>
                  <div>
                    <Label className="text-foreground mb-2 block text-sm font-medium">Type</Label>
                    <select
                      value={field.type}
                      onChange={(e) => updateOutputField(index, { type: e.target.value })}
                      className="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
                    >
                      <option value="string">String</option>
                      <option value="number">Number</option>
                      <option value="boolean">Boolean</option>
                    </select>
                  </div>
                </div>
                <div className="mb-4">
                  <Label className="text-foreground mb-2 block text-sm font-medium">
                    Description
                  </Label>
                  <Input
                    value={field.description}
                    onChange={(e) => updateOutputField(index, { description: e.target.value })}
                    placeholder="What does this field contain?"
                  />
                </div>
                <div className="flex justify-end">
                  <button
                    onClick={() => removeOutputField(index)}
                    className="text-muted-foreground hover:text-destructive text-sm transition-colors"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="border-border border-t pt-8">
          <div className="mb-6 flex items-center justify-between">
            <button
              onClick={handleDelete}
              className="text-muted-foreground hover:text-destructive text-sm transition-colors"
            >
              Delete Tool
            </button>
          </div>
          <div className="flex items-center justify-between">
            <Link
              href={`/agents/${resolvedParams.id}`}
              className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
            >
              <span>←</span>
            </Link>
            <Button onClick={handleSave} size="lg" disabled={isSaving}>
              {isSaving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
