'use client'

import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { useAgents } from '@/lib/hooks/useAgents'

export default function AgentsPage() {
  const { agents, isLoading, isError } = useAgents()
  const t = useTranslations('agents')
  const tDates = useTranslations('dates')

  function formatDate(dateString: string): string {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))

    if (diffInHours < 1) return tDates('justNow')
    if (diffInHours < 24) return tDates('hoursAgo', { hours: diffInHours })
    if (diffInHours < 48) return tDates('yesterday')

    const diffInDays = Math.floor(diffInHours / 24)
    if (diffInDays < 7) return tDates('daysAgo', { days: diffInDays })

    return date.toLocaleDateString()
  }

  return (
    <div className="bg-background min-h-screen">
      <div className="mx-auto max-w-4xl px-8 py-16">
        {/* Header */}
        <div className="mb-12 flex items-center justify-between">
          <div>
            <h1 className="text-foreground mb-2 text-4xl font-semibold tracking-tight">
              {t('title')}
            </h1>
            <p className="text-muted-foreground text-sm">
              {t('count', { count: agents?.length || 0 })}
            </p>
          </div>
          <Link href="/agents/new">
            <Button size="lg">{t('newAgent')}</Button>
          </Link>
        </div>

        {/* Agents List */}
        {isLoading ? (
          <div className="py-32 text-center">
            <p className="text-muted-foreground text-sm">{t('loading') || 'Loading...'}</p>
          </div>
        ) : isError ? (
          <div className="py-32 text-center">
            <p className="mb-4 text-sm text-red-500">
              {t('errorLoading') || 'Error loading agents'}
            </p>
            <Button onClick={() => window.location.reload()}>{t('retry') || 'Retry'}</Button>
          </div>
        ) : !agents || agents.length === 0 ? (
          <div className="py-32 text-center">
            <p className="mb-8 text-lg font-light text-gray-400">{t('noAgentsYet')}</p>
            <Link href="/agents/new">
              <Button>{t('createFirstAgent')}</Button>
            </Link>
          </div>
        ) : (
          <div className="space-y-1">
            {agents.map((agent) => {
              const totalTools =
                agent.integrations?.reduce(
                  (sum, integration) => sum + integration.enabledToolIds.length,
                  0
                ) || 0

              return (
                <Link key={agent.id} href={`/agents/${agent.id}`} className="group block">
                  <div className="border-border/50 bg-card shadow-soft-xs hover:shadow-soft-md hover:border-border cursor-pointer rounded-xl border px-6 py-6 transition-all duration-200 ease-out hover:-translate-y-0.5">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="text-foreground group-hover:text-primary text-base font-medium transition-colors">
                            {agent.name}
                          </h2>
                          {agent.status === 'active' && (
                            <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-xs font-medium text-green-600">
                              {t('active')}
                            </span>
                          )}
                        </div>
                        <div className="mt-2 flex items-center gap-3">
                          <p className="text-muted-foreground text-xs">
                            {t('toolCount', { count: totalTools })}
                          </p>
                          <span className="text-border">·</span>
                          <p className="text-muted-foreground text-xs" suppressHydrationWarning>
                            {formatDate(agent.updatedAt)}
                          </p>
                        </div>
                      </div>
                      <span className="text-muted-foreground group-hover:text-foreground transition-colors">
                        →
                      </span>
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
