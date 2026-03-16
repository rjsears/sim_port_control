import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import SwitchesView from '@/views/admin/SwitchesView.vue'

// Mock the api module
vi.mock('@/services/api', () => ({
  switchesApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    test: vi.fn()
  }
}))

import { switchesApi } from '@/services/api'

describe('SwitchesView', () => {
  let router
  let pinia

  const mockSwitches = [
    {
      id: 1,
      name: 'Main Switch',
      ip_address: '192.168.1.1',
      username: 'admin',
      device_type: 'cisco_ios',
      port_count: 5
    },
    {
      id: 2,
      name: 'Backup Switch',
      ip_address: '192.168.1.2',
      username: 'admin',
      device_type: 'cisco_ios',
      port_count: 3
    }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/admin/switches', name: 'admin-switches', component: SwitchesView },
        { path: '/admin', name: 'admin', component: { template: '<div>Admin</div>' } },
        { path: '/admin/discovered-ports', name: 'admin-discovered-ports', component: { template: '<div>Ports</div>' } }
      ]
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mountComponent(options = {}) {
    return mount(SwitchesView, {
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

  it('should display Switch Management title', async () => {
    switchesApi.list.mockResolvedValueOnce({ data: { switches: [] } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Switch Management')
  })

  it('should show loading spinner initially', async () => {
    switchesApi.list.mockImplementationOnce(() => new Promise(() => {}))

    const wrapper = mountComponent()

    expect(wrapper.find('.spinner').exists()).toBe(true)
  })

  it('should display switches as cards', async () => {
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Main Switch')
    expect(wrapper.text()).toContain('Backup Switch')
    expect(wrapper.text()).toContain('192.168.1.1')
    expect(wrapper.text()).toContain('192.168.1.2')
  })

  it('should show port count for each switch', async () => {
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('5 ports assigned')
    expect(wrapper.text()).toContain('3 ports assigned')
  })

  it('should show Add Switch button', async () => {
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Add Switch')
  })

  it('should show empty state when no switches', async () => {
    switchesApi.list.mockResolvedValueOnce({ data: { switches: [] } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('No switches configured')
    expect(wrapper.text()).toContain('Add First Switch')
  })

  it('should open add modal when Add Switch clicked', async () => {
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    const addButton = wrapper.find('.btn-primary')
    await addButton.trigger('click')

    expect(wrapper.text()).toContain('Add Switch')
    expect(wrapper.findAll('input').length).toBeGreaterThan(0)
  })

  it('should call create API when adding switch', async () => {
    switchesApi.list.mockResolvedValue({ data: { switches: mockSwitches } })
    switchesApi.create.mockResolvedValueOnce({})

    const wrapper = mountComponent()
    await flushPromises()

    // Open add modal
    const addButton = wrapper.find('.btn-primary')
    await addButton.trigger('click')

    // Fill form
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('New Switch')
    await inputs[1].setValue('192.168.1.10')
    await inputs[2].setValue('admin')
    await inputs[3].setValue('password123')

    // Submit
    const createButton = wrapper.findAll('.btn-primary')[1]
    await createButton.trigger('click')
    await flushPromises()

    expect(switchesApi.create).toHaveBeenCalled()
  })

  it('should open edit modal when edit button clicked', async () => {
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    // Click edit button (pencil icon button)
    const editButtons = wrapper.findAll('button[title="Edit"]')
    await editButtons[0].trigger('click')

    expect(wrapper.text()).toContain('Edit Switch')
  })

  it('should call update API when saving switch', async () => {
    switchesApi.list.mockResolvedValue({ data: { switches: mockSwitches } })
    switchesApi.update.mockResolvedValueOnce({})

    const wrapper = mountComponent()
    await flushPromises()

    // Open edit modal
    const editButtons = wrapper.findAll('button[title="Edit"]')
    await editButtons[0].trigger('click')

    // Change name
    const nameInput = wrapper.find('input[type="text"]')
    await nameInput.setValue('Updated Switch')

    // Save
    const saveButton = wrapper.findAll('.btn-primary')[1]
    await saveButton.trigger('click')
    await flushPromises()

    expect(switchesApi.update).toHaveBeenCalled()
  })

  it('should open delete modal when delete button clicked', async () => {
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    // Click delete button
    const deleteButtons = wrapper.findAll('button[title="Delete"]')
    await deleteButtons[0].trigger('click')

    expect(wrapper.text()).toContain('Delete Switch')
    expect(wrapper.text()).toContain('Are you sure you want to delete')
  })

  it('should call delete API when confirming delete', async () => {
    switchesApi.list.mockResolvedValue({ data: { switches: mockSwitches } })
    switchesApi.delete.mockResolvedValueOnce({})

    const wrapper = mountComponent()
    await flushPromises()

    // Open delete modal
    const deleteButtons = wrapper.findAll('button[title="Delete"]')
    await deleteButtons[0].trigger('click')

    // Confirm delete
    const confirmButton = wrapper.find('.bg-red-600')
    await confirmButton.trigger('click')
    await flushPromises()

    expect(switchesApi.delete).toHaveBeenCalledWith(1)
  })

  it('should test connection when test button clicked', async () => {
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    switchesApi.test.mockResolvedValueOnce({ data: { success: true } })

    const wrapper = mountComponent()
    await flushPromises()

    // Click test button
    const testButtons = wrapper.findAll('button[title="Test Connection"]')
    await testButtons[0].trigger('click')
    await flushPromises()

    expect(switchesApi.test).toHaveBeenCalledWith(1)
  })

  it('should show success message on successful connection test', async () => {
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    switchesApi.test.mockResolvedValueOnce({ data: { success: true } })

    const wrapper = mountComponent()
    await flushPromises()

    const testButtons = wrapper.findAll('button[title="Test Connection"]')
    await testButtons[0].trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Successfully connected')
  })

  it('should show failure message on failed connection test', async () => {
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    switchesApi.test.mockResolvedValueOnce({ data: { success: false, message: 'Connection refused' } })

    const wrapper = mountComponent()
    await flushPromises()

    const testButtons = wrapper.findAll('button[title="Test Connection"]')
    await testButtons[0].trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Connection failed')
  })

  it('should have back button', async () => {
    switchesApi.list.mockResolvedValueOnce({ data: { switches: [] } })

    const wrapper = mountComponent()
    await flushPromises()

    const backButton = wrapper.find('button.btn-secondary')
    expect(backButton.exists()).toBe(true)
  })
})
