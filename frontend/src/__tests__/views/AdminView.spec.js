import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import AdminView from '@/views/AdminView.vue'
import { useAuthStore } from '@/stores/auth'

describe('AdminView', () => {
  let router
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', name: 'home', component: { template: '<div>Home</div>' } },
        { path: '/admin', name: 'admin', component: AdminView },
        { path: '/login', name: 'login', component: { template: '<div>Login</div>' } },
        { path: '/admin/users', name: 'admin-users', component: { template: '<div>Users</div>' } },
        { path: '/admin/simulators', name: 'admin-simulators', component: { template: '<div>Simulators</div>' } },
        { path: '/admin/switches', name: 'admin-switches', component: { template: '<div>Switches</div>' } },
        { path: '/admin/ports', name: 'admin-ports', component: { template: '<div>Ports</div>' } },
        { path: '/admin/discovered-ports', name: 'admin-discovered-ports', component: { template: '<div>Discovered</div>' } },
        { path: '/admin/logs', name: 'admin-logs', component: { template: '<div>Logs</div>' } },
        { path: '/admin/system', name: 'admin-system', component: { template: '<div>System</div>' } }
      ]
    })
  })

  function mountComponent(options = {}) {
    return mount(AdminView, {
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

  it('should display Administration title', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Administration')
  })

  it('should display subtitle', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('SimPortControl System Management')
  })

  it('should display all menu items', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Users')
    expect(wrapper.text()).toContain('Simulators')
    expect(wrapper.text()).toContain('Switches')
    expect(wrapper.text()).toContain('Port Assignments')
    expect(wrapper.text()).toContain('Discovered Ports')
    expect(wrapper.text()).toContain('Activity Logs')
    expect(wrapper.text()).toContain('System')
  })

  it('should display menu item descriptions', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Manage user accounts')
    expect(wrapper.text()).toContain('Configure flight simulators')
    expect(wrapper.text()).toContain('Manage Cisco switch connections')
  })

  it('should have back button', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    // Find the back button (first button in header)
    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('should have Quick Access section', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Quick Access')
  })

  it('should have Go to Internet Access Control button', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Go to Internet Access Control')
  })

  it('should have Password button', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Password')
  })

  it('should have Logout button', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    expect(wrapper.text()).toContain('Logout')
  })

  it('should render menu cards', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    // Should have 7 menu item cards
    const cards = wrapper.findAll('.card')
    expect(cards.length).toBe(7)
  })

  it('should navigate when clicking menu item', async () => {
    const pushSpy = vi.spyOn(router, 'push')

    const wrapper = mountComponent()
    await router.isReady()
    await flushPromises()

    const usersCard = wrapper.findAll('.card')[0]
    await usersCard.trigger('click')

    expect(pushSpy).toHaveBeenCalledWith({ name: 'admin-users' })
  })

  it('should call logout on logout button click', async () => {
    const authStore = useAuthStore()
    authStore.logout = vi.fn()

    const wrapper = mountComponent()
    await flushPromises()

    // Find logout button (has "Logout" text)
    const buttons = wrapper.findAll('button')
    const logoutButton = buttons.find(b => b.text().includes('Logout'))

    await logoutButton.trigger('click')

    expect(authStore.logout).toHaveBeenCalled()
  })
})
