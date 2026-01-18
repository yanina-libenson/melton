'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { useAuth } from '@/lib/contexts/auth-context'
import { APIError } from '@/lib/api/client'

export default function AuthPage() {
  const router = useRouter()
  const { register, login } = useAuth()

  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    // Validation
    if (!email.trim() || !email.includes('@')) {
      toast.error('Please enter a valid email address')
      return
    }

    if (password.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }

    setIsLoading(true)

    try {
      if (mode === 'register') {
        await register(email, password)
        toast.success('Account created successfully!')
      } else {
        await login(email, password)
        toast.success('Welcome back!')
      }

      // Redirect to agents page
      router.push('/agents')
    } catch (error) {
      if (error instanceof APIError) {
        // Extract error message from API response
        const message = (error.data as { detail?: string })?.detail || 'Authentication failed'
        toast.error(message)
      } else {
        toast.error('Something went wrong. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="bg-background flex min-h-screen items-center justify-center px-8">
      <div className="w-full max-w-md">
        <div className="mb-12 text-center">
          <h1 className="text-foreground mb-2 text-4xl font-semibold tracking-tight">
            {mode === 'login' ? 'Sign In' : 'Create Account'}
          </h1>
          <p className="text-muted-foreground text-sm">
            {mode === 'login'
              ? 'Welcome back! Sign in to continue.'
              : 'Get started by creating your account.'}
          </p>
        </div>

        <div className="border-border bg-card shadow-soft-md rounded-2xl border p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <Label className="text-foreground mb-3 block text-sm font-medium">Email</Label>
              <Input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoFocus
                disabled={isLoading}
              />
            </div>

            <div>
              <Label className="text-foreground mb-3 block text-sm font-medium">Password</Label>
              <Input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                minLength={8}
              />
              <p className="text-muted-foreground mt-2 text-xs">
                {mode === 'register' && 'Must be at least 8 characters'}
              </p>
            </div>

            <Button type="submit" disabled={isLoading} className="w-full" size="lg">
              {isLoading
                ? mode === 'login'
                  ? 'Signing in...'
                  : 'Creating account...'
                : mode === 'login'
                  ? 'Sign In'
                  : 'Create Account'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setMode(mode === 'login' ? 'register' : 'login')
                setPassword('')
              }}
              className="text-muted-foreground hover:text-foreground text-sm transition-colors"
              disabled={isLoading}
            >
              {mode === 'login'
                ? "Don't have an account? Sign up"
                : 'Already have an account? Sign in'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
