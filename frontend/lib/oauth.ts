/**
 * OAuth 2.0 flow helper for popup-based authorization
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface OAuthResult {
  success: boolean
  integrationId?: string
  error?: string
}

/**
 * Initiate OAuth flow in a popup window
 *
 * @param platformId - Platform identifier (e.g., 'mercadolibre')
 * @param integrationId - Integration ID to associate with OAuth flow
 * @returns Promise that resolves when OAuth flow completes
 */
export async function initiateOAuthFlow(
  platformId: string,
  integrationId: string
): Promise<OAuthResult> {
  try {
    console.log('[OAuth] Initiating flow:', { platformId, integrationId, API_BASE_URL })

    // Get authorization URL from backend
    const url = `${API_BASE_URL}/api/v1/oauth/authorize/${platformId}?integration_id=${integrationId}`
    console.log('[OAuth] Fetching:', url)

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true',
      },
    })

    console.log('[OAuth] Response status:', response.status)

    if (!response.ok) {
      const error = await response.json()
      console.error('[OAuth] Error response:', error)
      return {
        success: false,
        error: error.detail || 'Failed to initiate OAuth flow',
      }
    }

    const data = await response.json()
    console.log('[OAuth] Response data:', data)
    const { authorization_url } = data

    if (!authorization_url) {
      return {
        success: false,
        error: 'No authorization URL received from server',
      }
    }

    // Open OAuth popup
    const popup = window.open(
      authorization_url,
      'oauth_popup',
      'width=600,height=700,scrollbars=yes,resizable=yes'
    )

    if (!popup) {
      return {
        success: false,
        error: 'Failed to open OAuth popup. Please check your browser popup settings.',
      }
    }

    // Wait for callback message from popup
    return new Promise<OAuthResult>((resolve) => {
      let checkClosed: NodeJS.Timeout | null = null
      let timeoutId: NodeJS.Timeout | null = null
      let resolved = false

      const cleanup = () => {
        if (checkClosed) clearInterval(checkClosed)
        if (timeoutId) clearTimeout(timeoutId)
        window.removeEventListener('message', messageHandler)
      }

      const messageHandler = (event: MessageEvent) => {
        // Accept messages from localhost or ngrok (for OAuth callback)
        const isValidOrigin =
          event.origin === window.location.origin || event.origin.includes('ngrok-free.app')

        if (!isValidOrigin) {
          console.log('[OAuth] Ignoring message from invalid origin:', event.origin)
          return
        }

        // Check for OAuth callback message
        if (event.data.type === 'oauth_callback') {
          console.log('[OAuth] Received callback message:', event.data)

          if (resolved) {
            console.log('[OAuth] Already resolved, ignoring duplicate message')
            return
          }

          resolved = true
          cleanup()

          if (event.data.status === 'success') {
            resolve({
              success: true,
              integrationId: event.data.integration_id,
            })
          } else {
            resolve({
              success: false,
              error: event.data.error || 'OAuth authorization failed',
            })
          }
        }
      }

      window.addEventListener('message', messageHandler)

      // Check if popup was closed before completion
      checkClosed = setInterval(() => {
        if (popup.closed) {
          console.log('[OAuth] Popup closed, resolved:', resolved)

          if (resolved) {
            clearInterval(checkClosed!)
            return
          }

          resolved = true
          cleanup()
          resolve({
            success: false,
            error: 'OAuth window was closed before completing authorization',
          })
        }
      }, 500)

      // Timeout after 5 minutes
      timeoutId = setTimeout(() => {
        if (resolved) {
          return
        }

        resolved = true
        cleanup()

        if (!popup.closed) {
          popup.close()
        }

        resolve({
          success: false,
          error: 'OAuth flow timed out after 5 minutes',
        })
      }, 300000) // 5 minutes
    })
  } catch (error) {
    console.error('[OAuth] Exception caught:', error)
    if (error instanceof TypeError && error.message.includes('fetch')) {
      console.error('[OAuth] Network error - check if backend is running and CORS is configured')
    }
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred',
    }
  }
}
