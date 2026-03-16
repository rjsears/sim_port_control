import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import UsersView from '@/views/admin/UsersView.vue'

// Mock the api module
vi.mock('@/services/api', () => ({
  usersApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn()
  },
  simulatorsApi: {
    list: vi.fn()
  }
}))

import { usersApi, simulatorsApi } from '@/services/api'

describe('UsersView', () => {
  let router
  let pinia

  const mockUsers = [
    {
      id: 1,
      username: 'admin',
      role: 'admin',
      assigned_simulators: []
    },
    {
      id: 2,
      username: 'simtech1',
      role: 'simtech',
      assigned_simulators: [{ id: 1, short_name: 'CL350' }]
    }
  ]

  const mockSimulators = [
    { id: 1, name: 'Citation Latitude', short_name: 'CL350' },
    { id: 2, name: 'Citation CJ3', short_name: 'CJ3' }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/admin/users', name: 'admin-users', component: UsersView },
        { path: '/admin', name: 'admin', component: { template: '<div>Admin</div>' } }
      ]
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mountComponent(options = {}) {
    return mount(UsersView, {
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

  it('should display User Management title', async () => {
    usersApi.list.mockResolvedValueOnce({ data: mockUsers })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('User Management')
  })

  it('should show loading spinner initially', async () => {
    usersApi.list.mockImplementationOnce(() => new Promise(() => {}))
    simulatorsApi.list.mockImplementationOnce(() => new Promise(() => {}))

    const wrapper = mountComponent()

    expect(wrapper.find('.spinner').exists()).toBe(true)
  })

  it('should display users in table', async () => {
    usersApi.list.mockResolvedValueOnce({ data: mockUsers })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('admin')
    expect(wrapper.text()).toContain('simtech1')
  })

  it('should display table headers', async () => {
    usersApi.list.mockResolvedValueOnce({ data: mockUsers })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Username')
    expect(wrapper.text()).toContain('Role')
    expect(wrapper.text()).toContain('Assigned Simulators')
    expect(wrapper.text()).toContain('Actions')
  })

  it('should show Add User button', async () => {
    usersApi.list.mockResolvedValueOnce({ data: mockUsers })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Add User')
  })

  it('should show All Simulators for admin users', async () => {
    usersApi.list.mockResolvedValueOnce({ data: mockUsers })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('All Simulators')
  })

  it('should show assigned simulators for simtech users', async () => {
    usersApi.list.mockResolvedValueOnce({ data: mockUsers })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('CL350')
  })

  it('should open add modal when Add User clicked', async () => {
    usersApi.list.mockResolvedValueOnce({ data: mockUsers })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    const addButton = wrapper.find('.btn-primary')
    await addButton.trigger('click')

    expect(wrapper.text()).toContain('Add User')
    expect(wrapper.findAll('input[type="text"]').length).toBeGreaterThan(0)
  })

  it('should call create API when adding user', async () => {
    usersApi.list.mockResolvedValue({ data: mockUsers })
    simulatorsApi.list.mockResolvedValue({ data: { simulators: mockSimulators } })
    usersApi.create.mockResolvedValueOnce({})

    const wrapper = mountComponent()
    await flushPromises()

    // Open add modal
    const addButton = wrapper.find('.btn-primary')
    await addButton.trigger('click')

    // Fill form
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('newuser')
    await inputs[1].setValue('password123')

    // Submit
    const createButton = wrapper.findAll('.btn-primary')[1]
    await createButton.trigger('click')
    await flushPromises()

    expect(usersApi.create).toHaveBeenCalled()
  })

  it('should open edit modal when edit button clicked', async () => {
    usersApi.list.mockResolvedValueOnce({ data: mockUsers })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    // Click edit button (first one for admin user)
    const editButtons = wrapper.findAll('.text-blue-600')
    await editButtons[0].trigger('click')

    expect(wrapper.text()).toContain('Edit User')
  })

  it('should call update API when saving user', async () => {
    usersApi.list.mockResolvedValue({ data: mockUsers })
    simulatorsApi.list.mockResolvedValue({ data: { simulators: mockSimulators } })
    usersApi.update.mockResolvedValueOnce({})

    const wrapper = mountComponent()
    await flushPromises()

    // Open edit modal
    const editButtons = wrapper.findAll('.text-blue-600')
    await editButtons[0].trigger('click')

    // Change username
    const usernameInput = wrapper.find('input[type="text"]')
    await usernameInput.setValue('updatedadmin')

    // Save
    const saveButton = wrapper.findAll('.btn-primary')[1]
    await saveButton.trigger('click')
    await flushPromises()

    expect(usersApi.update).toHaveBeenCalled()
  })

  it('should open delete modal when delete button clicked', async () => {
    usersApi.list.mockResolvedValueOnce({ data: mockUsers })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    // Click delete button
    const deleteButtons = wrapper.findAll('.text-red-600')
    await deleteButtons[0].trigger('click')

    expect(wrapper.text()).toContain('Delete User')
    expect(wrapper.text()).toContain('Are you sure you want to delete')
  })

  it('should call delete API when confirming delete', async () => {
    usersApi.list.mockResolvedValue({ data: mockUsers })
    simulatorsApi.list.mockResolvedValue({ data: { simulators: mockSimulators } })
    usersApi.delete.mockResolvedValueOnce({})

    const wrapper = mountComponent()
    await flushPromises()

    // Open delete modal
    const deleteButtons = wrapper.findAll('.text-red-600')
    await deleteButtons[0].trigger('click')

    // Confirm delete
    const confirmButton = wrapper.find('.bg-red-600')
    await confirmButton.trigger('click')
    await flushPromises()

    expect(usersApi.delete).toHaveBeenCalledWith(1)
  })

  it('should display role badges', async () => {
    usersApi.list.mockResolvedValueOnce({ data: mockUsers })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.find('.bg-purple-100').exists()).toBe(true) // admin badge
    expect(wrapper.find('.bg-blue-100').exists()).toBe(true) // simtech badge
  })

  it('should show error message on API failure', async () => {
    usersApi.list.mockResolvedValue({ data: mockUsers })
    simulatorsApi.list.mockResolvedValue({ data: { simulators: mockSimulators } })
    usersApi.create.mockRejectedValueOnce({
      response: { data: { detail: 'Username already exists' } }
    })

    const wrapper = mountComponent()
    await flushPromises()

    // Open add modal
    const addButton = wrapper.find('.btn-primary')
    await addButton.trigger('click')

    // Fill form
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('existinguser')
    await inputs[1].setValue('password123')

    // Submit
    const createButton = wrapper.findAll('.btn-primary')[1]
    await createButton.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Username already exists')
  })

  it('should have back button', async () => {
    usersApi.list.mockResolvedValueOnce({ data: mockUsers })
    simulatorsApi.list.mockResolvedValueOnce({ data: { simulators: mockSimulators } })

    const wrapper = mountComponent()
    await flushPromises()

    const backButton = wrapper.find('button.btn-secondary')
    expect(backButton.exists()).toBe(true)
  })
})
