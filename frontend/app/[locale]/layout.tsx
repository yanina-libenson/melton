import type { Metadata } from 'next'
import { Inter, Dancing_Script } from 'next/font/google'
import { NextIntlClientProvider } from 'next-intl'
import { getMessages } from 'next-intl/server'
import { notFound } from 'next/navigation'
import '../globals.css'
import { Toaster } from '@/components/ui/sonner'
import { Nav } from '@/components/nav'
import { locales, type Locale } from '@/lib/i18n/config'
import { AuthProvider } from '@/lib/contexts/auth-context'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
})

const dancingScript = Dancing_Script({
  subsets: ['latin'],
  weight: '700',
  variable: '--font-signature',
})

export const metadata: Metadata = {
  title: 'Dr. Melton - Build Powerful AI Agents',
  description: 'Create and deploy AI agents for your business with an easy-to-use interface',
}

type Props = {
  children: React.ReactNode
  params: Promise<{ locale: string }>
}

export default async function RootLayout({ children, params }: Props) {
  const { locale } = await params

  // Validate locale
  if (!locales.includes(locale as Locale)) {
    notFound()
  }

  // Providing all messages to the client side is the easiest way to get started
  const messages = await getMessages()

  return (
    <html lang={locale}>
      <body className={`${inter.variable} ${dancingScript.variable} font-sans antialiased`}>
        <NextIntlClientProvider messages={messages}>
          <AuthProvider>
            <Nav />
            <main className="pt-14">{children}</main>
            <Toaster />
          </AuthProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  )
}
