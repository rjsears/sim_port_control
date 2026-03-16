import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

// Mock the api module
vi.mock('@/services/api', () => ({
  default: {
    post: vi.fn(),
    defaults: {
      headers: {
        common: {}
      }
    }
  }
}))

import api from '@/services/api'

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should have null user and token initially', () => {
      const store = useAuthStore()
      expect(store.user).toBeNull()
      expect(store.token).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should not be authenticated initially', () => {
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(false)
    })

    it('should not be admin initially', () => {
      const store = useAuthStore()
      expect(store.isAdmin).toBe(false)
    })

    it('should have empty username initially', () => {
      const store = useAuthStore()
      expect(store.username).toBe('')
    })
  })

  describe('initAuth', () => {
    it('should restore token and user from localStorage', () => {
      const savedUser = { id: 1, username: 'testuser', role: 'admin' }
      localStorage.setItem('token', 'saved-token')
      localStorage.setItem('user', JSON.stringify(savedUser))

      const store = useAuthStore()
      store.initAuth()

      expect(store.token).toBe('saved-token')
      expect(store.user).toEqual(savedUser)
      expect(store.isAuthenticated).toBe(true)
      expect(api.defaults.headers.common['Authorization']).toBe('Bearer saved-token')
    })

    it('should do nothing if no saved token', () => {
      const store = useAuthStore()
      store.initAuth()

      expect(store.token).toBeNull()
      expect(store.user).toBeNull()
    })
  })

  describe('login', () => {
    it('should login successfully and store credentials', async () => {
      const mockResponse = {
        data: {
          access_token: 'new-token',
          user: { id: 1, username: 'admin', role: 'admin' }
        }
      }
      api.post.mockResolvedValueOnce(mockResponse)

      const store = useAuthStore()
      const result = await store.login('admin', 'password')

      expect(result).toBe(true)
      expect(store.token).toBe('new-token')
      expect(store.user).toEqual(mockResponse.data.user)
      expect(store.isAuthenticated).toBe(true)
      expect(store.isAdmin).toBe(true)
      expect(localStorage.getItem('token')).toBe('new-token')
      expect(JSON.parse(localStorage.getItem('user'))).toEqual(mockResponse.data.user)
    })

    it('should set loading during login', async () => {
      let resolvePromise
      api.post.mockImplementationOnce(() => new Promise(resolve => { resolvePromise = resolve }))

      const store = useAuthStore()
      const loginPromise = store.login('admin', 'password')

      expect(store.loading).toBe(true)

      resolvePromise({ data: { access_token: 'token', user: {} } })
      await loginPromise

      expect(store.loading).toBe(false)
    })

    it('should handle login failure', async () => {
      api.post.mockRejectedValueOnce({
        response: { data: { detail: 'Invalid credentials' } }
      })

      const store = useAuthStore()
      const result = await store.login('admin', 'wrongpassword')

      expect(result).toBe(false)
      expect(store.error).toBe('Invalid credentials')
      expect(store.token).toBeNull()
      expect(store.isAuthenticated).toBe(false)
    })

    it('should use default error message on network failure', async () => {
      api.post.mockRejectedValueOnce(new Error('Network error'))

      const store = useAuthStore()
      const result = await store.login('admin', 'password')

      expect(result).toBe(false)
      expect(store.error).toBe('Login failed')
    })
  })

  describe('logout', () => {
    it('should clear credentials on logout', async () => {
      // Setup logged in state
      const store = useAuthStore()
      store.token = 'test-token'
      store.user = { id: 1, username: 'test' }
      localStorage.setItem('token', 'test-token')
      localStorage.setItem('user', JSON.stringify({ id: 1 }))
      api.defaults.headers.common['Authorization'] = 'Bearer test-token'

      api.post.mockResolvedValueOnce({})

      await store.logout()

      expect(store.token).toBeNull()
      expect(store.user).toBeNull()
      expect(localStorage.getItem('token')).toBeNull()
      expect(localStorage.getItem('user')).toBeNull()
      expect(api.defaults.headers.common['Authorization']).toBeUndefined()
    })

    it('should clear credentials even if logout request fails', async () => {
      const store = useAuthStore()
      store.token = 'test-token'
      store.user = { id: 1 }
      localStorage.setItem('token', 'test-token')

      api.post.mockRejectedValueOnce(new Error('Network error'))

      await store.logout()

      expect(store.token).toBeNull()
      expect(store.user).toBeNull()
      expect(localStorage.getItem('token')).toBeNull()
    })
  })

  describe('computed properties', () => {
    it('isAdmin should return true for admin users', () => {
      const store = useAuthStore()
      store.user = { role: 'admin' }
      expect(store.isAdmin).toBe(true)
    })

    it('isAdmin should return false for non-admin users', () => {
      const store = useAuthStore()
      store.user = { role: 'simtech' }
      expect(store.isAdmin).toBe(false)
    })

    it('username should return user username', () => {
      const store = useAuthStore()
      store.user = { username: 'testuser' }
      expect(store.username).toBe('testuser')
    })
  })
})
