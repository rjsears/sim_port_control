import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import SystemView from '@/views/admin/SystemView.vue'

// Mock the api module
vi.mock('@/services/api', () => ({
  systemApi: {
    info: vi.fn(),
    ssl: vi.fn(),
    renewSsl: vi.fn()
  }
}))

import { systemApi } from '@/services/api'

describe('SystemView', () => {
  let router
  let pinia

  const mockSystemInfo = {
    version: '1.0.0',
    uptime_seconds: 86400,
    resources: {
      cpu: { percent: 25 },
      memory: { percent: 45, used: 4000000000, total: 8000000000 },
      disk: { percent: 60, used: 50000000000, total: 100000000000 }
    },
    database: {
      simulators: 5,
      users: 3,
      switches: 2,
      port_assignments: 10
    },
    scheduler: {
      running: true,
      active_jobs: 2
    }
  }

  const mockSslInfo = {
    certificates: [
      {
        domain: 'example.com',
        issuer: "Let's Encrypt",
        valid_from: '2024-01-01',
        valid_until: '2024-04-01',
        days_until_expiry: 60
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
        { path: '/admin/system', name: 'admin-system', component: SystemView },
        { path: '/admin', name: 'admin', component: { template: '<div>Admin</div>' } }
      ]
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  function mountComponent(options = {}) {
    return mount(SystemView, {
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

  it('should display System title', async () => {
    systemApi.info.mockResolvedValueOnce({ data: mockSystemInfo })
    systemApi.ssl.mockResolvedValueOnce({ data: mockSslInfo })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('System')
  })

  it('should show loading spinner initially', async () => {
    systemApi.info.mockImplementationOnce(() => new Promise(() => {}))
    systemApi.ssl.mockImplementationOnce(() => new Promise(() => {}))

    const wrapper = mountComponent()

    expect(wrapper.find('.spinner').exists()).toBe(true)
  })

  it('should display system version', async () => {
    systemApi.info.mockResolvedValueOnce({ data: mockSystemInfo })
    systemApi.ssl.mockResolvedValueOnce({ data: mockSslInfo })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('1.0.0')
  })

  it('should display CPU usage', async () => {
    systemApi.info.mockResolvedValueOnce({ data: mockSystemInfo })
    systemApi.ssl.mockResolvedValueOnce({ data: mockSslInfo })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('25.0%')
  })

  it('should display memory usage', async () => {
    systemApi.info.mockResolvedValueOnce({ data: mockSystemInfo })
    systemApi.ssl.mockResolvedValueOnce({ data: mockSslInfo })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('45.0%')
  })

  it('should display disk usage', async () => {
    systemApi.info.mockResolvedValueOnce({ data: mockSystemInfo })
    systemApi.ssl.mockResolvedValueOnce({ data: mockSslInfo })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('60.0%')
  })

  it('should display database counts', async () => {
    systemApi.info.mockResolvedValueOnce({ data: mockSystemInfo })
    systemApi.ssl.mockResolvedValueOnce({ data: mockSslInfo })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('5') // simulators
    expect(wrapper.text()).toContain('3') // users
  })

  it('should display SSL certificate info', async () => {
    systemApi.info.mockResolvedValueOnce({ data: mockSystemInfo })
    systemApi.ssl.mockResolvedValueOnce({ data: mockSslInfo })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('example.com')
    expect(wrapper.text()).toContain("Let's Encrypt")
  })

  it('should show Refresh button', async () => {
    systemApi.info.mockResolvedValueOnce({ data: mockSystemInfo })
    systemApi.ssl.mockResolvedValueOnce({ data: mockSslInfo })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Refresh')
  })

  it('should refresh data when Refresh clicked', async () => {
    systemApi.info.mockResolvedValue({ data: mockSystemInfo })
    systemApi.ssl.mockResolvedValue({ data: mockSslInfo })

    const wrapper = mountComponent()
    await flushPromises()

    // Clear mock call counts
    systemApi.info.mockClear()
    systemApi.ssl.mockClear()

    // Click refresh
    const refreshButton = wrapper.findAll('button').find(b => b.text().includes('Refresh'))
    await refreshButton.trigger('click')
    await flushPromises()

    expect(systemApi.info).toHaveBeenCalled()
    expect(systemApi.ssl).toHaveBeenCalled()
  })

  it('should show days until SSL expiry', async () => {
    systemApi.info.mockResolvedValueOnce({ data: mockSystemInfo })
    systemApi.ssl.mockResolvedValueOnce({ data: mockSslInfo })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('60')
  })

  it('should have back button', async () => {
    systemApi.info.mockResolvedValueOnce({ data: mockSystemInfo })
    systemApi.ssl.mockResolvedValueOnce({ data: mockSslInfo })

    const wrapper = mountComponent()
    await flushPromises()

    const backButton = wrapper.find('button.btn-secondary')
    expect(backButton.exists()).toBe(true)
  })

  it('should show scheduler status', async () => {
    systemApi.info.mockResolvedValueOnce({ data: mockSystemInfo })
    systemApi.ssl.mockResolvedValueOnce({ data: mockSslInfo })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('2') // active jobs
  })

  it('should show warning for SSL expiring soon', async () => {
    const expiringSslInfo = {
      certificates: [{
        domain: 'example.com',
        issuer: "Let's Encrypt",
        valid_from: '2024-01-01',
        valid_until: '2024-01-20',
        days_until_expiry: 15
      }]
    }

    systemApi.info.mockResolvedValueOnce({ data: mockSystemInfo })
    systemApi.ssl.mockResolvedValueOnce({ data: expiringSslInfo })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('15')
  })
})
