import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import SimulatorDetailView from '@/views/SimulatorDetailView.vue'
import { useSimulatorsStore } from '@/stores/simulators'
import { useAuthStore } from '@/stores/auth'

// Mock the api module
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn()
  }
}))

import api from '@/services/api'

describe('SimulatorDetailView', () => {
  let router
  let pinia

  const mockSimulator = {
    id: 1,
    name: 'Citation CJ3 Full Flight Simulator',
    short_name: 'CJ3',
    has_active_ports: false,
    port_assignments: [
      {
        id: 1,
        port_number: 'Gi1/0/1',
        status: 'assigned',
        seconds_remaining: 0,
        force_enabled: false
      },
      {
        id: 2,
        port_number: 'Gi1/0/2',
        status: 'enabled',
        seconds_remaining: 3600,
        force_enabled: false
      }
    ]
  }

  beforeEach(() => {
    vi.useFakeTimers()
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/simulator/:id', name: 'simulator', component: SimulatorDetailView },
        { path: '/', name: 'home', component: { template: '<div>Home</div>' } }
      ]
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  async function mountComponent(simulatorId = 1, options = {}) {
    router.push(`/simulator/${simulatorId}`)
    await router.isReady()

    return mount(SimulatorDetailView, {
      global: {
        plugins: [pinia, router],
        stubs: {
          Teleport: true
        },
        ...options.global
      },
      ...options
    })
  }

  it('should display simulator name', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('CJ3')
  })

  it('should display port assignments', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Gi1/0/1')
    expect(wrapper.text()).toContain('Gi1/0/2')
  })

  it('should show back button', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    const backButton = wrapper.find('button')
    expect(backButton.exists()).toBe(true)
  })

  it('should display time remaining for enabled port', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    // Should show time remaining (1 hour = 3600 seconds)
    expect(wrapper.text()).toContain('1h')
  })

  it('should show port status for each port', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    // Check that both port buttons are rendered (Enable for assigned, Disable for enabled)
    expect(wrapper.text()).toContain('Enable')
    expect(wrapper.text()).toContain('Disable')
  })

  it('should show Manage Ports link for admin users', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'admin', role: 'admin' }

    const wrapper = await mountComponent()
    await flushPromises()

    // Admin should see Manage Ports link
    expect(wrapper.text()).toContain('Manage Ports')
  })

  it('should not show Manage Ports link for regular users', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    expect(wrapper.text()).not.toContain('Manage Ports')
  })

  it('should show Help link', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    const helpLink = wrapper.find('a[href="/manual/index.html"]')
    expect(helpLink.exists()).toBe(true)
  })

  it('should display enable button for assigned ports', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Enable')
  })

  it('should display disable button for enabled ports', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Disable')
  })

  it('should show force enable option for admins', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'admin', role: 'admin' }

    const wrapper = await mountComponent()
    await flushPromises()

    // Admin should see the bolt icon for force enable
    expect(wrapper.findAll('.h-5.w-5').length).toBeGreaterThan(0)
  })

  it('should show locked indicator for force-enabled ports', async () => {
    const simulatorWithLockedPort = {
      ...mockSimulator,
      port_assignments: [
        {
          id: 1,
          port_number: 'Gi1/0/1',
          status: 'enabled',
          seconds_remaining: 0,
          force_enabled: true,
          force_enabled_reason: 'Maintenance'
        }
      ]
    }

    api.get.mockResolvedValueOnce({ data: simulatorWithLockedPort })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Always On')
  })

  it('should show error message for ports in error state', async () => {
    const simulatorWithError = {
      ...mockSimulator,
      port_assignments: [
        {
          id: 1,
          port_number: 'Gi1/0/1',
          status: 'error',
          seconds_remaining: 0,
          force_enabled: false,
          error_message: 'Connection timeout'
        }
      ]
    }

    api.get.mockResolvedValueOnce({ data: simulatorWithError })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Connection timeout')
  })

  it('should show default error message when no error_message provided', async () => {
    const simulatorWithError = {
      ...mockSimulator,
      port_assignments: [
        {
          id: 1,
          port_number: 'Gi1/0/1',
          status: 'error',
          seconds_remaining: 0,
          force_enabled: false
        }
      ]
    }

    api.get.mockResolvedValueOnce({ data: simulatorWithError })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Error occurred')
  })

  it('should show Retry button for ports in error state', async () => {
    const simulatorWithError = {
      ...mockSimulator,
      port_assignments: [
        {
          id: 1,
          port_number: 'Gi1/0/1',
          status: 'error',
          seconds_remaining: 0,
          force_enabled: false
        }
      ]
    }

    api.get.mockResolvedValueOnce({ data: simulatorWithError })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Retry')
  })

  it('should show no ports message when simulator has no ports', async () => {
    const simulatorNoPorts = {
      ...mockSimulator,
      port_assignments: []
    }

    api.get.mockResolvedValueOnce({ data: simulatorNoPorts })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('No ports configured')
  })

  it('should display VLAN information', async () => {
    const simulatorWithVlan = {
      ...mockSimulator,
      port_assignments: [
        {
          id: 1,
          port_number: 'Gi1/0/1',
          status: 'enabled',
          seconds_remaining: 3600,
          force_enabled: false,
          switch_name: 'Main Switch',
          vlan: 100
        }
      ]
    }

    api.get.mockResolvedValueOnce({ data: simulatorWithVlan })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('VLAN 100')
    expect(wrapper.text()).toContain('Main Switch')
  })

  it('should open confirmation modal when Enable button is clicked', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    // Click Enable button
    const enableButton = wrapper.findAll('button').find(b => b.text() === 'Enable')
    await enableButton.trigger('click')

    expect(wrapper.text()).toContain('Enable Internet Access')
    expect(wrapper.text()).toContain('Duration')
  })

  it('should open confirmation modal when Disable button is clicked', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    // Click Disable button
    const disableButton = wrapper.findAll('button').find(b => b.text() === 'Disable')
    await disableButton.trigger('click')

    expect(wrapper.text()).toContain('Disable Internet Access')
    expect(wrapper.text()).toContain('Deactivate internet access')
  })

  it('should show duration selector in enable modal', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    // Click Enable button
    const enableButton = wrapper.findAll('button').find(b => b.text() === 'Enable')
    await enableButton.trigger('click')

    // Check for duration options
    expect(wrapper.text()).toContain('1 hour')
    expect(wrapper.text()).toContain('2 hours')
    expect(wrapper.text()).toContain('4 hours')
  })

  it('should show extended timeout options for admin users', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'admin', role: 'admin' }

    const wrapper = await mountComponent()
    await flushPromises()

    // Click Enable button
    const enableButton = wrapper.findAll('button').find(b => b.text() === 'Enable')
    await enableButton.trigger('click')

    // Admin should see extended options
    expect(wrapper.text()).toContain('1 week')
    expect(wrapper.text()).toContain('Always On')
  })

  it('should format time remaining correctly for minutes and seconds', async () => {
    const simulatorWithShortTime = {
      ...mockSimulator,
      port_assignments: [
        {
          id: 1,
          port_number: 'Gi1/0/1',
          status: 'enabled',
          seconds_remaining: 125, // 2 minutes 5 seconds
          force_enabled: false
        }
      ]
    }

    api.get.mockResolvedValueOnce({ data: simulatorWithShortTime })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('2:05')
  })

  it('should close modal when Cancel is clicked', async () => {
    api.get.mockResolvedValueOnce({ data: mockSimulator })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser', role: 'user' }

    const wrapper = await mountComponent()
    await flushPromises()

    // Open modal
    const enableButton = wrapper.findAll('button').find(b => b.text() === 'Enable')
    await enableButton.trigger('click')

    expect(wrapper.text()).toContain('Enable Internet Access')

    // Click Cancel
    const cancelButton = wrapper.findAll('button').find(b => b.text() === 'Cancel')
    await cancelButton.trigger('click')

    // Modal should be closed - check that Duration selector is gone
    expect(wrapper.text()).not.toContain('Enable Internet Access')
  })
})
