'use client'

import { useState, use, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import Image from 'next/image'
import { useTranslations } from 'next-intl'
import { apiClient } from '@/lib/api/client'
import type { Agent, IntegrationSource } from '@/lib/types'
import { PLATFORM_INTEGRATIONS } from '@/lib/platforms'

export default function EditIntegrationPage({
  params,
}: {
  params: Promise<{ id: string; integrationId: string; locale: string }>
}) {
  const resolvedParams = use(params)
  const router = useRouter()
  const t = useTranslations('toolsEdit')

  const [agent, setAgent] = useState<Agent | null>(null)
  const [integration, setIntegration] = useState<IntegrationSource | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const [enabledToolIds, setEnabledToolIds] = useState<string[]>([])

  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true)
        const agentData = await apiClient.getAgent(resolvedParams.id)
        setAgent(agentData)

        const foundIntegration = agentData.integrations.find(
          (i) => i.id === resolvedParams.integrationId
        )
        setIntegration(foundIntegration || null)

        if (foundIntegration) {
          setEnabledToolIds(
            foundIntegration.availableTools.filter((t) => t.isEnabled !== false).map((t) => t.id)
          )
        }
      } catch (error) {
        console.error('Failed to load agent:', error)
        toast.error('Failed to load integration')
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [resolvedParams.id, resolvedParams.integrationId])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="font-light text-gray-400">Loading...</p>
      </div>
    )
  }

  if (!agent || !integration) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="font-light text-gray-400">{t('integrationNotFound')}</p>
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
      toast.error(t('errorAtLeastOneTool'))
      return
    }

    toast.success(t('successUpdated'))
    router.push(`/agents/${resolvedParams.id}`)
  }

  async function handleRemove() {
    if (integration && confirm(t('confirmRemove', { name: integration.name }))) {
      try {
        await apiClient.deleteIntegration(integration.id)
        toast.success(t('successRemoved'))
        router.push(`/${resolvedParams.locale}/agents/${resolvedParams.id}`)
      } catch (error) {
        console.error('Failed to delete integration:', error)
        toast.error('Failed to remove integration')
      }
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
            <Image
              src={
                integration.icon ||
                (integration.type === 'custom-tool'
                  ? 'https://api.iconify.design/lucide/wrench.svg?color=%23888888'
                  : integration.platformId
                    ? PLATFORM_INTEGRATIONS.find((p) => p.id === integration.platformId)?.icon ||
                      'https://api.iconify.design/lucide/box.svg?color=%23888888'
                    : 'https://api.iconify.design/lucide/box.svg?color=%23888888')
              }
              alt={integration.name}
              width={48}
              height={48}
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
            <Label className="text-foreground mb-2 block text-sm font-medium">
              {t('selectToolsLabel')}
            </Label>
            <p className="text-muted-foreground text-xs">
              {t('toolsSelectedCount', {
                count: enabledToolIds.length,
                total: integration.availableTools.length,
              })}
            </p>
          </div>

          <div className="space-y-2">
            {integration.availableTools.map((tool) => (
              <div
                key={tool.id}
                className={`rounded-xl border px-5 py-4 transition-all duration-200 ease-out ${
                  enabledToolIds.includes(tool.id)
                    ? 'border-primary bg-primary/5 shadow-soft-sm'
                    : 'border-border bg-card shadow-soft-xs'
                }`}
              >
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={enabledToolIds.includes(tool.id)}
                    onChange={() => handleToggleTool(tool.id)}
                    className="mt-0.5 h-4 w-4"
                  />
                  <div className="flex-1">
                    <p className="text-foreground text-sm font-medium">{tool.name}</p>
                    <p className="text-muted-foreground mt-1 text-xs">{tool.description}</p>
                  </div>
                  <Link
                    href={`/agents/${resolvedParams.id}/tools/edit/${tool.id}`}
                    onClick={(e) => e.stopPropagation()}
                    className="text-muted-foreground hover:text-foreground text-sm transition-colors"
                  >
                    Configure →
                  </Link>
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
              {t('remove')}
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
              {t('save')}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
