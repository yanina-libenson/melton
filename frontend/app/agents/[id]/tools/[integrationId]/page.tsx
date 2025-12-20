'use client'

import { useState, use } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { mockAgents } from '@/lib/mock-data'
import { toast } from 'sonner'

export default function EditIntegrationPage({
  params,
}: {
  params: Promise<{ id: string; integrationId: string }>
}) {
  const resolvedParams = use(params)
  const router = useRouter()

  const agent = mockAgents.find((a) => a.id === resolvedParams.id)
  const integration = agent?.integrations.find((i) => i.id === resolvedParams.integrationId)

  const [enabledToolIds, setEnabledToolIds] = useState<string[]>(integration?.enabledToolIds || [])

  if (!agent || !integration) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="font-light text-gray-400">Integration not found</p>
      </div>
    )
  }

  function handleToggleTool(toolId: string) {
    setEnabledToolIds((prev) =>
      prev.includes(toolId) ? prev.filter((id) => id !== toolId) : [...prev, toolId]
    )
  }

  function handleSave() {
    if (enabledToolIds.length === 0) {
      toast.error('Please enable at least one tool')
      return
    }

    toast.success('Integration updated')
    router.push(`/agents/${resolvedParams.id}`)
  }

  function handleRemove() {
    if (integration && confirm(`Remove ${integration.name}?`)) {
      toast.success('Integration removed')
      router.push(`/agents/${resolvedParams.id}`)
    }
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
          <div className="flex items-start gap-4">
            <img
              src={
                integration.icon ||
                (integration.type === 'custom-tool'
                  ? 'https://api.iconify.design/lucide/wrench.svg?color=%23888888'
                  : '')
              }
              alt={integration.name}
              className="h-12 w-12 object-contain"
            />
            <div>
              <h1 className="text-foreground mb-1 text-3xl font-semibold tracking-tight">
                {integration.name}
              </h1>
              <p className="text-muted-foreground text-sm">{integration.description}</p>
            </div>
          </div>
        </div>

        {/* Tools Selection */}
        <div className="mb-12">
          <div className="mb-6">
            <Label className="text-foreground mb-2 block text-sm font-medium">Select Tools</Label>
            <p className="text-muted-foreground text-xs">
              {enabledToolIds.length} of {integration.availableTools.length} selected
            </p>
          </div>

          <div className="space-y-2">
            {integration.availableTools.map((tool) => (
              <div
                key={tool.id}
                onClick={() => handleToggleTool(tool.id)}
                className={`cursor-pointer rounded-xl border px-5 py-4 transition-all duration-200 ease-out ${
                  enabledToolIds.includes(tool.id)
                    ? 'border-primary bg-primary/5 shadow-soft-sm'
                    : 'border-border bg-card shadow-soft-xs hover:shadow-soft-sm hover:border-border'
                }`}
              >
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={enabledToolIds.includes(tool.id)}
                    onChange={() => {}}
                    className="mt-0.5 h-4 w-4"
                  />
                  <div className="flex-1">
                    <p className="text-foreground text-sm font-medium">{tool.name}</p>
                    <p className="text-muted-foreground mt-1 text-xs">{tool.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="border-border border-t pt-8">
          <div className="mb-6 flex items-center justify-between">
            <button
              onClick={handleRemove}
              className="text-muted-foreground hover:text-destructive text-sm transition-colors"
            >
              Remove
            </button>
          </div>
          <div className="flex items-center justify-between">
            <Link
              href={`/agents/${resolvedParams.id}`}
              className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
            >
              <span>←</span>
            </Link>
            <Button onClick={handleSave} size="lg">
              Save
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
