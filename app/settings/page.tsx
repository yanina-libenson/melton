'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'

interface ProviderToken {
  id: string
  name: string
  logo: string
  description: string
  placeholder: string
  token: string
}

export default function SettingsPage() {
  const [providers, setProviders] = useState<ProviderToken[]>([
    {
      id: 'openai',
      name: 'OpenAI',
      logo: 'https://cdn.worldvectorlogo.com/logos/openai-2.svg',
      description: 'GPT-4, GPT-3.5, and other OpenAI models',
      placeholder: 'sk-...',
      token: '',
    },
    {
      id: 'anthropic',
      name: 'Anthropic',
      logo: 'https://cdn.simpleicons.org/anthropic',
      description: 'Claude Opus, Claude Sonnet models',
      placeholder: 'sk-ant-...',
      token: '',
    },
    {
      id: 'google',
      name: 'Google AI',
      logo: 'https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg',
      description: 'Gemini and other Google models',
      placeholder: 'AIza...',
      token: '',
    },
  ])

  function handleUpdateToken(providerId: string, token: string) {
    setProviders(providers.map((p) => (p.id === providerId ? { ...p, token } : p)))
  }

  function handleSave() {
    // Mock save - in production this would save to backend
    toast.success('Settings saved')
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
        <div className="mb-12">
          <h1 className="text-foreground mb-2 text-4xl font-semibold tracking-tight">Settings</h1>
          <p className="text-muted-foreground text-sm">Configure your AI provider tokens</p>
        </div>

        {/* Provider Tokens */}
        <div className="mb-12">
          <Label className="text-foreground mb-4 block text-sm font-medium">
            AI Provider API Keys
          </Label>
          <p className="text-muted-foreground mb-6 text-sm">
            Add your API keys to enable AI models in your agents
          </p>

          <div className="space-y-4">
            {providers.map((provider) => (
              <div
                key={provider.id}
                className="border-border bg-card shadow-soft-xs rounded-xl border p-6"
              >
                <div className="flex items-start gap-4">
                  <img
                    src={provider.logo}
                    alt={provider.name}
                    className="h-10 w-10 rounded-lg object-contain"
                  />
                  <div className="flex-1">
                    <h3 className="text-foreground mb-1 text-sm font-medium">{provider.name}</h3>
                    <p className="text-muted-foreground mb-4 text-xs">{provider.description}</p>

                    <div>
                      <Input
                        type="password"
                        placeholder={provider.placeholder}
                        value={provider.token}
                        onChange={(e) => handleUpdateToken(provider.id, e.target.value)}
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="border-border flex items-center justify-between border-t pt-8">
          <Link
            href="/agents"
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
  )
}
