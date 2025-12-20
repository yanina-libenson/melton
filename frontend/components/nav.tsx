'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { mockAgents } from '@/lib/mock-data'
import { PLATFORM_INTEGRATIONS } from '@/lib/platforms'

export function Nav() {
  const pathname = usePathname()

  // Parse breadcrumbs from pathname
  const getBreadcrumbs = () => {
    const crumbs: { label: string; href: string }[] = []

    // Always start with Agents
    crumbs.push({ label: 'Agents', href: '/agents' })

    // Settings page
    if (pathname === '/settings') {
      crumbs.push({ label: 'Settings', href: '/settings' })
      return crumbs
    }

    if (pathname === '/agents') {
      return crumbs
    }

    // Parse agent routes
    const agentMatch = pathname.match(/^\/agents\/([^\/]+)/)
    if (agentMatch) {
      const agentId = agentMatch[1]

      if (agentId === 'new') {
        crumbs.push({ label: 'New Agent', href: '/agents/new' })
      } else {
        const agent = mockAgents.find((a) => a.id === agentId)
        const agentName = agent?.name || 'Agent'
        crumbs.push({ label: agentName, href: `/agents/${agentId}` })

        // Parse tool routes
        if (pathname.includes('/tools/add')) {
          crumbs.push({ label: 'Add Tool', href: `/agents/${agentId}/tools/add` })
        } else if (pathname.includes('/tools/integration/')) {
          const platformMatch = pathname.match(/\/tools\/integration\/([^\/]+)/)
          if (platformMatch) {
            const platformId = platformMatch[1]
            const platform = PLATFORM_INTEGRATIONS.find((p) => p.id === platformId)
            crumbs.push({ label: 'Add Tool', href: `/agents/${agentId}/tools/add` })
            crumbs.push({ label: platform?.name || 'Tool', href: pathname })
          }
        } else if (pathname.includes('/deploy')) {
          crumbs.push({ label: 'Connect', href: `/agents/${agentId}/deploy` })
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
              <span className="font-signature text-2xl font-bold">Dr. Melton</span>
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

          <Link
            href="/settings"
            className="text-muted-foreground hover:text-foreground text-sm transition-colors"
          >
            Settings
          </Link>
        </div>
      </div>
    </nav>
  )
}
