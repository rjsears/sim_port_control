import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import DiscoveredPortsView from '@/views/admin/DiscoveredPortsView.vue'

// Mock the api module
vi.mock('@/services/api', () => ({
  discoveryApi: {
    getAllPorts: vi.fn(),
    scanSwitch: vi.fn(),
    refreshPort: vi.fn(),
    assignPort: vi.fn()
  },
  switchesApi: {
    list: vi.fn()
  },
  simulatorsApi: {
    list: vi.fn()
  }
}))

import { discoveryApi, switchesApi, simulatorsApi } from '@/services/api'

describe('DiscoveredPortsView', () => {
  let router
  let pinia

  const mockPorts = [
    {
      id: 1,
      port_name: 'GigabitEthernet1/0/1',
      short_name: 'Gi1/0/1',
      status: 'available',
      switch_id: 1,
      switch_name: 'Main Switch',
      vlan: 30
    },
    {
      id: 2,
      port_name: 'GigabitEthernet1/0/2',
      short_name: 'Gi1/0/2',
      status: 'assigned',
      switch_id: 1,
      switch_name: 'Main Switch',
      assigned_simulator_name: 'CJ3',
      vlan: 30
    },
    {
      id: 3,
      port_name: 'GigabitEthernet1/0/3',
      short_name: 'Gi1/0/3',
      status: 'error',
      switch_id: 2,
      switch_name: 'Backup Switch',
      vlan: 30
    }
  ]

  const mockSwitches = [
    { id: 1, name: 'Main Switch' },
    { id: 2, name: 'Backup Switch' }
  ]

  const mockSimulators = [
    { id: 1, name: 'Citation CJ3', short_name: 'CJ3' },
    { id: 2, name: 'Citation Latitude', short_name: 'CL350' }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/admin/discovered-ports', name: 'admin-discovered-ports', component: DiscoveredPortsView },
        { path: '/admin', name: 'admin', component: { template: '<div>Admin</div>' } },
        { path: '/admin/switches', name: 'admin-switches', component: { template: '<div>Switches</div>' } }
      ]
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mountComponent(options = {}) {
    return mount(DiscoveredPortsView, {
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

  it('should display Discovered Ports title', async () => {
    discoveryApi.getAllPorts.mockResolvedValueOnce({ data: { ports: [] } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Discovered Ports')
  })

  it('should show loading spinner initially', async () => {
    discoveryApi.getAllPorts.mockImplementationOnce(() => new Promise(() => {}))
    switchesApi.list.mockImplementationOnce(() => new Promise(() => {}))
    simulatorsApi.list.mockImplementationOnce(() => new Promise(() => {}))

    const wrapper = mountComponent()

    expect(wrapper.find('.spinner').exists()).toBe(true)
  })

  it('should display ports in table', async () => {
    discoveryApi.getAllPorts.mockResolvedValueOnce({ data: { ports: mockPorts } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Gi1/0/1')
    expect(wrapper.text()).toContain('Gi1/0/2')
    expect(wrapper.text()).toContain('Gi1/0/3')
  })

  it('should display switch names', async () => {
    discoveryApi.getAllPorts.mockResolvedValueOnce({ data: { ports: mockPorts } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Main Switch')
    expect(wrapper.text()).toContain('Backup Switch')
  })

  it('should show port statistics', async () => {
    discoveryApi.getAllPorts.mockResolvedValueOnce({ data: { ports: mockPorts } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    // Total: 3, Available: 1, Assigned: 1, Error: 1
    expect(wrapper.text()).toContain('3') // total
  })

  it('should show Scan All Switches button', async () => {
    discoveryApi.getAllPorts.mockResolvedValueOnce({ data: { ports: mockPorts } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Scan All Switches')
  })

  it('should filter ports by switch', async () => {
    discoveryApi.getAllPorts.mockResolvedValueOnce({ data: { ports: mockPorts } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    // Find switch filter and select first switch
    const switchSelect = wrapper.findAll('select')[0]
    await switchSelect.setValue('1')
    await flushPromises()

    // Should only show ports from switch 1
    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(2) // 2 ports from Main Switch
  })

  it('should filter ports by status', async () => {
    discoveryApi.getAllPorts.mockResolvedValueOnce({ data: { ports: mockPorts } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    // Find status filter and select 'available'
    const statusSelect = wrapper.findAll('select')[1]
    await statusSelect.setValue('available')
    await flushPromises()

    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(1) // 1 available port
  })

  it('should show Assign button for available ports', async () => {
    discoveryApi.getAllPorts.mockResolvedValueOnce({ data: { ports: mockPorts } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Assign')
  })

  it('should open assign modal when Assign clicked', async () => {
    discoveryApi.getAllPorts.mockResolvedValueOnce({ data: { ports: mockPorts } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    // Click Assign button (in the available port row)
    const assignButtons = wrapper.findAll('button').filter(b => b.text().includes('Assign'))
    await assignButtons[0].trigger('click')

    expect(wrapper.text()).toContain('Assign Port to Simulator')
  })

  it('should call assignPort API when assigning', async () => {
    discoveryApi.getAllPorts.mockResolvedValue({ data: { ports: mockPorts } })
    switchesApi.list.mockResolvedValue({ data: { switches: mockSwitches } })
    simulatorsApi.list.mockResolvedValue({ data: { simulators: mockSimulators } })
    discoveryApi.assignPort.mockResolvedValueOnce({})

    const wrapper = mountComponent()
    await flushPromises()

    // Open assign modal - click the Assign button in the first available port row
    const assignButtons = wrapper.findAll('button').filter(b => b.text().includes('Assign'))
    await assignButtons[0].trigger('click')
    await flushPromises()

    // Select simulator from the modal (last select in the component)
    const selects = wrapper.findAll('select')
    const simulatorSelect = selects[selects.length - 1]
    await simulatorSelect.setValue('1')
    await flushPromises()

    // Find and click the Assign Port button in modal footer
    const modalButtons = wrapper.findAll('button').filter(b => b.text().includes('Assign Port'))
    const confirmButton = modalButtons[modalButtons.length - 1]
    await confirmButton.trigger('click')
    await flushPromises()

    // Should have attempted to assign
    expect(discoveryApi.assignPort).toHaveBeenCalled()
  })

  it('should scan all switches when Scan All clicked', async () => {
    discoveryApi.getAllPorts.mockResolvedValue({ data: { ports: mockPorts } })
    switchesApi.list.mockResolvedValue({ data: { switches: mockSwitches } })
    simulatorsApi.list.mockResolvedValue({ data: { simulators: mockSimulators } })
    discoveryApi.scanSwitch.mockResolvedValue({})

    const wrapper = mountComponent()
    await flushPromises()

    // Click Scan All Switches button
    const scanButton = wrapper.findAll('button').find(b => b.text().includes('Scan All Switches'))
    await scanButton.trigger('click')
    await flushPromises()

    // Should scan each switch
    expect(discoveryApi.scanSwitch).toHaveBeenCalledTimes(2)
  })

  it('should have back button', async () => {
    discoveryApi.getAllPorts.mockResolvedValueOnce({ data: { ports: [] } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    const backButton = wrapper.find('button.btn-secondary')
    expect(backButton.exists()).toBe(true)
  })

  it('should show status badges', async () => {
    discoveryApi.getAllPorts.mockResolvedValueOnce({ data: { ports: mockPorts } })
    switchesApi.list.mockResolvedValueOnce({ data: { switches: mockSwitches } })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Available')
    expect(wrapper.text()).toContain('Assigned')
    expect(wrapper.text()).toContain('Error')
  })
})
