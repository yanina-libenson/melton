import type { Metadata } from 'next'
import { Inter, Dancing_Script } from 'next/font/google'
import './globals.css'
import { Toaster } from '@/components/ui/sonner'
import { Nav } from '@/components/nav'

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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${dancingScript.variable} font-sans antialiased`}>
        <Nav />
        <main className="pt-14">{children}</main>
        <Toaster />
      </body>
    </html>
  )
}
