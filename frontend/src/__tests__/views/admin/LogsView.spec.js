import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import LogsView from '@/views/admin/LogsView.vue'

// Mock the api module
vi.mock('@/services/api', () => ({
  logsApi: {
    list: vi.fn(),
    clear: vi.fn()
  }
}))

import { logsApi } from '@/services/api'

describe('LogsView', () => {
  let router
  let pinia

  const mockLogs = [
    {
      id: 1,
      timestamp: '2024-01-15T10:30:00Z',
      username: 'admin',
      action: 'enable',
      simulator_name: 'CL350',
      port_number: 'Port 1',
      details: { reason: 'Test reason' }
    },
    {
      id: 2,
      timestamp: '2024-01-15T11:00:00Z',
      username: 'simtech1',
      action: 'disable',
      simulator_name: 'CJ3',
      port_number: 'Port 2',
      details: null
    },
    {
      id: 3,
      timestamp: '2024-01-15T11:30:00Z',
      username: 'admin',
      action: 'force_enable',
      simulator_name: 'CL350',
      port_number: 'Port 3',
      details: { reason: 'Maintenance' }
    }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/admin/logs', name: 'admin-logs', component: LogsView },
        { path: '/admin', name: 'admin', component: { template: '<div>Admin</div>' } }
      ]
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mountComponent(options = {}) {
    return mount(LogsView, {
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

  it('should display Activity Logs title', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: [] } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Activity Logs')
  })

  it('should show loading spinner initially', async () => {
    logsApi.list.mockImplementationOnce(() => new Promise(() => {}))

    const wrapper = mountComponent()

    expect(wrapper.find('.spinner').exists()).toBe(true)
  })

  it('should display logs in table', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: mockLogs } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('admin')
    expect(wrapper.text()).toContain('simtech1')
    expect(wrapper.text()).toContain('CL350')
    expect(wrapper.text()).toContain('CJ3')
  })

  it('should display table headers', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: mockLogs } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Time')
    expect(wrapper.text()).toContain('User')
    expect(wrapper.text()).toContain('Action')
    expect(wrapper.text()).toContain('Simulator')
    expect(wrapper.text()).toContain('Port')
    expect(wrapper.text()).toContain('Reason')
  })

  it('should show Clear Logs button when logs exist', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: mockLogs } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Clear Logs')
  })

  it('should not show Clear Logs button when no logs', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: [] } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).not.toContain('Clear Logs')
  })

  it('should filter logs by action', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: mockLogs } })

    const wrapper = mountComponent()
    await flushPromises()

    // Find action filter and select 'enable'
    const actionSelect = wrapper.findAll('select')[0]
    await actionSelect.setValue('enable')

    // Should only show 'enable' actions
    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(1)
  })

  it('should filter logs by user', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: mockLogs } })

    const wrapper = mountComponent()
    await flushPromises()

    // Find user filter and select 'simtech1'
    const userSelect = wrapper.findAll('select')[1]
    await userSelect.setValue('simtech1')

    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(1)
    expect(wrapper.text()).toContain('simtech1')
  })

  it('should filter logs by simulator', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: mockLogs } })

    const wrapper = mountComponent()
    await flushPromises()

    // Find simulator filter and select 'CJ3'
    const simSelect = wrapper.findAll('select')[2]
    await simSelect.setValue('CJ3')

    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(1)
    expect(wrapper.text()).toContain('CJ3')
  })

  it('should show filter count when filters active', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: mockLogs } })

    const wrapper = mountComponent()
    await flushPromises()

    const actionSelect = wrapper.findAll('select')[0]
    await actionSelect.setValue('enable')

    expect(wrapper.text()).toContain('Showing 1 of 3 logs')
  })

  it('should clear filters when Clear Filters clicked', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: mockLogs } })

    const wrapper = mountComponent()
    await flushPromises()

    // Set a filter
    const actionSelect = wrapper.findAll('select')[0]
    await actionSelect.setValue('enable')
    await flushPromises()

    // Should show 1 row
    expect(wrapper.findAll('tbody tr').length).toBe(1)

    // Click Clear Filters (should appear after setting filter)
    const clearFiltersBtn = wrapper.findAll('button').find(b => b.text().includes('Clear Filters'))
    await clearFiltersBtn.trigger('click')
    await flushPromises()

    // Should show all logs again
    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(3)
  })

  it('should show clear confirmation modal', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: mockLogs } })

    const wrapper = mountComponent()
    await flushPromises()

    // Click Clear Logs button
    const clearLogsBtn = wrapper.find('.btn-danger')
    await clearLogsBtn.trigger('click')

    expect(wrapper.text()).toContain('Clear All Logs')
    expect(wrapper.text()).toContain('Are you sure you want to delete')
  })

  it('should call clear API when confirming clear', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: mockLogs } })
    logsApi.clear.mockResolvedValueOnce({})

    const wrapper = mountComponent()
    await flushPromises()

    // Open modal
    const clearLogsBtn = wrapper.find('.btn-danger')
    await clearLogsBtn.trigger('click')

    // Find and click confirm button in modal
    const confirmBtn = wrapper.findAll('.btn-danger')[1]
    await confirmBtn.trigger('click')
    await flushPromises()

    expect(logsApi.clear).toHaveBeenCalled()
  })

  it('should display reason from log details', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: mockLogs } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Test reason')
    expect(wrapper.text()).toContain('Maintenance')
  })

  it('should have back button', async () => {
    logsApi.list.mockResolvedValueOnce({ data: { logs: [] } })

    const wrapper = mountComponent()
    await flushPromises()

    const backButton = wrapper.find('button.btn-secondary')
    expect(backButton.exists()).toBe(true)
  })
})
