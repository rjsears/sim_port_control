/**
 * Simulators Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useSimulatorsStore = defineStore('simulators', () => {
  // State
  const simulators = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const activeSimulators = computed(() =>
    simulators.value.filter(s => s.has_active_ports)
  )

  const getSimulatorById = computed(() => (id) =>
    simulators.value.find(s => s.id === id)
  )

  // Actions
  async function fetchSimulators() {
    loading.value = true
    error.value = null

    try {
      const response = await api.get('/simulators')
      simulators.value = response.data.simulators
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to load simulators'
    } finally {
      loading.value = false
    }
  }

  async function fetchSimulator(id) {
    loading.value = true
    error.value = null

    try {
      const response = await api.get(`/simulators/${id}`)
      // Update or add to local state
      const index = simulators.value.findIndex(s => s.id === id)
      if (index >= 0) {
        simulators.value[index] = response.data
      } else {
        simulators.value.push(response.data)
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to load simulator'
      return null
    } finally {
      loading.value = false
    }
  }

  async function enablePort(portId, options = {}) {
    try {
      const response = await api.post(`/ports/${portId}/enable`, options)
      // Refresh simulators to get updated status
      await fetchSimulators()
      return response.data
    } catch (err) {
      throw new Error(err.response?.data?.detail || 'Failed to enable port')
    }
  }

  async function disablePort(portId) {
    try {
      const response = await api.post(`/ports/${portId}/disable`)
      // Refresh simulators to get updated status
      await fetchSimulators()
      return response.data
    } catch (err) {
      throw new Error(err.response?.data?.detail || 'Failed to disable port')
    }
  }

  async function forceEnablePort(portId, reason) {
    try {
      const response = await api.post(`/ports/${portId}/force-enable`, { reason })
      await fetchSimulators()
      return response.data
    } catch (err) {
      throw new Error(err.response?.data?.detail || 'Failed to force-enable port')
    }
  }

  async function forceDisablePort(portId) {
    try {
      const response = await api.post(`/ports/${portId}/force-disable`)
      await fetchSimulators()
      return response.data
    } catch (err) {
      throw new Error(err.response?.data?.detail || 'Failed to remove force-enable')
    }
  }

  return {
    simulators,
    loading,
    error,
    activeSimulators,
    getSimulatorById,
    fetchSimulators,
    fetchSimulator,
    enablePort,
    disablePort,
    forceEnablePort,
    forceDisablePort
  }
})
