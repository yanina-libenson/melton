'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import Image from 'next/image'
import { apiClient } from '@/lib/api/client'
import { useAuth } from '@/lib/contexts/auth-context'

interface ProviderToken {
  id: string
  nameKey: string
  logo: string
  descriptionKey: string
  placeholder: string
  token: string
  isConfigured: boolean
  maskedKey: string | null
}

export default function SettingsPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const t = useTranslations('settings')
  const tCommon = useTranslations('common')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/auth')
    }
  }, [isAuthenticated, authLoading, router])

  const [providers, setProviders] = useState<ProviderToken[]>([
    {
      id: 'openai',
      nameKey: 'openaiName',
      logo: 'https://cdn.worldvectorlogo.com/logos/openai-2.svg',
      descriptionKey: 'openaiDescription',
      placeholder: 'sk-...',
      token: '',
      isConfigured: false,
      maskedKey: null,
    },
    {
      id: 'anthropic',
      nameKey: 'anthropicName',
      logo: 'https://cdn.simpleicons.org/anthropic',
      descriptionKey: 'anthropicDescription',
      placeholder: 'sk-ant-...',
      token: '',
      isConfigured: false,
      maskedKey: null,
    },
    {
      id: 'google',
      nameKey: 'googleName',
      logo: 'https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg',
      descriptionKey: 'googleDescription',
      placeholder: 'AIza...',
      token: '',
      isConfigured: false,
      maskedKey: null,
    },
  ])

  // Load API keys on mount
  useEffect(() => {
    async function loadApiKeys() {
      try {
        const apiKeys = await apiClient.getUserApiKeys()
        setProviders((prev) =>
          prev.map((p) => ({
            ...p,
            isConfigured: apiKeys[p.id as keyof typeof apiKeys].is_configured,
            maskedKey: apiKeys[p.id as keyof typeof apiKeys].masked_key,
          }))
        )
      } catch (error) {
        console.error('Failed to load API keys:', error)
        toast.error('Failed to load API keys')
      } finally {
        setIsLoading(false)
      }
    }
    loadApiKeys()
  }, [])

  function handleUpdateToken(providerId: string, token: string) {
    setProviders(providers.map((p) => (p.id === providerId ? { ...p, token } : p)))
  }

  async function handleSave() {
    setIsSaving(true)
    try {
      // Only send API keys that have been changed (non-empty)
      const updates: Record<string, string | null> = {}
      providers.forEach((p) => {
        if (p.token) {
          updates[p.id] = p.token
        }
      })

      const result = await apiClient.updateUserApiKeys(updates)

      // Update UI with new masked keys
      setProviders((prev) =>
        prev.map((p) => ({
          ...p,
          token: '', // Clear the input field
          isConfigured: result[p.id as keyof typeof result].is_configured,
          maskedKey: result[p.id as keyof typeof result].masked_key,
        }))
      )

      toast.success(t('successSaved'))
    } catch (error) {
      console.error('Failed to save API keys:', error)
      toast.error('Failed to save API keys')
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return (
      <div className="bg-background min-h-screen">
        <div className="mx-auto max-w-3xl px-8 py-16">
          <div className="py-32 text-center">
            <p className="text-muted-foreground text-sm">Loading settings...</p>
          </div>
        </div>
      </div>
    )
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
                    <div className="mb-1 flex items-center gap-2">
                      <h3 className="text-foreground text-sm font-medium">{t(provider.nameKey)}</h3>
                      {provider.isConfigured && (
                        <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-xs font-medium text-green-600">
                          Configured
                        </span>
                      )}
                    </div>
                    <p className="text-muted-foreground mb-4 text-xs">
                      {t(provider.descriptionKey)}
                    </p>

                    {provider.maskedKey && (
                      <p className="text-muted-foreground mb-2 text-xs">
                        Current: {provider.maskedKey}
                      </p>
                    )}

                    <div>
                      <Input
                        type="password"
                        placeholder={
                          provider.isConfigured
                            ? 'Enter new API key to update'
                            : provider.placeholder
                        }
                        value={provider.token}
                        onChange={(e) => handleUpdateToken(provider.id, e.target.value)}
                        disabled={isSaving}
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
          <Button onClick={handleSave} size="lg" disabled={isSaving}>
            {isSaving ? 'Saving...' : tCommon('save')}
          </Button>
        </div>
      </div>
    </div>
  )
}
