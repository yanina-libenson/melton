'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Sparkles, Zap, Users } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="from-background to-muted/20 min-h-screen bg-gradient-to-b">
      {/* Hero Section */}
      <div className="container mx-auto px-6 py-20">
        <div className="mx-auto max-w-4xl text-center">
          <h1 className="mb-6 text-5xl font-bold tracking-tight sm:text-6xl">
            Build Your Own AI Agents
          </h1>
          <p className="text-muted-foreground mb-8 text-xl">
            Create custom AI agents with tools, deploy them anywhere, and share with your team. No
            code required.
          </p>
          <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
            <Link href="/auth">
              <Button size="lg" className="w-full sm:w-auto">
                Get Started
              </Button>
            </Link>
            <Link href="/agents">
              <Button size="lg" variant="outline" className="w-full sm:w-auto">
                View Agents
              </Button>
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="mx-auto mt-24 grid max-w-5xl gap-8 md:grid-cols-3">
          <div className="bg-card rounded-lg border p-6">
            <div className="bg-primary/10 mb-4 inline-flex rounded-lg p-3">
              <Sparkles className="text-primary h-6 w-6" />
            </div>
            <h3 className="mb-2 text-lg font-semibold">Easy to Build</h3>
            <p className="text-muted-foreground text-sm">
              Create agents with simple instructions. Add tools from popular platforms like
              MercadoLibre, Spotify, and more.
            </p>
          </div>

          <div className="bg-card rounded-lg border p-6">
            <div className="bg-primary/10 mb-4 inline-flex rounded-lg p-3">
              <Zap className="text-primary h-6 w-6" />
            </div>
            <h3 className="mb-2 text-lg font-semibold">Deploy Anywhere</h3>
            <p className="text-muted-foreground text-sm">
              Deploy your agents to custom subdomains. Share them publicly or keep them private for
              your team.
            </p>
          </div>

          <div className="bg-card rounded-lg border p-6">
            <div className="bg-primary/10 mb-4 inline-flex rounded-lg p-3">
              <Users className="text-primary h-6 w-6" />
            </div>
            <h3 className="mb-2 text-lg font-semibold">Collaborate</h3>
            <p className="text-muted-foreground text-sm">
              Share agents with your team using simple share codes. Everyone gets their own
              conversations and permissions.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
