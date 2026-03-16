import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import PortsView from '@/views/admin/PortsView.vue'

// Mock the api module
vi.mock('@/services/api', () => ({
  portsApi: {
    listAssignments: vi.fn(),
    updateAssignment: vi.fn()
  },
  simulatorsApi: {
    list: vi.fn()
  },
  switchesApi: {
    list: vi.fn()
  },
  discoveryApi: {
    getSwitchPorts: vi.fn(),
    scanSwitch: vi.fn(),
    assignPort: vi.fn(),
    releasePort: vi.fn()
  }
}))

import { portsApi, simulatorsApi, switchesApi, discoveryApi } from '@/services/api'

describe('PortsView', () => {
  let router
  let pinia

  const mockPortAssignments = [
    {
      id: 1,
      port_number: 'Gi1/0/1',
      simulator_id: 1,
      simulator_name: 'CJ3',
      switch_id: 1,
      switch_name: 'Main Switch',
      vlan: 30,
      timeout_hours: 4,
      status: 'assigned'
    },
    {
      id: 2,
      port_number: 'Gi1/0/2',
      simulator_id: 2,
      simulator_name: 'CL350',
      switch_id: 1,
      switch_name: 'Main Switch',
      vlan: 40,
      timeout_hours: 8,
      status: 'enabled'
    }
  ]

  const mockSimulators = [
    { id: 1, name: 'Citation CJ3', short_name: 'CJ3' },
    { id: 2, name: 'Citation Latitude', short_name: 'CL350' }
  ]

  const mockSwitches = [
    { id: 1, name: 'Main Switch' },
    { id: 2, name: 'Backup Switch' }
  ]

  const mockAvailablePorts = [
    { id: 10, port_number: 'Gi1/0/10', status: 'available' },
    { id: 11, port_number: 'Gi1/0/11', status: 'available' }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/admin/ports', name: 'admin-ports', component: PortsView },
        { path: '/admin', name: 'admin', component: { template: '<div>Admin</div>' } }
      ]
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mountComponent(options = {}) {
    return mount(PortsView, {
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

  it('should display Port Assignments title', async () => {
    portsApi.listAssignments.mockResolvedValueOnce({ data: { port_assignments: [] } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Port Assignments')
  })

  it('should show loading spinner initially', async () => {
    portsApi.listAssignments.mockImplementationOnce(() => new Promise(() => {}))
    simulatorsApi.list.mockImplementationOnce(() => new Promise(() => {}))
    switchesApi.list.mockImplementationOnce(() => new Promise(() => {}))

    const wrapper = mountComponent()

    expect(wrapper.find('.spinner').exists()).toBe(true)
  })

  it('should display port assignments in table', async () => {
    portsApi.listAssignments.mockResolvedValueOnce({ data: { port_assignments: mockPortAssignments } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Gi1/0/1')
    expect(wrapper.text()).toContain('Gi1/0/2')
    expect(wrapper.text()).toContain('CJ3')
    expect(wrapper.text()).toContain('CL350')
  })

  it('should display VLAN info', async () => {
    portsApi.listAssignments.mockResolvedValueOnce({ data: { port_assignments: mockPortAssignments } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('30')
    expect(wrapper.text()).toContain('40')
  })

  it('should display timeout hours', async () => {
    portsApi.listAssignments.mockResolvedValueOnce({ data: { port_assignments: mockPortAssignments } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('4')
    expect(wrapper.text()).toContain('8')
  })

  it('should show Add Assignment button', async () => {
    portsApi.listAssignments.mockResolvedValueOnce({ data: { port_assignments: mockPortAssignments } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Add Assignment')
  })

  it('should open add modal when Add Assignment clicked', async () => {
    portsApi.listAssignments.mockResolvedValueOnce({ data: { port_assignments: mockPortAssignments } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    const addButton = wrapper.find('.btn-primary')
    await addButton.trigger('click')

    expect(wrapper.text()).toContain('Add Port Assignment')
  })

  it('should open edit modal when edit button clicked', async () => {
    portsApi.listAssignments.mockResolvedValueOnce({ data: { port_assignments: mockPortAssignments } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    // Click edit button (blue pencil icon button - first in row)
    const editButtons = wrapper.findAll('button.text-blue-600')
    await editButtons[0].trigger('click')

    expect(wrapper.text()).toContain('Edit Port Assignment')
  })

  it('should call update API when saving changes', async () => {
    portsApi.listAssignments.mockResolvedValue({ data: { port_assignments: mockPortAssignments } })
    simulatorsApi.list.mockResolvedValue({ data: { simulators: mockSimulators } })
    switchesApi.list.mockResolvedValue({ data: { switches: mockSwitches } })
    portsApi.updateAssignment.mockResolvedValueOnce({})

    const wrapper = mountComponent()
    await flushPromises()

    // Open edit modal (blue pencil button)
    const editButtons = wrapper.findAll('button.text-blue-600')
    await editButtons[0].trigger('click')

    // Find and click save button
    const saveButton = wrapper.findAll('.btn-primary')[1]
    await saveButton.trigger('click')
    await flushPromises()

    expect(portsApi.updateAssignment).toHaveBeenCalled()
  })

  it('should open delete modal when delete button clicked', async () => {
    portsApi.listAssignments.mockResolvedValueOnce({ data: { port_assignments: mockPortAssignments } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    // Click delete button (red trash icon button)
    const deleteButtons = wrapper.findAll('button.text-red-600')
    await deleteButtons[0].trigger('click')

    expect(wrapper.text()).toContain('Delete Port Assignment')
  })

  it('should call releasePort API when confirming delete', async () => {
    portsApi.listAssignments.mockResolvedValue({ data: { port_assignments: mockPortAssignments } })
    simulatorsApi.list.mockResolvedValue({ data: { simulators: mockSimulators } })
    switchesApi.list.mockResolvedValue({ data: { switches: mockSwitches } })
    discoveryApi.releasePort.mockResolvedValueOnce({})

    const wrapper = mountComponent()
    await flushPromises()

    // Open delete modal (red trash button)
    const deleteButtons = wrapper.findAll('button.text-red-600')
    await deleteButtons[0].trigger('click')
    await flushPromises()

    // Confirm delete - find button with Delete text in modal
    const confirmButton = wrapper.findAll('button').find(b => b.text() === 'Delete')
    await confirmButton.trigger('click')
    await flushPromises()

    expect(discoveryApi.releasePort).toHaveBeenCalledWith(1)
  })

  it('should fetch available ports when switch is selected', async () => {
    portsApi.listAssignments.mockResolvedValueOnce({ data: { port_assignments: mockPortAssignments } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    discoveryApi.getSwitchPorts.mockResolvedValueOnce({ data: { ports: mockAvailablePorts } })

    const wrapper = mountComponent()
    await flushPromises()

    // Open add modal
    const addButton = wrapper.findAll('button').find(b => b.text().includes('Add Assignment'))
    await addButton.trigger('click')
    await flushPromises()

    // Select a switch (second select in modal - first is simulator)
    const selects = wrapper.findAll('select')
    // Find the switch select (second one, after simulator)
    await selects[1].setValue('1')
    await flushPromises()

    expect(discoveryApi.getSwitchPorts).toHaveBeenCalled()
  })

  it('should show error on API failure', async () => {
    portsApi.listAssignments.mockResolvedValue({ data: { port_assignments: mockPortAssignments } })
    simulatorsApi.list.mockResolvedValue({ data: { simulators: mockSimulators } })
    switchesApi.list.mockResolvedValue({ data: { switches: mockSwitches } })
    portsApi.updateAssignment.mockRejectedValueOnce({
      response: { data: { detail: 'Update failed' } }
    })

    const wrapper = mountComponent()
    await flushPromises()

    // Open edit modal (blue pencil button)
    const editButtons = wrapper.findAll('button.text-blue-600')
    await editButtons[0].trigger('click')

    // Try to save
    const saveButton = wrapper.findAll('.btn-primary')[1]
    await saveButton.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Update failed')
  })

  it('should have back button', async () => {
    portsApi.listAssignments.mockResolvedValueOnce({ data: { port_assignments: [] } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })

    const wrapper = mountComponent()
    await flushPromises()

    const backButton = wrapper.find('button.btn-secondary')
    expect(backButton.exists()).toBe(true)
  })
})
