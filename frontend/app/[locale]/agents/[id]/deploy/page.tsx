'use client'

import { useState, use } from 'react'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent } from '@/components/ui/tabs'
import { mockAgents } from '@/lib/mock-data'
import { Agent } from '@/lib/types'
import { toast } from 'sonner'

export default function DeployPage({ params }: { params: Promise<{ id: string }> }) {
  const t = useTranslations('deploy')
  const resolvedParams = use(params)
  const [agent] = useState<Agent | null>(() => {
    return mockAgents.find((a) => a.id === resolvedParams.id) || null
  })

  const [activeTab, setActiveTab] = useState<'live-chat' | 'whatsapp' | 'email'>('live-chat')
  const [embedCopied, setEmbedCopied] = useState(false)
  const [whatsappNumber, setWhatsappNumber] = useState('')
  const [emailAddress, setEmailAddress] = useState('')

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

  function activateAgent() {
    toast.success(t('successAgentActivated'))
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

        {/* Channel Selection */}
        <div className="mb-12">
          <div className="mb-8 grid grid-cols-3 gap-3">
            <button
              onClick={() => setActiveTab('live-chat')}
              className={`cursor-pointer rounded-xl border px-5 py-4 transition-all duration-200 ease-out ${
                activeTab === 'live-chat'
                  ? 'border-primary bg-primary/5 shadow-soft-sm'
                  : 'border-border bg-card shadow-soft-xs hover:shadow-soft-sm hover:border-border'
              }`}
            >
              <p className="text-foreground text-sm font-medium">{t('liveChat')}</p>
            </button>
            <button
              onClick={() => setActiveTab('whatsapp')}
              className={`cursor-pointer rounded-xl border px-5 py-4 transition-all duration-200 ease-out ${
                activeTab === 'whatsapp'
                  ? 'border-primary bg-primary/5 shadow-soft-sm'
                  : 'border-border bg-card shadow-soft-xs hover:shadow-soft-sm hover:border-border'
              }`}
            >
              <p className="text-foreground text-sm font-medium">{t('whatsapp')}</p>
            </button>
            <button
              onClick={() => setActiveTab('email')}
              className={`cursor-pointer rounded-xl border px-5 py-4 transition-all duration-200 ease-out ${
                activeTab === 'email'
                  ? 'border-primary bg-primary/5 shadow-soft-sm'
                  : 'border-border bg-card shadow-soft-xs hover:shadow-soft-sm hover:border-border'
              }`}
            >
              <p className="text-foreground text-sm font-medium">{t('email')}</p>
            </button>
          </div>

          <Tabs
            value={activeTab}
            onValueChange={(v) => setActiveTab(v as 'live-chat' | 'whatsapp' | 'email')}
          >
            {/* Live Chat Tab */}
            <TabsContent value="live-chat" className="space-y-12">
              <div>
                <Label className="text-foreground mb-3 block text-sm font-medium">
                  {t('embedCodeLabel')}
                </Label>
                <p className="text-muted-foreground mb-6 text-xs">{t('embedCodeDescription')}</p>
                <div className="bg-card border-border shadow-soft-xs rounded-xl border p-6">
                  <pre className="text-foreground overflow-x-auto font-mono text-xs">
                    <code>{embedCode}</code>
                  </pre>
                </div>
                <div className="mt-8">
                  <Button onClick={copyEmbedCode} size="lg" className="px-8">
                    {embedCopied ? t('copied') : t('copyCode')}
                  </Button>
                </div>
              </div>
            </TabsContent>

            {/* WhatsApp Tab */}
            <TabsContent value="whatsapp" className="space-y-12">
              <div>
                <Label className="text-foreground mb-3 block text-sm font-medium">
                  {t('whatsappNumberLabel')}
                </Label>
                <p className="text-muted-foreground mb-6 text-xs">
                  {t('whatsappNumberDescription')}
                </p>
                <Input
                  placeholder={t('whatsappNumberPlaceholder')}
                  value={whatsappNumber}
                  onChange={(e) => setWhatsappNumber(e.target.value)}
                  className="mb-8"
                />
                <Button onClick={connectWhatsApp} size="lg" className="px-8">
                  {t('connectWhatsapp')}
                </Button>
              </div>
            </TabsContent>

            {/* Email Tab */}
            <TabsContent value="email" className="space-y-12">
              <div>
                <Label className="text-foreground mb-3 block text-sm font-medium">
                  {t('emailLabel')}
                </Label>
                <p className="text-muted-foreground mb-6 text-xs">{t('emailDescription')}</p>
                <Input
                  type="email"
                  placeholder={t('emailPlaceholder')}
                  value={emailAddress}
                  onChange={(e) => setEmailAddress(e.target.value)}
                  className="mb-8"
                />
                <Button onClick={connectEmail} size="lg" className="px-8">
                  {t('connectEmail')}
                </Button>
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Actions */}
        {agent.status !== 'active' && (
          <div className="border-border flex items-center justify-between border-t pt-8">
            <Link
              href={`/agents/${agent.id}`}
              className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
            >
              <span>←</span>
            </Link>
            <Button onClick={activateAgent} size="lg" className="px-8">
              {t('launchAgent')}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
