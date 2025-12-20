'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'

export default function AuthPage() {
  const router = useRouter()
  const [step, setStep] = useState<'email' | 'code'>('email')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function handleSendCode() {
    if (!email.trim() || !email.includes('@')) {
      toast.error('Please enter a valid email address')
      return
    }

    setIsLoading(true)

    // Mock API call - in production this would send the code via email
    setTimeout(() => {
      setIsLoading(false)
      setStep('code')
      toast.success('Check your email for the code')
    }, 1000)
  }

  async function handleVerifyCode() {
    if (!code.trim() || code.length < 6) {
      toast.error('Please enter the 6-digit code')
      return
    }

    setIsLoading(true)

    // Mock API call - in production this would verify the code
    setTimeout(() => {
      setIsLoading(false)
      toast.success('Welcome!')
      router.push('/agents')
    }, 1000)
  }

  return (
    <div className="bg-background flex min-h-screen items-center justify-center px-8">
      <div className="w-full max-w-md">
        <div className="mb-12 text-center">
          <h1 className="text-foreground mb-2 text-4xl font-semibold tracking-tight">
            Welcome to Cesar
          </h1>
          <p className="text-muted-foreground text-sm">
            {step === 'email' ? 'Sign in or create an account' : 'Enter the code we sent you'}
          </p>
        </div>

        <div className="border-border bg-card shadow-soft-md rounded-2xl border p-8">
          {step === 'email' ? (
            <div className="space-y-6">
              <div>
                <Label className="text-foreground mb-3 block text-sm font-medium">Email</Label>
                <Input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendCode()}
                  autoFocus
                />
              </div>

              <Button onClick={handleSendCode} disabled={isLoading} className="w-full" size="lg">
                {isLoading ? 'Sending...' : 'Continue'}
              </Button>
            </div>
          ) : (
            <div className="space-y-6">
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <Label className="text-foreground text-sm font-medium">Verification Code</Label>
                  <button
                    onClick={() => setStep('email')}
                    className="text-muted-foreground hover:text-foreground text-xs transition-colors"
                  >
                    Change email
                  </button>
                </div>
                <Input
                  type="text"
                  placeholder="123456"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  onKeyDown={(e) => e.key === 'Enter' && handleVerifyCode()}
                  autoFocus
                  maxLength={6}
                />
                <p className="text-muted-foreground mt-2 text-xs">Sent to {email}</p>
              </div>

              <Button onClick={handleVerifyCode} disabled={isLoading} className="w-full" size="lg">
                {isLoading ? 'Verifying...' : 'Verify'}
              </Button>

              <button
                onClick={handleSendCode}
                className="text-muted-foreground hover:text-foreground w-full text-sm transition-colors"
              >
                Resend code
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
