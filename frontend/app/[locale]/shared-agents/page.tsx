'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import { apiClient } from '@/lib/api/client'
import useSWR from 'swr'
import type { Agent } from '@/lib/types'
import { useAuth } from '@/lib/contexts/auth-context'

export default function SharedAgentsPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const [shareCode, setShareCode] = useState('')
  const [isAccepting, setIsAccepting] = useState(false)

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/auth')
    }
  }, [isAuthenticated, authLoading, router])

  // Fetch shared agents
  const {
    data: sharedAgents,
    error,
    mutate,
  } = useSWR<Agent[]>('/shared/agents', () => apiClient.listSharedAgents())

  const handleAcceptShareCode = async () => {
    if (!shareCode.trim()) {
      toast.error('Please enter a share code')
      return
    }

    setIsAccepting(true)
    try {
      const result = await apiClient.acceptShareCode(shareCode.trim())
      toast.success(result.message)
      setShareCode('')
      mutate() // Refresh the list
    } catch (error: unknown) {
      const message =
        (error as { data?: { detail?: string } })?.data?.detail || 'Invalid or expired share code'
      toast.error(message)
    } finally {
      setIsAccepting(false)
    }
  }

  return (
    <div className="bg-background min-h-screen">
      <div className="mx-auto max-w-5xl px-8 py-16">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-foreground mb-2 text-4xl font-semibold tracking-tight">
            Shared with Me
          </h1>
          <p className="text-muted-foreground text-sm">Agents that others have shared with you</p>
        </div>

        {/* Join via Share Code */}
        <div className="border-border bg-card shadow-soft-md mb-8 rounded-2xl border p-6">
          <h2 className="text-foreground mb-4 text-lg font-medium">Join with Share Code</h2>
          <div className="flex gap-3">
            <Input
              placeholder="Enter share code (e.g., abc12345)"
              value={shareCode}
              onChange={(e) => setShareCode(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAcceptShareCode()}
              disabled={isAccepting}
              className="flex-1"
            />
            <Button onClick={handleAcceptShareCode} disabled={isAccepting || !shareCode.trim()}>
              {isAccepting ? 'Joining...' : 'Join Agent'}
            </Button>
          </div>
        </div>

        {/* Loading State */}
        {!sharedAgents && !error && (
          <div className="space-y-4">
            <div className="border-border bg-card h-24 animate-pulse rounded-xl border" />
            <div className="border-border bg-card h-24 animate-pulse rounded-xl border" />
            <div className="border-border bg-card h-24 animate-pulse rounded-xl border" />
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="border-border bg-card rounded-xl border p-8 text-center">
            <p className="text-muted-foreground text-sm">Failed to load shared agents</p>
          </div>
        )}

        {/* Agents List */}
        {sharedAgents && sharedAgents.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2">
            {sharedAgents.map((agent) => (
              <Link key={agent.id} href={`/agents/${agent.id}?mode=use`} className="group">
                <div className="border-border bg-card shadow-soft-md hover:shadow-soft-lg h-full rounded-xl border p-6 transition-all duration-200 ease-out group-hover:-translate-y-1">
                  <div className="mb-3 flex items-start justify-between">
                    <h3 className="text-foreground group-hover:text-primary text-lg font-semibold transition-colors">
                      {agent.name}
                    </h3>
                    <span className="rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                      Shared
                    </span>
                  </div>

                  {agent.instructions && (
                    <p className="text-muted-foreground mb-4 line-clamp-2 text-sm">
                      {agent.instructions.split('\n')[0]}
                    </p>
                  )}

                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground text-xs">
                      {agent.status === 'active' ? '🟢 Active' : '⚪ Draft'}
                    </span>
                    <span className="text-muted-foreground group-hover:text-foreground text-sm transition-colors">
                      →
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Empty State */}
        {sharedAgents && sharedAgents.length === 0 && (
          <div className="border-border bg-card rounded-xl border py-16 text-center">
            <p className="text-muted-foreground mb-4 text-sm">
              No agents have been shared with you yet
            </p>
            <p className="text-muted-foreground text-xs">
              Ask someone to share an agent with you via email or share code
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
