'use client'

import { use } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Input } from '@/components/ui/input'
import { PLATFORM_INTEGRATIONS } from '@/lib/platforms'
import { useState } from 'react'
import Image from 'next/image'
import { useTranslations } from 'next-intl'

export default function AddToolPage({
  params,
}: {
  params: Promise<{ id: string; locale: string }>
}) {
  const resolvedParams = use(params)
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState('')
  const t = useTranslations('toolsAdd')

  const filteredIntegrations = PLATFORM_INTEGRATIONS.filter((integration) =>
    integration.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  function handleSelectIntegration(platformId: string) {
    // Route to integration page for all tool types
    router.push(
      `/${resolvedParams.locale}/agents/${resolvedParams.id}/tools/integration/${platformId}`
    )
  }

  return (
    <div className="bg-background min-h-screen">
      <div className="mx-auto max-w-4xl px-8 py-16">
        {/* Back Button */}
        <Link
          href={`/agents/${resolvedParams.id}`}
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

        {/* Search */}
        <div className="mb-8">
          <Input
            placeholder={t('searchPlaceholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {/* Tools Grid */}
        <div className="mb-12 space-y-2">
          {filteredIntegrations.map((integration) => (
            <div
              key={integration.id}
              onClick={() => handleSelectIntegration(integration.id)}
              className="group border-border bg-card shadow-soft-xs hover:shadow-soft-md hover:border-border cursor-pointer rounded-xl border px-6 py-5 transition-all duration-200 ease-out hover:-translate-y-0.5"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <Image
                    src={integration.icon}
                    alt={integration.name}
                    width={32}
                    height={32}
                    className="h-8 w-8 object-contain"
                  />
                  <div>
                    <h3 className="text-foreground text-sm font-medium">{integration.name}</h3>
                    <p className="text-muted-foreground mt-0.5 text-xs">
                      {integration.description}
                    </p>
                  </div>
                </div>
                <span className="text-muted-foreground group-hover:text-foreground transition-colors">
                  →
                </span>
              </div>
            </div>
          ))}

          {filteredIntegrations.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-muted-foreground text-sm">{t('noToolsFound')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
