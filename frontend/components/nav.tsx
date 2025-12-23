'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { PLATFORM_INTEGRATIONS } from '@/lib/platforms'
import { LanguageSwitcher } from './language-switcher'
import { useAgent } from '@/lib/hooks/useAgents'

export function Nav() {
  const pathname = usePathname()
  const t = useTranslations('nav')

  // Remove locale prefix from pathname for matching
  const pathWithoutLocale = pathname.replace(/^\/(en|es-AR)/, '') || '/'

  // Extract agent ID from URL for fetching agent data
  const agentMatch = pathWithoutLocale.match(/^\/agents\/([^\/]+)/)
  const agentId = agentMatch?.[1] !== 'new' ? agentMatch?.[1] || null : null

  // Fetch agent data if we have an agent ID
  const { agent } = useAgent(agentId || null)

  // Parse breadcrumbs from pathname
  const getBreadcrumbs = () => {
    const crumbs: { label: string; href: string }[] = []

    // Always start with Agents
    crumbs.push({ label: t('agents'), href: '/agents' })

    // Settings page
    if (pathWithoutLocale === '/settings') {
      crumbs.push({ label: t('settings'), href: '/settings' })
      return crumbs
    }

    if (pathWithoutLocale === '/agents' || pathWithoutLocale === '/') {
      return crumbs
    }

    // Parse agent routes
    if (agentMatch) {
      const agentIdFromMatch = agentMatch[1]

      if (agentIdFromMatch === 'new') {
        crumbs.push({ label: t('newAgent'), href: '/agents/new' })
      } else {
        const agentName = agent?.name || t('agents')
        crumbs.push({ label: agentName, href: `/agents/${agentIdFromMatch}` })

        // Parse tool routes
        if (pathWithoutLocale.includes('/tools/add')) {
          crumbs.push({ label: t('addTool'), href: `/agents/${agentIdFromMatch}/tools/add` })
        } else if (pathWithoutLocale.includes('/tools/integration/')) {
          const platformMatch = pathWithoutLocale.match(/\/tools\/integration\/([^\/]+)/)
          if (platformMatch) {
            const platformId = platformMatch[1]
            const platform = PLATFORM_INTEGRATIONS.find((p) => p.id === platformId)
            crumbs.push({ label: t('addTool'), href: `/agents/${agentIdFromMatch}/tools/add` })
            crumbs.push({ label: platform?.name || t('addTool'), href: pathname })
          }
        } else if (pathWithoutLocale.includes('/deploy')) {
          crumbs.push({ label: t('connect'), href: `/agents/${agentIdFromMatch}/deploy` })
        }
      }
    }

    return crumbs
  }

  const breadcrumbs = getBreadcrumbs()

  return (
    <nav className="bg-background/80 border-border fixed top-0 right-0 left-0 z-50 border-b backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-8">
        <div className="flex h-14 items-center justify-between">
          <div className="flex items-center gap-8">
            {/* Logo */}
            <Link
              href="/agents"
              className="text-foreground hover:text-foreground/90 transition-colors"
            >
              <span className="font-signature text-2xl font-bold">{t('logo')}</span>
            </Link>

            {/* Breadcrumbs */}
            <div className="flex items-center gap-2">
              {breadcrumbs.map((crumb, index) => (
                <div key={crumb.href} className="flex items-center gap-2">
                  <Link
                    href={crumb.href}
                    className={`text-sm transition-colors ${
                      index === breadcrumbs.length - 1
                        ? 'text-foreground font-medium'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {crumb.label}
                  </Link>
                  {index < breadcrumbs.length - 1 && (
                    <span className="text-muted-foreground">›</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex min-w-[200px] items-center justify-end gap-4">
            <LanguageSwitcher />
            <Link
              href="/conversations"
              className="text-muted-foreground hover:text-foreground text-sm whitespace-nowrap transition-colors"
            >
              Conversations
            </Link>
            <Link
              href="/settings"
              className="text-muted-foreground hover:text-foreground text-sm whitespace-nowrap transition-colors"
            >
              {t('settings')}
            </Link>
          </div>
        </div>
      </div>
    </nav>
  )
}
