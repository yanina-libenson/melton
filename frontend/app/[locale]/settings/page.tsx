'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import Image from 'next/image'

interface ProviderToken {
  id: string
  nameKey: string
  logo: string
  descriptionKey: string
  placeholder: string
  token: string
}

export default function SettingsPage() {
  const t = useTranslations('settings')
  const tCommon = useTranslations('common')

  const [providers, setProviders] = useState<ProviderToken[]>([
    {
      id: 'openai',
      nameKey: 'openaiName',
      logo: 'https://cdn.worldvectorlogo.com/logos/openai-2.svg',
      descriptionKey: 'openaiDescription',
      placeholder: 'sk-...',
      token: '',
    },
    {
      id: 'anthropic',
      nameKey: 'anthropicName',
      logo: 'https://cdn.simpleicons.org/anthropic',
      descriptionKey: 'anthropicDescription',
      placeholder: 'sk-ant-...',
      token: '',
    },
    {
      id: 'google',
      nameKey: 'googleName',
      logo: 'https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg',
      descriptionKey: 'googleDescription',
      placeholder: 'AIza...',
      token: '',
    },
  ])

  function handleUpdateToken(providerId: string, token: string) {
    setProviders(providers.map((p) => (p.id === providerId ? { ...p, token } : p)))
  }

  function handleSave() {
    // Mock save - in production this would save to backend
    toast.success(t('successSaved'))
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
          <h1 className="text-foreground mb-2 text-4xl font-semibold tracking-tight">
            {t('title')}
          </h1>
          <p className="text-muted-foreground text-sm">{t('subtitle')}</p>
        </div>

        {/* Provider Tokens */}
        <div className="mb-12">
          <Label className="text-foreground mb-4 block text-sm font-medium">
            {t('apiKeysLabel')}
          </Label>
          <p className="text-muted-foreground mb-6 text-sm">{t('apiKeysDescription')}</p>

          <div className="space-y-4">
            {providers.map((provider) => (
              <div
                key={provider.id}
                className="border-border bg-card shadow-soft-xs rounded-xl border p-6"
              >
                <div className="flex items-start gap-4">
                  <Image
                    src={provider.logo}
                    alt={t(provider.nameKey)}
                    width={40}
                    height={40}
                    className="h-10 w-10 rounded-lg object-contain"
                  />
                  <div className="flex-1">
                    <h3 className="text-foreground mb-1 text-sm font-medium">
                      {t(provider.nameKey)}
                    </h3>
                    <p className="text-muted-foreground mb-4 text-xs">
                      {t(provider.descriptionKey)}
                    </p>

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
            {tCommon('save')}
          </Button>
        </div>
      </div>
    </div>
  )
}
