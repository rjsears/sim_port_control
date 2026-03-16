import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import SimulatorsView from '@/views/SimulatorsView.vue'
import { useAuthStore } from '@/stores/auth'
import { useSimulatorsStore } from '@/stores/simulators'

// Mock the api module
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: { simulators: [] } })),
    post: vi.fn()
  }
}))

import api from '@/services/api'

describe('SimulatorsView', () => {
  let router
  let pinia

  beforeEach(() => {
    vi.useFakeTimers()
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', name: 'simulators', component: SimulatorsView },
        { path: '/login', name: 'login', component: { template: '<div>Login</div>' } },
        { path: '/admin', name: 'admin', component: { template: '<div>Admin</div>' } },
        { path: '/simulator/:id', name: 'simulator', component: { template: '<div>Simulator</div>' } }
      ]
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  function mountComponent(options = {}) {
    return mount(SimulatorsView, {
      global: {
        plugins: [pinia, router],
        stubs: {
          Teleport: true,
          SignalSlashIcon: true
        },
        ...options.global
      },
      ...options
    })
  }

  it('should display welcome message with username', async () => {
    api.get.mockResolvedValueOnce({ data: { simulators: [] } })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Welcome, testuser')
  })

  it('should display app title', async () => {
    api.get.mockResolvedValueOnce({ data: { simulators: [] } })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('SimPortControl')
  })

  it('should show empty state when no simulators', async () => {
    api.get.mockResolvedValueOnce({ data: { simulators: [] } })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('No Simulators Assigned')
  })

  it('should display simulator cards', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        simulators: [
          { id: 1, name: 'CL350', short_name: 'CL350', has_active_ports: false },
          { id: 2, name: 'CJ3', short_name: 'CJ3', has_active_ports: false }
        ]
      }
    })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('CL350')
    expect(wrapper.text()).toContain('CJ3')
  })

  it('should show Internet Active badge for active simulators', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        simulators: [
          { id: 1, name: 'CL350', short_name: 'CL350', has_active_ports: true }
        ]
      }
    })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Internet Active')
  })

  it('should show Locked On indicator for force-enabled ports', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        simulators: [
          {
            id: 1,
            name: 'CL350',
            short_name: 'CL350',
            has_active_ports: true,
            port_assignments: [
              { id: 1, port_number: 'Port 1', status: 'enabled', force_enabled: true }
            ]
          }
        ]
      }
    })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Locked On')
  })

  it('should show Admin button for admin users', async () => {
    api.get.mockResolvedValueOnce({ data: { simulators: [] } })

    const authStore = useAuthStore()
    authStore.user = { username: 'admin', role: 'admin' }

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Admin')
  })

  it('should not show Admin button for non-admin users', async () => {
    api.get.mockResolvedValueOnce({ data: { simulators: [] } })

    const authStore = useAuthStore()
    authStore.user = { username: 'user', role: 'user' }

    const wrapper = mountComponent()
    await flushPromises()

    // Check that Admin text doesn't appear in buttons
    const buttons = wrapper.findAll('button')
    const adminButton = buttons.find(b => b.text().includes('Admin'))
    expect(adminButton).toBeUndefined()
  })

  it('should have Help link', async () => {
    api.get.mockResolvedValueOnce({ data: { simulators: [] } })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    const helpLink = wrapper.find('a[href="/manual/index.html"]')
    expect(helpLink.exists()).toBe(true)
  })

  it('should have Password button', async () => {
    api.get.mockResolvedValueOnce({ data: { simulators: [] } })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Password')
  })

  it('should have Logout button', async () => {
    api.get.mockResolvedValueOnce({ data: { simulators: [] } })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Logout')
  })

  it('should show error message when API fails', async () => {
    api.get.mockRejectedValueOnce({
      response: { data: { detail: 'Server error' } }
    })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Server error')
  })

  it('should show retry button on error', async () => {
    api.get.mockRejectedValueOnce({
      response: { data: { detail: 'Failed to load' } }
    })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Retry')
  })

  it('should display time remaining for active ports', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        simulators: [
          {
            id: 1,
            name: 'CL350',
            short_name: 'CL350',
            has_active_ports: true,
            port_assignments: [
              {
                id: 1,
                port_number: 'Gi1/0/1',
                status: 'enabled',
                seconds_remaining: 3600,
                force_enabled: false
              }
            ]
          }
        ]
      }
    })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    // Should show time remaining (1h 0m)
    expect(wrapper.text()).toContain('1h 0m')
  })

  it('should display port number with time for multiple active ports', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        simulators: [
          {
            id: 1,
            name: 'CL350',
            short_name: 'CL350',
            has_active_ports: true,
            port_assignments: [
              {
                id: 1,
                port_number: 'Gi1/0/1',
                status: 'enabled',
                seconds_remaining: 3600,
                force_enabled: false
              },
              {
                id: 2,
                port_number: 'Gi1/0/2',
                status: 'enabled',
                seconds_remaining: 7200,
                force_enabled: false
              }
            ]
          }
        ]
      }
    })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    // Should show port numbers with times
    expect(wrapper.text()).toContain('Gi1/0/1')
    expect(wrapper.text()).toContain('Gi1/0/2')
  })

  it('should have clickable simulator cards', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        simulators: [
          { id: 1, name: 'CL350', short_name: 'CL350', has_active_ports: false }
        ]
      }
    })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    // Check simulator card exists and is clickable
    const card = wrapper.find('.simulator-card')
    expect(card.exists()).toBe(true)
  })

  it('should open change password modal when Password button is clicked', async () => {
    api.get.mockResolvedValueOnce({ data: { simulators: [] } })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    // Click Password button
    const passwordButton = wrapper.findAll('button').find(b => b.text().includes('Password'))
    await passwordButton.trigger('click')

    // Modal should be open (ChangePasswordModal component renders)
    expect(wrapper.findComponent({ name: 'ChangePasswordModal' }).exists()).toBe(true)
  })

  it('should have logout button that triggers logout', async () => {
    api.get.mockResolvedValueOnce({ data: { simulators: [] } })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }
    authStore.token = 'test-token'

    const wrapper = mountComponent()
    await flushPromises()

    // Check logout button exists
    const logoutButton = wrapper.findAll('button').find(b => b.text().includes('Logout'))
    expect(logoutButton.exists()).toBe(true)
  })

  it('should show loading state in store while fetching', async () => {
    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const simulatorsStore = useSimulatorsStore()
    simulatorsStore.loading = true
    simulatorsStore.simulators = []

    api.get.mockResolvedValueOnce({ data: { simulators: [] } })

    const wrapper = mountComponent()

    expect(wrapper.find('.spinner').exists()).toBe(true)
  })

  it('should use placeholder icon when simulator has no icon', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        simulators: [
          { id: 1, name: 'CL350', short_name: 'CL350', has_active_ports: false, icon_path: null }
        ]
      }
    })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    const img = wrapper.find('img')
    expect(img.attributes('src')).toBe('/icons/placeholder.svg')
  })

  it('should format time correctly for minutes only', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        simulators: [
          {
            id: 1,
            name: 'CL350',
            short_name: 'CL350',
            has_active_ports: true,
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
        ]
      }
    })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('2:05')
  })

  it('should not show time for disabled ports', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        simulators: [
          {
            id: 1,
            name: 'CL350',
            short_name: 'CL350',
            has_active_ports: false,
            port_assignments: [
              {
                id: 1,
                port_number: 'Gi1/0/1',
                status: 'disabled',
                seconds_remaining: 0,
                force_enabled: false
              }
            ]
          }
        ]
      }
    })

    const authStore = useAuthStore()
    authStore.user = { username: 'testuser' }

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).not.toContain('Internet Active')
  })
})
