import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSimulatorsStore } from '@/stores/simulators'

// Mock the api module
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn()
  }
}))

import api from '@/services/api'

describe('Simulators Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should have empty simulators array initially', () => {
      const store = useSimulatorsStore()
      expect(store.simulators).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })
  })

  describe('activeSimulators getter', () => {
    it('should return only simulators with active ports', () => {
      const store = useSimulatorsStore()
      store.simulators = [
        { id: 1, name: 'Sim1', has_active_ports: true },
        { id: 2, name: 'Sim2', has_active_ports: false },
        { id: 3, name: 'Sim3', has_active_ports: true }
      ]

      expect(store.activeSimulators).toHaveLength(2)
      expect(store.activeSimulators.map(s => s.id)).toEqual([1, 3])
    })

    it('should return empty array when no simulators have active ports', () => {
      const store = useSimulatorsStore()
      store.simulators = [
        { id: 1, name: 'Sim1', has_active_ports: false }
      ]

      expect(store.activeSimulators).toHaveLength(0)
    })
  })

  describe('getSimulatorById getter', () => {
    it('should find simulator by ID', () => {
      const store = useSimulatorsStore()
      store.simulators = [
        { id: 1, name: 'Sim1' },
        { id: 2, name: 'Sim2' },
        { id: 3, name: 'Sim3' }
      ]

      const result = store.getSimulatorById(2)
      expect(result).toEqual({ id: 2, name: 'Sim2' })
    })

    it('should return undefined for non-existent ID', () => {
      const store = useSimulatorsStore()
      store.simulators = [{ id: 1, name: 'Sim1' }]

      const result = store.getSimulatorById(999)
      expect(result).toBeUndefined()
    })
  })

  describe('fetchSimulators', () => {
    it('should fetch and store simulators', async () => {
      const mockSimulators = [
        { id: 1, name: 'CL350' },
        { id: 2, name: 'CJ3' }
      ]
      api.get.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

      const store = useSimulatorsStore()
      await store.fetchSimulators()

      expect(api.get).toHaveBeenCalledWith('/simulators')
      expect(store.simulators).toEqual(mockSimulators)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should set loading during fetch', async () => {
      let resolvePromise
      api.get.mockImplementationOnce(() => new Promise(resolve => { resolvePromise = resolve }))

      const store = useSimulatorsStore()
      const fetchPromise = store.fetchSimulators()

      expect(store.loading).toBe(true)

      resolvePromise({ data: { simulators: [] } })
      await fetchPromise

      expect(store.loading).toBe(false)
    })

    it('should handle fetch error', async () => {
      api.get.mockRejectedValueOnce({
        response: { data: { detail: 'Server error' } }
      })

      const store = useSimulatorsStore()
      await store.fetchSimulators()

      expect(store.error).toBe('Server error')
      expect(store.simulators).toEqual([])
    })

    it('should use default error message on network failure', async () => {
      api.get.mockRejectedValueOnce(new Error('Network error'))

      const store = useSimulatorsStore()
      await store.fetchSimulators()

      expect(store.error).toBe('Failed to load simulators')
    })
  })

  describe('fetchSimulator', () => {
    it('should fetch a single simulator and add to state', async () => {
      const mockSimulator = { id: 1, name: 'CL350', ports: [] }
      api.get.mockResolvedValueOnce({ data: mockSimulator })

      const store = useSimulatorsStore()
      const result = await store.fetchSimulator(1)

      expect(api.get).toHaveBeenCalledWith('/simulators/1')
      expect(result).toEqual(mockSimulator)
      expect(store.simulators).toContainEqual(mockSimulator)
    })

    it('should update existing simulator in state', async () => {
      const store = useSimulatorsStore()
      store.simulators = [
        { id: 1, name: 'Old Name', ports: [] }
      ]

      const updatedSimulator = { id: 1, name: 'New Name', ports: [{ id: 1 }] }
      api.get.mockResolvedValueOnce({ data: updatedSimulator })

      await store.fetchSimulator(1)

      expect(store.simulators).toHaveLength(1)
      expect(store.simulators[0].name).toBe('New Name')
      expect(store.simulators[0].ports).toHaveLength(1)
    })

    it('should return null on error', async () => {
      api.get.mockRejectedValueOnce({
        response: { data: { detail: 'Not found' } }
      })

      const store = useSimulatorsStore()
      const result = await store.fetchSimulator(999)

      expect(result).toBeNull()
      expect(store.error).toBe('Not found')
    })
  })

  describe('enablePort', () => {
    it('should enable port and refresh simulators', async () => {
      api.post.mockResolvedValueOnce({ data: { success: true } })
      api.get.mockResolvedValueOnce({ data: { simulators: [] } })

      const store = useSimulatorsStore()
      const result = await store.enablePort(1, { timeout_hours: 4 })

      expect(api.post).toHaveBeenCalledWith('/ports/1/enable', { timeout_hours: 4 })
      expect(result).toEqual({ success: true })
    })

    it('should throw error on failure', async () => {
      api.post.mockRejectedValueOnce({
        response: { data: { detail: 'Port not found' } }
      })

      const store = useSimulatorsStore()
      await expect(store.enablePort(999)).rejects.toThrow('Port not found')
    })
  })

  describe('disablePort', () => {
    it('should disable port and refresh simulators', async () => {
      api.post.mockResolvedValueOnce({ data: { success: true } })
      api.get.mockResolvedValueOnce({ data: { simulators: [] } })

      const store = useSimulatorsStore()
      const result = await store.disablePort(1)

      expect(api.post).toHaveBeenCalledWith('/ports/1/disable')
      expect(result).toEqual({ success: true })
    })

    it('should throw error on failure', async () => {
      api.post.mockRejectedValueOnce({
        response: { data: { detail: 'Failed to disable' } }
      })

      const store = useSimulatorsStore()
      await expect(store.disablePort(1)).rejects.toThrow('Failed to disable')
    })
  })

  describe('forceEnablePort', () => {
    it('should force enable port with reason', async () => {
      api.post.mockResolvedValueOnce({ data: { success: true } })
      api.get.mockResolvedValueOnce({ data: { simulators: [] } })

      const store = useSimulatorsStore()
      const result = await store.forceEnablePort(1, 'Software update')

      expect(api.post).toHaveBeenCalledWith('/ports/1/force-enable', { reason: 'Software update' })
      expect(result).toEqual({ success: true })
    })
  })

  describe('forceDisablePort', () => {
    it('should force disable port', async () => {
      api.post.mockResolvedValueOnce({ data: { success: true } })
      api.get.mockResolvedValueOnce({ data: { simulators: [] } })

      const store = useSimulatorsStore()
      const result = await store.forceDisablePort(1)

      expect(api.post).toHaveBeenCalledWith('/ports/1/force-disable')
      expect(result).toEqual({ success: true })
    })
  })
})
