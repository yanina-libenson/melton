'use client'

import { useState } from 'react'
import { apiClient } from '@/lib/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'

interface AgentShareLinkProps {
  agentId: string
}

export function AgentShareLink({ agentId }: AgentShareLinkProps) {
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isRevoking, setIsRevoking] = useState(false)

  const handleGenerate = async () => {
    setIsGenerating(true)
    try {
      const result = await apiClient.generateShareCode(agentId)
      setShareUrl(result.share_url)
      toast.success('Share link generated!')
    } catch (error: unknown) {
      const message =
        (error as { data?: { detail?: string } })?.data?.detail || 'Failed to generate share link'
      toast.error(message)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleCopy = () => {
    if (shareUrl) {
      navigator.clipboard.writeText(shareUrl)
      toast.success('Link copied to clipboard!')
    }
  }

  const handleRevoke = async () => {
    if (
      !confirm('Revoke this share link? Users with the old link will no longer be able to join.')
    ) {
      return
    }

    setIsRevoking(true)
    try {
      await apiClient.revokeShareCode(agentId)
      setShareUrl(null)
      toast.success('Share link revoked')
    } catch (error: unknown) {
      const message =
        (error as { data?: { detail?: string } })?.data?.detail || 'Failed to revoke share link'
      toast.error(message)
    } finally {
      setIsRevoking(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h3 className="text-foreground text-lg font-medium">Share Link</h3>
        <p className="text-muted-foreground text-sm">
          Generate a link that anyone can use to get access to this agent
        </p>
      </div>

      {!shareUrl ? (
        /* Generate Button */
        <Button onClick={handleGenerate} disabled={isGenerating} size="lg">
          {isGenerating ? 'Generating...' : 'Generate Share Link'}
        </Button>
      ) : (
        /* Share Link Display */
        <div className="border-border bg-card shadow-soft-xs space-y-4 rounded-lg border p-4">
          <div>
            <label className="text-foreground mb-2 block text-sm font-medium">Share URL</label>
            <div className="flex gap-2">
              <Input value={shareUrl} readOnly className="font-mono text-sm" />
              <Button onClick={handleCopy} variant="outline">
                Copy
              </Button>
            </div>
          </div>

          <div className="border-t border-gray-200 pt-4 dark:border-gray-700">
            <p className="text-muted-foreground mb-3 text-xs">
              Anyone with this link can join as a &ldquo;use&rdquo; member. If you revoke it, the
              old link will stop working.
            </p>
            <Button
              onClick={handleRevoke}
              disabled={isRevoking}
              variant="outline"
              size="sm"
              className="text-red-600 hover:bg-red-50 hover:text-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
            >
              {isRevoking ? 'Revoking...' : 'Revoke Link'}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
