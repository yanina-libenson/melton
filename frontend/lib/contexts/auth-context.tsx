'use client'

import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api/client'

const TOKEN_KEY = 'melton_auth_token'

export interface User {
  id: string
  email: string
  subdomain: string | null
  full_name: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  register: (
    email: string,
    password: string,
    fullName?: string
  ) => Promise<{ access_token: string }>
  login: (email: string, password: string) => Promise<{ access_token: string }>
  logout: () => void
  claimSubdomain: (subdomain: string) => Promise<User>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  const logout = useCallback(() => {
    console.log('[Auth] Logging out user')
    localStorage.removeItem(TOKEN_KEY)
    apiClient.clearToken()
    setUser(null)
    setIsAuthenticated(false)
    router.push('/auth')
  }, [router])

  const loadUser = useCallback(async () => {
    try {
      console.log('[Auth] Fetching current user...')
      const userData = await apiClient.getCurrentUser()
      console.log('[Auth] User loaded successfully:', userData.email)
      setUser(userData)
      setIsAuthenticated(true)
    } catch (error) {
      console.error('[Auth] Failed to load user:', error)

      // Only logout on auth errors (401), not on network errors
      if (error && typeof error === 'object' && 'status' in error && error.status === 401) {
        console.log('[Auth] Token invalid (401), logging out')
        logout()
      } else {
        // Network error or other issue - keep token but mark as not authenticated
        console.warn('[Auth] Network error loading user, keeping token but not authenticated')
        setIsAuthenticated(false)
        setIsLoading(false)
      }
    } finally {
      setIsLoading(false)
    }
  }, [logout])

  // Initialize auth state from localStorage
  useEffect(() => {
    console.log('[Auth] Initializing auth state...')
    const token = localStorage.getItem(TOKEN_KEY)
    console.log('[Auth] Token in localStorage:', token ? `${token.substring(0, 20)}...` : 'none')

    if (token) {
      console.log('[Auth] Setting token on apiClient and loading user...')
      apiClient.setToken(token)
      loadUser()
    } else {
      console.log('[Auth] No token found, not authenticated')
      setIsLoading(false)
    }

    // Verify token persistence every few seconds (debugging)
    const verifyInterval = setInterval(() => {
      const currentToken = localStorage.getItem(TOKEN_KEY)
      const apiToken = apiClient.getToken()

      if (currentToken && !apiToken) {
        console.error('[Auth] TOKEN DESYNC: localStorage has token but apiClient does not!')
        console.log('[Auth] Re-setting token on apiClient')
        apiClient.setToken(currentToken)
      }

      if (currentToken && apiToken && currentToken !== apiToken) {
        console.error('[Auth] TOKEN MISMATCH: localStorage and apiClient tokens differ!')
      }
    }, 5000)

    return () => clearInterval(verifyInterval)
  }, [loadUser])

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      console.log('[Auth] Registering user:', email)
      const response = await apiClient.register({
        email,
        password,
        full_name: fullName,
      })

      // Store token
      console.log('[Auth] Registration successful, storing token')
      localStorage.setItem(TOKEN_KEY, response.access_token)
      apiClient.setToken(response.access_token)

      // Load user data
      await loadUser()

      return response
    },
    [loadUser]
  )

  const login = useCallback(
    async (email: string, password: string) => {
      console.log('[Auth] Logging in user:', email)
      const response = await apiClient.login({ email, password })

      // Store token
      console.log('[Auth] Login successful, storing token')
      localStorage.setItem(TOKEN_KEY, response.access_token)
      apiClient.setToken(response.access_token)

      // Load user data
      await loadUser()

      return response
    },
    [loadUser]
  )

  const claimSubdomain = useCallback(async (subdomain: string) => {
    const updatedUser = await apiClient.claimSubdomain(subdomain)
    setUser(updatedUser)
    return updatedUser
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated,
        register,
        login,
        logout,
        claimSubdomain,
        refreshUser: loadUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
