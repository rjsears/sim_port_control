import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import SimulatorsManageView from '@/views/admin/SimulatorsManageView.vue'

// Mock the api module
vi.mock('@/services/api', () => ({
  simulatorsApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn()
  }
}))

import { simulatorsApi } from '@/services/api'

describe('SimulatorsManageView', () => {
  let router
  let pinia

  const mockSimulators = [
    {
      id: 1,
      name: 'Citation CJ3 Full Flight Simulator',
      short_name: 'CJ3',
      icon_path: '/icons/cj3.png',
      port_assignments: [{ id: 1 }, { id: 2 }]
    },
    {
      id: 2,
      name: 'Citation Latitude',
      short_name: 'CL350',
      icon_path: '/icons/cl350.png',
      port_assignments: []
    }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/admin/simulators', name: 'admin-simulators', component: SimulatorsManageView },
        { path: '/admin', name: 'admin', component: { template: '<div>Admin</div>' } }
      ]
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mountComponent(options = {}) {
    return mount(SimulatorsManageView, {
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

  it('should display Simulator Management title', async () => {
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: [] } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Simulator Management')
  })

  it('should show loading spinner initially', async () => {
    simulatorsApi.list.mockImplementationOnce(() => new Promise(() => {}))

    const wrapper = mountComponent()

    expect(wrapper.find('.spinner').exists()).toBe(true)
  })

  it('should display simulators as cards', async () => {
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Citation CJ3 Full Flight Simulator')
    expect(wrapper.text()).toContain('Citation Latitude')
    expect(wrapper.text()).toContain('CJ3')
    expect(wrapper.text()).toContain('CL350')
  })

  it('should show port count for each simulator', async () => {
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('2 ports configured')
    expect(wrapper.text()).toContain('0 ports configured')
  })

  it('should show Add Simulator button', async () => {
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Add Simulator')
  })

  it('should open add modal when Add Simulator clicked', async () => {
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    const addButton = wrapper.find('.btn-primary')
    await addButton.trigger('click')

    expect(wrapper.text()).toContain('Add Simulator')
    expect(wrapper.findAll('input').length).toBeGreaterThan(0)
  })

  it('should call create API when adding simulator', async () => {
    simulatorsApi.list.mockResolvedValue({ data: { simulators: mockSimulators } })
    simulatorsApi.create.mockResolvedValueOnce({})

    const wrapper = mountComponent()
    await flushPromises()

    // Open add modal
    const addButton = wrapper.find('.btn-primary')
    await addButton.trigger('click')

    // Fill form
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('New Simulator')
    await inputs[1].setValue('NS1')

    // Submit
    const createButton = wrapper.findAll('.btn-primary')[1]
    await createButton.trigger('click')
    await flushPromises()

    expect(simulatorsApi.create).toHaveBeenCalled()
  })

  it('should open edit modal when edit button clicked', async () => {
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    // Click edit button
    const editButtons = wrapper.findAll('button[title="Edit"]')
    await editButtons[0].trigger('click')

    expect(wrapper.text()).toContain('Edit Simulator')
  })

  it('should populate form with simulator data when editing', async () => {
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    // Open edit modal for first simulator
    const editButtons = wrapper.findAll('button[title="Edit"]')
    await editButtons[0].trigger('click')

    // Check that form is populated
    const nameInput = wrapper.findAll('input')[0]
    expect(nameInput.element.value).toBe('Citation CJ3 Full Flight Simulator')
  })

  it('should call update API when saving simulator', async () => {
    simulatorsApi.list.mockResolvedValue({ data: { simulators: mockSimulators } })
    simulatorsApi.update.mockResolvedValueOnce({})

    const wrapper = mountComponent()
    await flushPromises()

    // Open edit modal
    const editButtons = wrapper.findAll('button[title="Edit"]')
    await editButtons[0].trigger('click')

    // Change name
    const nameInput = wrapper.find('input[type="text"]')
    await nameInput.setValue('Updated Simulator')

    // Save
    const saveButton = wrapper.findAll('.btn-primary')[1]
    await saveButton.trigger('click')
    await flushPromises()

    expect(simulatorsApi.update).toHaveBeenCalled()
  })

  it('should open delete modal when delete button clicked', async () => {
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    // Click delete button
    const deleteButtons = wrapper.findAll('button[title="Delete"]')
    await deleteButtons[0].trigger('click')

    expect(wrapper.text()).toContain('Delete Simulator')
    expect(wrapper.text()).toContain('Are you sure you want to delete')
  })

  it('should warn about port assignments when deleting', async () => {
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    const deleteButtons = wrapper.findAll('button[title="Delete"]')
    await deleteButtons[0].trigger('click')

    expect(wrapper.text()).toContain('remove all port assignments')
  })

  it('should call delete API when confirming delete', async () => {
    simulatorsApi.list.mockResolvedValue({ data: { simulators: mockSimulators } })
    simulatorsApi.delete.mockResolvedValueOnce({})

    const wrapper = mountComponent()
    await flushPromises()

    // Open delete modal
    const deleteButtons = wrapper.findAll('button[title="Delete"]')
    await deleteButtons[0].trigger('click')

    // Confirm delete
    const confirmButton = wrapper.find('.bg-red-600')
    await confirmButton.trigger('click')
    await flushPromises()

    expect(simulatorsApi.delete).toHaveBeenCalledWith(1)
  })

  it('should show error message on API failure', async () => {
    simulatorsApi.list.mockResolvedValue({ data: { simulators: mockSimulators } })
    simulatorsApi.create.mockRejectedValueOnce({
      response: { data: { detail: 'Short name already exists' } }
    })

    const wrapper = mountComponent()
    await flushPromises()

    // Open add modal
    const addButton = wrapper.find('.btn-primary')
    await addButton.trigger('click')

    // Fill form
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('New Sim')
    await inputs[1].setValue('CJ3')

    // Submit
    const createButton = wrapper.findAll('.btn-primary')[1]
    await createButton.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Short name already exists')
  })

  it('should have back button', async () => {
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: [] } })

    const wrapper = mountComponent()
    await flushPromises()

    const backButton = wrapper.find('button.btn-secondary')
    expect(backButton.exists()).toBe(true)
  })
})
