'use client'

import { use, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'

// Get API base URL - use environment variable or default to localhost
const getApiBaseUrl = () => {
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
}

export default function OAuthCallbackPage({ params }: { params: Promise<{ platform: string }> }) {
  const API_BASE_URL = getApiBaseUrl()
  const searchParams = useSearchParams()
  const resolvedParams = use(params)

  // Parse URL parameters
  const code = searchParams.get('code')
  const state = searchParams.get('state')
  const error = searchParams.get('error')
  const errorDescription = searchParams.get('error_description')

  // Get platform from route params
  const platformId = resolvedParams.platform

  // Check if we're in a popup window (do this once)
  const [isPopup] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.opener && window.opener !== window
    }
    return false
  })

  const [message, setMessage] = useState('Processing authorization...')

  useEffect(() => {
    async function handleOAuthCallback() {
      console.log('[OAuth Callback] Starting...')
      console.log('[OAuth Callback] API_BASE_URL:', API_BASE_URL)
      console.log('[OAuth Callback] platformId:', platformId)
      console.log('[OAuth Callback] code:', code ? 'present' : 'missing')
      console.log('[OAuth Callback] state:', state ? 'present' : 'missing')
      console.log('[OAuth Callback] isPopup:', isPopup)
      console.log('[OAuth Callback] window.opener exists:', !!window.opener)

      if (!isPopup) {
        console.error('[OAuth Callback] Not a popup! window.opener is missing')
        setMessage('This page should only be accessed via OAuth popup flow.')
        return
      }

      // Check for OAuth provider errors
      if (error) {
        const errorMsg = errorDescription || error
        console.error('[OAuth Callback] OAuth provider error:', errorMsg)
        window.opener.postMessage(
          {
            type: 'oauth_callback',
            status: 'error',
            error: errorMsg,
          },
          window.location.origin
        )
        setMessage(`Authorization failed: ${errorMsg}`)
        setTimeout(() => window.close(), 1500)
        return
      }

      // Exchange code for tokens
      if (code && state && platformId) {
        try {
          const exchangeUrl = `${API_BASE_URL}/api/v1/oauth/exchange/${platformId}?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`
          console.log('[OAuth Callback] Fetching:', exchangeUrl)

          const response = await fetch(exchangeUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'ngrok-skip-browser-warning': 'true',
            },
          })

          console.log('[OAuth Callback] Response status:', response.status)
          console.log('[OAuth Callback] Response ok:', response.ok)

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
            console.error('[OAuth Callback] Error response:', errorData)
            console.error('[OAuth Callback] About to send error postMessage to parent')
            throw new Error(errorData.detail || 'Token exchange failed')
          }

          const data = await response.json()
          console.log('[OAuth Callback] Success! Integration ID:', data.integration_id)

          // Send success message to parent
          console.log('[OAuth Callback] window.opener exists:', !!window.opener)
          console.log('[OAuth Callback] window.location.origin:', window.location.origin)
          console.log('[OAuth Callback] About to send success postMessage')

          if (window.opener) {
            window.opener.postMessage(
              {
                type: 'oauth_callback',
                status: 'success',
                integration_id: data.integration_id,
              },
              '*' // Use wildcard for ngrok compatibility
            )
            console.log('[OAuth Callback] Success postMessage sent')
          } else {
            console.warn('[OAuth Callback] No window.opener found!')
          }

          setMessage('Authorization successful! Closing...')
          // Wait longer to ensure postMessage is received
          setTimeout(() => window.close(), 3000)
        } catch (err) {
          const errorMsg = err instanceof Error ? err.message : 'Unknown error'
          console.error('[OAuth Callback] Caught error:', errorMsg, err)
          console.error('[OAuth Callback] window.opener exists:', !!window.opener)
          console.error('[OAuth Callback] window.location.origin:', window.location.origin)
          console.error('[OAuth Callback] About to send error postMessage')

          if (window.opener) {
            window.opener.postMessage(
              {
                type: 'oauth_callback',
                status: 'error',
                error: errorMsg,
              },
              '*'
            )
            console.error('[OAuth Callback] Error postMessage sent')
          } else {
            console.error('[OAuth Callback] Cannot send error - no window.opener!')
          }

          setMessage(`Authorization failed: ${errorMsg}`)
          setTimeout(() => {
            console.error('[OAuth Callback] Closing popup after error')
            window.close()
          }, 1500)
        }
      } else {
        console.error('[OAuth Callback] Missing parameters:', { code, state, platformId })
        setMessage('Invalid OAuth callback parameters')
      }
    }

    handleOAuthCallback()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="bg-background flex min-h-screen items-center justify-center">
      <div className="max-w-md p-8 text-center">
        <div className="mb-4">
          <svg
            className="text-primary mx-auto h-12 w-12 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        </div>
        <h1 className="mb-2 text-2xl font-semibold">OAuth Authorization</h1>
        <p className="text-muted-foreground">{message}</p>
      </div>
    </div>
  )
}
