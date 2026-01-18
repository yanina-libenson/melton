'use client'

import { useState } from 'react'
import { apiClient } from '@/lib/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import useSWR, { mutate } from 'swr'
import { useAuth } from '@/lib/contexts/auth-context'

interface AgentPermission {
  user_id: string
  email: string
  full_name: string | null
  permission_type: string
  granted_at: string
  granted_by: string
}

interface AgentPermissionsProps {
  agentId: string
}

export function AgentPermissions({ agentId }: AgentPermissionsProps) {
  const { user } = useAuth()
  const [isAdding, setIsAdding] = useState(false)
  const [newUserEmail, setNewUserEmail] = useState('')
  const [newUserPermission, setNewUserPermission] = useState<'use' | 'admin'>('use')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Fetch permissions
  const { data: permissions, error } = useSWR<AgentPermission[]>(
    agentId ? `/agents/${agentId}/permissions` : null,
    () => apiClient.listAgentPermissions(agentId)
  )

  const handleAddUser = async () => {
    if (!newUserEmail.trim() || !newUserEmail.includes('@')) {
      toast.error('Please enter a valid email address')
      return
    }

    setIsSubmitting(true)
    try {
      await apiClient.grantPermission(agentId, newUserEmail, newUserPermission)
      toast.success(`Permission granted to ${newUserEmail}`)
      setNewUserEmail('')
      setNewUserPermission('use')
      setIsAdding(false)
      mutate(`/agents/${agentId}/permissions`)
    } catch (error: unknown) {
      const message =
        (error as { data?: { detail?: string } })?.data?.detail || 'Failed to grant permission'
      toast.error(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleRemoveUser = async (userId: string, email: string) => {
    if (!confirm(`Remove access for ${email}?`)) {
      return
    }

    try {
      await apiClient.revokePermission(agentId, userId)
      toast.success(`Access revoked for ${email}`)
      mutate(`/agents/${agentId}/permissions`)
    } catch (error: unknown) {
      const message =
        (error as { data?: { detail?: string } })?.data?.detail || 'Failed to revoke permission'
      toast.error(message)
    }
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
        <p className="text-sm text-red-600 dark:text-red-400">
          Failed to load permissions. You may not have admin access.
        </p>
      </div>
    )
  }

  if (!permissions) {
    return (
      <div className="space-y-4">
        <div className="h-16 animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700" />
        <div className="h-16 animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-foreground text-lg font-medium">Agent Access</h3>
          <p className="text-muted-foreground text-sm">Manage who can use and edit this agent</p>
        </div>
        {!isAdding && (
          <Button onClick={() => setIsAdding(true)} size="sm">
            Add User
          </Button>
        )}
      </div>

      {/* Add User Form */}
      {isAdding && (
        <div className="border-border bg-card shadow-soft-xs rounded-lg border p-4">
          <div className="space-y-4">
            <div>
              <Label className="text-foreground mb-2 block text-sm font-medium">
                Email Address
              </Label>
              <Input
                type="email"
                placeholder="user@example.com"
                value={newUserEmail}
                onChange={(e) => setNewUserEmail(e.target.value)}
                disabled={isSubmitting}
              />
            </div>

            <div>
              <Label className="text-foreground mb-2 block text-sm font-medium">
                Permission Level
              </Label>
              <Select
                value={newUserPermission}
                onValueChange={(value) => setNewUserPermission(value as 'use' | 'admin')}
                disabled={isSubmitting}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="use">
                    <div className="flex flex-col items-start">
                      <span className="font-medium">Use</span>
                      <span className="text-muted-foreground text-xs">Can chat with the agent</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="admin">
                    <div className="flex flex-col items-start">
                      <span className="font-medium">Admin</span>
                      <span className="text-muted-foreground text-xs">
                        Full access - edit, delete, manage permissions
                      </span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex gap-2">
              <Button onClick={handleAddUser} disabled={isSubmitting}>
                {isSubmitting ? 'Adding...' : 'Add User'}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setIsAdding(false)
                  setNewUserEmail('')
                  setNewUserPermission('use')
                }}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Users List */}
      <div className="space-y-2">
        {permissions.map((permission) => {
          const isCurrentUser = permission.user_id === user?.id
          const canRemove = !isCurrentUser // Can't remove yourself

          return (
            <div
              key={permission.user_id}
              className="border-border bg-card shadow-soft-xs flex items-center justify-between rounded-lg border p-4"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-foreground text-sm font-medium">
                    {permission.email}
                    {isCurrentUser && (
                      <span className="text-muted-foreground ml-2 text-xs">(You)</span>
                    )}
                  </p>
                  {permission.permission_type === 'admin' ? (
                    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                      Admin
                    </span>
                  ) : (
                    <span className="text-muted-foreground rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium dark:bg-gray-800">
                      Use
                    </span>
                  )}
                </div>
                {permission.full_name && (
                  <p className="text-muted-foreground text-xs">{permission.full_name}</p>
                )}
              </div>

              {canRemove && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRemoveUser(permission.user_id, permission.email)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  Remove
                </Button>
              )}
            </div>
          )
        })}

        {permissions.length === 0 && (
          <div className="border-border rounded-lg border border-dashed py-12 text-center">
            <p className="text-muted-foreground text-sm">No users have access yet</p>
          </div>
        )}
      </div>
    </div>
  )
}
