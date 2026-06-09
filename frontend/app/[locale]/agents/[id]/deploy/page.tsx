'use client'

import { useState, use, useEffect } from 'react'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAgent } from '@/lib/hooks/useAgents'
import { apiClient } from '@/lib/api/client'
import type { DeploymentChannel } from '@/lib/types'
import { toast } from 'sonner'

// The channels an agent can be deployed to. "Web" = embeddable live-chat widget.
const CHANNELS: { id: DeploymentChannel; label: string }[] = [
  { id: 'web', label: 'Web' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'email', label: 'Email' },
  { id: 'mobile', label: 'Mobile' },
  { id: 'apple_watch', label: 'Apple Watch' },
]

export default function DeployPage({ params }: { params: Promise<{ id: string }> }) {
  const t = useTranslations('deploy')
  const resolvedParams = use(params)
  const { agent, isLoading, mutate } = useAgent(resolvedParams.id)

  const [embedCopied, setEmbedCopied] = useState(false)
  const [whatsappNumber, setWhatsappNumber] = useState('')
  const [emailAddress, setEmailAddress] = useState('')
  const [deployedChannels, setDeployedChannels] = useState<Set<string>>(new Set())
  const [togglingChannel, setTogglingChannel] = useState<string | null>(null)

  // Load which channels the agent is currently deployed to.
  useEffect(() => {
    let active = true
    apiClient
      .listDeployments(resolvedParams.id)
      .then((deps) => {
        if (active) {
          setDeployedChannels(new Set(deps.filter((d) => d.isActive).map((d) => d.channelType)))
        }
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [resolvedParams.id])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-muted-foreground font-light">…</p>
      </div>
    )
  }

  if (!agent) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-muted-foreground font-light">{t('agentNotFound')}</p>
      </div>
    )
  }

  const embedCode = `<!-- Dr. Melton Widget -->
<script src="https://cdn.melton.app/widget.js"></script>
<script>
  Melton.init({
    agentId: '${agent.id}',
    position: 'bottom-right'
  });
</script>`

  function copyEmbedCode() {
    navigator.clipboard.writeText(embedCode)
    setEmbedCopied(true)
    toast.success(t('successEmbedCopied'))
    setTimeout(() => setEmbedCopied(false), 2000)
  }

  function connectWhatsApp() {
    if (!whatsappNumber.trim()) {
      toast.error(t('errorWhatsappRequired'))
      return
    }
    toast.success(t('successWhatsappConnected'))
  }

  function connectEmail() {
    if (!emailAddress.trim()) {
      toast.error(t('errorEmailRequired'))
      return
    }
    toast.success(t('successEmailConnected'))
  }

  async function toggleChannel(channel: DeploymentChannel) {
    const isOn = deployedChannels.has(channel)
    setTogglingChannel(channel)
    try {
      if (isOn) {
        await apiClient.undeployFromChannel(resolvedParams.id, channel)
        setDeployedChannels((prev) => {
          const next = new Set(prev)
          next.delete(channel)
          return next
        })
      } else {
        await apiClient.deployToChannel(resolvedParams.id, channel)
        setDeployedChannels((prev) => new Set(prev).add(channel))
      }
      mutate() // refresh derived is_active badge
    } catch {
      toast.error(t('channelError'))
    } finally {
      setTogglingChannel(null)
    }
  }

  // Channel-specific config, shown inline inside a channel only when it's on.
  function renderChannelConfig(channelId: DeploymentChannel) {
    if (channelId === 'web') {
      return (
        <div className="border-border mt-4 border-t pt-4">
          <Label className="text-foreground mb-2 block text-sm font-medium">
            {t('embedCodeLabel')}
          </Label>
          <p className="text-muted-foreground mb-4 text-xs">{t('embedCodeDescription')}</p>
          <div className="bg-background border-border rounded-lg border p-4">
            <pre className="text-foreground overflow-x-auto font-mono text-xs">
              <code>{embedCode}</code>
            </pre>
          </div>
          <Button onClick={copyEmbedCode} size="sm" className="mt-4">
            {embedCopied ? t('copied') : t('copyCode')}
          </Button>
        </div>
      )
    }
    if (channelId === 'whatsapp') {
      return (
        <div className="border-border mt-4 border-t pt-4">
          <Label className="text-foreground mb-2 block text-sm font-medium">
            {t('whatsappNumberLabel')}
          </Label>
          <p className="text-muted-foreground mb-4 text-xs">{t('whatsappNumberDescription')}</p>
          <Input
            placeholder={t('whatsappNumberPlaceholder')}
            value={whatsappNumber}
            onChange={(e) => setWhatsappNumber(e.target.value)}
            className="mb-4"
          />
          <Button onClick={connectWhatsApp} size="sm">
            {t('connectWhatsapp')}
          </Button>
        </div>
      )
    }
    if (channelId === 'email') {
      return (
        <div className="border-border mt-4 border-t pt-4">
          <Label className="text-foreground mb-2 block text-sm font-medium">
            {t('emailLabel')}
          </Label>
          <p className="text-muted-foreground mb-4 text-xs">{t('emailDescription')}</p>
          <Input
            type="email"
            placeholder={t('emailPlaceholder')}
            value={emailAddress}
            onChange={(e) => setEmailAddress(e.target.value)}
            className="mb-4"
          />
          <Button onClick={connectEmail} size="sm">
            {t('connectEmail')}
          </Button>
        </div>
      )
    }
    if (channelId === 'mobile') {
      return (
        <p className="border-border text-muted-foreground mt-4 border-t pt-4 text-xs">
          {t('mobileHint')}
        </p>
      )
    }
    if (channelId === 'apple_watch') {
      return (
        <p className="border-border text-muted-foreground mt-4 border-t pt-4 text-xs">
          {t('watchHint')}
        </p>
      )
    }
    return null
  }

  return (
    <div className="bg-background min-h-screen">
      <div className="mx-auto max-w-4xl px-8 py-16">
        {/* Back Button */}
        <Link
          href={`/agents/${agent.id}`}
          className="text-muted-foreground hover:text-foreground mb-8 inline-flex items-center gap-1 transition-colors"
        >
          <span>←</span>
        </Link>

        {/* Header */}
        <div className="mb-12">
          <h1 className="text-foreground mb-2 text-4xl font-semibold tracking-tight">
            {t('title', { agentName: agent.name })}
          </h1>
          <p className="text-muted-foreground text-sm">{t('subtitle')}</p>
        </div>

        {/* Channels — toggle per channel; channel-specific config shows inline
            when the channel is on. The agent is "active" when deployed to ≥1. */}
        <div className="mb-12">
          <p className="text-foreground text-sm font-medium">{t('channelsTitle')}</p>
          <p className="text-muted-foreground mt-0.5 mb-6 text-xs">{t('channelsSubtitle')}</p>
          <div className="space-y-3">
            {CHANNELS.map((channel) => {
              const isOn = deployedChannels.has(channel.id)
              return (
                <div
                  key={channel.id}
                  className="border-border bg-card shadow-soft-xs rounded-xl border px-5 py-4"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-foreground text-sm font-medium">{channel.label}</span>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={isOn}
                      aria-label={channel.label}
                      disabled={togglingChannel === channel.id}
                      onClick={() => toggleChannel(channel.id)}
                      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${
                        isOn ? 'bg-green-500' : 'bg-muted-foreground/30'
                      }`}
                    >
                      <span
                        className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                          isOn ? 'translate-x-5' : 'translate-x-0.5'
                        }`}
                      />
                    </button>
                  </div>
                  {isOn && renderChannelConfig(channel.id)}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
