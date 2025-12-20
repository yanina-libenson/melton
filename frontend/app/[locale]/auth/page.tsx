'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'

export default function AuthPage() {
  const router = useRouter()
  const t = useTranslations('auth')
  const [step, setStep] = useState<'email' | 'code'>('email')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function handleSendCode() {
    if (!email.trim() || !email.includes('@')) {
      toast.error(t('errorInvalidEmail'))
      return
    }

    setIsLoading(true)

    // Mock API call - in production this would send the code via email
    setTimeout(() => {
      setIsLoading(false)
      setStep('code')
      toast.success(t('successCheckEmail'))
    }, 1000)
  }

  async function handleVerifyCode() {
    if (!code.trim() || code.length < 6) {
      toast.error(t('errorInvalidCode'))
      return
    }

    setIsLoading(true)

    // Mock API call - in production this would verify the code
    setTimeout(() => {
      setIsLoading(false)
      toast.success(t('successWelcome'))
      router.push('/agents')
    }, 1000)
  }

  return (
    <div className="bg-background flex min-h-screen items-center justify-center px-8">
      <div className="w-full max-w-md">
        <div className="mb-12 text-center">
          <h1 className="text-foreground mb-2 text-4xl font-semibold tracking-tight">
            {t('title')}
          </h1>
          <p className="text-muted-foreground text-sm">
            {step === 'email' ? t('signInSubtitle') : t('codeSubtitle')}
          </p>
        </div>

        <div className="border-border bg-card shadow-soft-md rounded-2xl border p-8">
          {step === 'email' ? (
            <div className="space-y-6">
              <div>
                <Label className="text-foreground mb-3 block text-sm font-medium">
                  {t('email')}
                </Label>
                <Input
                  type="email"
                  placeholder={t('emailPlaceholder')}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendCode()}
                  autoFocus
                />
              </div>

              <Button onClick={handleSendCode} disabled={isLoading} className="w-full" size="lg">
                {isLoading ? t('sending') : t('continue')}
              </Button>
            </div>
          ) : (
            <div className="space-y-6">
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <Label className="text-foreground text-sm font-medium">
                    {t('verificationCode')}
                  </Label>
                  <button
                    onClick={() => setStep('email')}
                    className="text-muted-foreground hover:text-foreground text-xs transition-colors"
                  >
                    {t('changeEmail')}
                  </button>
                </div>
                <Input
                  type="text"
                  placeholder={t('codePlaceholder')}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  onKeyDown={(e) => e.key === 'Enter' && handleVerifyCode()}
                  autoFocus
                  maxLength={6}
                />
                <p className="text-muted-foreground mt-2 text-xs">{t('sentTo', { email })}</p>
              </div>

              <Button onClick={handleVerifyCode} disabled={isLoading} className="w-full" size="lg">
                {isLoading ? t('verifying') : t('verify')}
              </Button>

              <button
                onClick={handleSendCode}
                className="text-muted-foreground hover:text-foreground w-full text-sm transition-colors"
              >
                {t('resendCode')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
