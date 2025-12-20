'use client'

import { useState, use } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent } from '@/components/ui/tabs'
import { mockAgents } from '@/lib/mock-data'
import { Agent } from '@/lib/types'
import { toast } from 'sonner'

export default function DeployPage({ params }: { params: Promise<{ id: string }> }) {
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
        <p className="text-muted-foreground font-light">Agent not found</p>
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
    toast.success('Embed code copied to clipboard')
    setTimeout(() => setEmbedCopied(false), 2000)
  }

  function connectWhatsApp() {
    if (!whatsappNumber.trim()) {
      toast.error('Please enter a WhatsApp Business number')
      return
    }
    toast.success('WhatsApp connected successfully')
  }

  function connectEmail() {
    if (!emailAddress.trim()) {
      toast.error('Please enter an email address')
      return
    }
    toast.success('Email integration configured successfully')
  }

  function activateAgent() {
    toast.success('Agent activated')
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
            Connect {agent.name}
          </h1>
          <p className="text-muted-foreground text-sm">
            Choose how customers will reach your agent
          </p>
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
              <p className="text-foreground text-sm font-medium">Live Chat</p>
            </button>
            <button
              onClick={() => setActiveTab('whatsapp')}
              className={`cursor-pointer rounded-xl border px-5 py-4 transition-all duration-200 ease-out ${
                activeTab === 'whatsapp'
                  ? 'border-primary bg-primary/5 shadow-soft-sm'
                  : 'border-border bg-card shadow-soft-xs hover:shadow-soft-sm hover:border-border'
              }`}
            >
              <p className="text-foreground text-sm font-medium">WhatsApp</p>
            </button>
            <button
              onClick={() => setActiveTab('email')}
              className={`cursor-pointer rounded-xl border px-5 py-4 transition-all duration-200 ease-out ${
                activeTab === 'email'
                  ? 'border-primary bg-primary/5 shadow-soft-sm'
                  : 'border-border bg-card shadow-soft-xs hover:shadow-soft-sm hover:border-border'
              }`}
            >
              <p className="text-foreground text-sm font-medium">Email</p>
            </button>
          </div>

          <Tabs
            value={activeTab}
            onValueChange={(v) => setActiveTab(v as 'live-chat' | 'whatsapp' | 'email')}
          >
            {/* Live Chat Tab */}
            <TabsContent value="live-chat" className="space-y-12">
              <div>
                <Label className="text-foreground mb-3 block text-sm font-medium">Embed Code</Label>
                <p className="text-muted-foreground mb-6 text-xs">
                  Add this code to your website before the closing &lt;/body&gt; tag
                </p>
                <div className="bg-card border-border shadow-soft-xs rounded-xl border p-6">
                  <pre className="text-foreground overflow-x-auto font-mono text-xs">
                    <code>{embedCode}</code>
                  </pre>
                </div>
                <div className="mt-8">
                  <Button onClick={copyEmbedCode} size="lg" className="px-8">
                    {embedCopied ? 'Copied' : 'Copy Code'}
                  </Button>
                </div>
              </div>
            </TabsContent>

            {/* WhatsApp Tab */}
            <TabsContent value="whatsapp" className="space-y-12">
              <div>
                <Label className="text-foreground mb-3 block text-sm font-medium">
                  WhatsApp Business Number
                </Label>
                <p className="text-muted-foreground mb-6 text-xs">
                  Enter your WhatsApp Business phone number with country code
                </p>
                <Input
                  placeholder="+54 9 11 1234-5678"
                  value={whatsappNumber}
                  onChange={(e) => setWhatsappNumber(e.target.value)}
                  className="mb-8"
                />
                <Button onClick={connectWhatsApp} size="lg" className="px-8">
                  Connect WhatsApp
                </Button>
              </div>
            </TabsContent>

            {/* Email Tab */}
            <TabsContent value="email" className="space-y-12">
              <div>
                <Label className="text-foreground mb-3 block text-sm font-medium">
                  Support Email Address
                </Label>
                <p className="text-muted-foreground mb-6 text-xs">
                  Emails sent to this address will be handled by your agent
                </p>
                <Input
                  type="email"
                  placeholder="support@yourcompany.com"
                  value={emailAddress}
                  onChange={(e) => setEmailAddress(e.target.value)}
                  className="mb-8"
                />
                <Button onClick={connectEmail} size="lg" className="px-8">
                  Connect Email
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
              Launch Agent
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
