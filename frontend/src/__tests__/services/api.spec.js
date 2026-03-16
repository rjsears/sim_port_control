import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock axios before importing api
vi.mock('axios', () => {
  const mockAxios = {
    create: vi.fn(() => mockAxios),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    defaults: {
      headers: {
        common: {}
      }
    }
  }
  return { default: mockAxios }
})

// Mock the router
vi.mock('@/router', () => ({
  default: {
    push: vi.fn()
  }
}))

import axios from 'axios'
import router from '@/router'

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('axios instance configuration', () => {
    it('should create axios instance with correct config', async () => {
      // Re-import to trigger module execution
      vi.resetModules()
      await import('@/services/api')

      expect(axios.create).toHaveBeenCalledWith({
        baseURL: '/api',
        timeout: 30000,
        headers: {
          'Content-Type': 'application/json'
        }
      })
    })

    it('should register request interceptor', async () => {
      vi.resetModules()
      await import('@/services/api')

      expect(axios.interceptors.request.use).toHaveBeenCalled()
    })

    it('should register response interceptor', async () => {
      vi.resetModules()
      await import('@/services/api')

      expect(axios.interceptors.response.use).toHaveBeenCalled()
    })
  })

  describe('request interceptor', () => {
    it('should add Authorization header when token exists', async () => {
      vi.resetModules()

      // Set up the token before importing
      localStorage.setItem('token', 'test-token')

      await import('@/services/api')

      // Get the request interceptor callback
      const requestCallback = axios.interceptors.request.use.mock.calls[0][0]

      const config = { headers: {} }
      const result = requestCallback(config)

      expect(result.headers.Authorization).toBe('Bearer test-token')
    })

    it('should not add Authorization header when no token', async () => {
      vi.resetModules()

      await import('@/services/api')

      const requestCallback = axios.interceptors.request.use.mock.calls[0][0]

      const config = { headers: {} }
      const result = requestCallback(config)

      expect(result.headers.Authorization).toBeUndefined()
    })

    it('should reject on request error', async () => {
      vi.resetModules()

      await import('@/services/api')

      const errorCallback = axios.interceptors.request.use.mock.calls[0][1]
      const error = new Error('Request error')

      await expect(errorCallback(error)).rejects.toThrow('Request error')
    })
  })

  describe('response interceptor', () => {
    it('should pass through successful responses', async () => {
      vi.resetModules()

      await import('@/services/api')

      const successCallback = axios.interceptors.response.use.mock.calls[0][0]
      const response = { data: 'test' }

      expect(successCallback(response)).toBe(response)
    })

    it('should handle 401 errors by clearing storage and redirecting', async () => {
      vi.resetModules()

      localStorage.setItem('token', 'test-token')
      localStorage.setItem('user', JSON.stringify({ username: 'test' }))

      await import('@/services/api')

      const errorCallback = axios.interceptors.response.use.mock.calls[0][1]
      const error = { response: { status: 401 } }

      await expect(errorCallback(error)).rejects.toEqual(error)

      expect(localStorage.getItem('token')).toBeNull()
      expect(localStorage.getItem('user')).toBeNull()
      expect(router.push).toHaveBeenCalledWith({ name: 'login' })
    })

    it('should not redirect on non-401 errors', async () => {
      vi.resetModules()

      await import('@/services/api')

      const errorCallback = axios.interceptors.response.use.mock.calls[0][1]
      const error = { response: { status: 500 } }

      await expect(errorCallback(error)).rejects.toEqual(error)

      expect(router.push).not.toHaveBeenCalled()
    })
  })

  describe('authApi', () => {
    it('should export authApi with correct methods', async () => {
      vi.resetModules()
      const { authApi } = await import('@/services/api')

      expect(authApi).toHaveProperty('login')
      expect(authApi).toHaveProperty('logout')
      expect(authApi).toHaveProperty('me')
      expect(authApi).toHaveProperty('changePassword')
    })
  })

  describe('simulatorsApi', () => {
    it('should export simulatorsApi with correct methods', async () => {
      vi.resetModules()
      const { simulatorsApi } = await import('@/services/api')

      expect(simulatorsApi).toHaveProperty('list')
      expect(simulatorsApi).toHaveProperty('get')
      expect(simulatorsApi).toHaveProperty('create')
      expect(simulatorsApi).toHaveProperty('update')
      expect(simulatorsApi).toHaveProperty('delete')
    })
  })

  describe('portsApi', () => {
    it('should export portsApi with correct methods', async () => {
      vi.resetModules()
      const { portsApi } = await import('@/services/api')

      expect(portsApi).toHaveProperty('getStatus')
      expect(portsApi).toHaveProperty('enable')
      expect(portsApi).toHaveProperty('disable')
      expect(portsApi).toHaveProperty('forceEnable')
      expect(portsApi).toHaveProperty('forceDisable')
      expect(portsApi).toHaveProperty('listAssignments')
    })
  })

  describe('switchesApi', () => {
    it('should export switchesApi with correct methods', async () => {
      vi.resetModules()
      const { switchesApi } = await import('@/services/api')

      expect(switchesApi).toHaveProperty('list')
      expect(switchesApi).toHaveProperty('get')
      expect(switchesApi).toHaveProperty('create')
      expect(switchesApi).toHaveProperty('update')
      expect(switchesApi).toHaveProperty('delete')
      expect(switchesApi).toHaveProperty('test')
    })
  })

  describe('usersApi', () => {
    it('should export usersApi with correct methods', async () => {
      vi.resetModules()
      const { usersApi } = await import('@/services/api')

      expect(usersApi).toHaveProperty('list')
      expect(usersApi).toHaveProperty('get')
      expect(usersApi).toHaveProperty('create')
      expect(usersApi).toHaveProperty('update')
      expect(usersApi).toHaveProperty('delete')
    })
  })

  describe('logsApi', () => {
    it('should export logsApi with correct methods', async () => {
      vi.resetModules()
      const { logsApi } = await import('@/services/api')

      expect(logsApi).toHaveProperty('list')
      expect(logsApi).toHaveProperty('clear')
    })
  })

  describe('systemApi', () => {
    it('should export systemApi with correct methods', async () => {
      vi.resetModules()
      const { systemApi } = await import('@/services/api')

      expect(systemApi).toHaveProperty('health')
      expect(systemApi).toHaveProperty('info')
      expect(systemApi).toHaveProperty('ssl')
      expect(systemApi).toHaveProperty('renewSsl')
    })
  })

  describe('discoveryApi', () => {
    it('should export discoveryApi with correct methods', async () => {
      vi.resetModules()
      const { discoveryApi } = await import('@/services/api')

      expect(discoveryApi).toHaveProperty('scanSwitch')
      expect(discoveryApi).toHaveProperty('getSwitchPorts')
      expect(discoveryApi).toHaveProperty('getAllPorts')
      expect(discoveryApi).toHaveProperty('assignPort')
      expect(discoveryApi).toHaveProperty('releasePort')
      expect(discoveryApi).toHaveProperty('refreshPort')
    })
  })
})
