import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '@/views/LoginView.vue'
import { useAuthStore } from '@/stores/auth'

// Mock the api module
vi.mock('@/services/api', () => ({
  default: {
    post: vi.fn(),
    defaults: {
      headers: {
        common: {}
      }
    }
  }
}))

describe('LoginView', () => {
  let router

  beforeEach(() => {
    setActivePinia(createPinia())

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', name: 'home', component: { template: '<div>Home</div>' } },
        { path: '/login', name: 'login', component: LoginView }
      ]
    })
  })

  function mountComponent(options = {}) {
    return mount(LoginView, {
      global: {
        plugins: [router],
        ...options.global
      },
      ...options
    })
  }

  it('should render login form', () => {
    const wrapper = mountComponent()

    expect(wrapper.find('form').exists()).toBe(true)
    expect(wrapper.find('input#username').exists()).toBe(true)
    expect(wrapper.find('input#password').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').exists()).toBe(true)
  })

  it('should display app title', () => {
    const wrapper = mountComponent()

    expect(wrapper.text()).toContain('SimPortControl')
    expect(wrapper.text()).toContain('Simulator Network Access Management')
  })

  it('should bind username input to v-model', async () => {
    const wrapper = mountComponent()
    const input = wrapper.find('input#username')

    await input.setValue('testuser')

    expect(input.element.value).toBe('testuser')
  })

  it('should bind password input to v-model', async () => {
    const wrapper = mountComponent()
    const input = wrapper.find('input#password')

    await input.setValue('testpass')

    expect(input.element.value).toBe('testpass')
  })

  it('should display error message when auth error exists', async () => {
    const wrapper = mountComponent()
    const store = useAuthStore()

    store.error = 'Invalid credentials'
    await flushPromises()

    expect(wrapper.text()).toContain('Invalid credentials')
  })

  it('should not display error message when no error', () => {
    const wrapper = mountComponent()
    const store = useAuthStore()

    store.error = null

    // Check that error div is not present
    expect(wrapper.find('.bg-red-50').exists()).toBe(false)
  })

  it('should show loading state on submit button', async () => {
    const wrapper = mountComponent()
    const store = useAuthStore()

    store.loading = true
    await flushPromises()

    expect(wrapper.text()).toContain('Signing in...')
  })

  it('should disable submit button when loading', async () => {
    const wrapper = mountComponent()
    const store = useAuthStore()

    store.loading = true
    await flushPromises()

    const button = wrapper.find('button[type="submit"]')
    expect(button.attributes('disabled')).toBeDefined()
  })

  it('should show Sign In text when not loading', () => {
    const wrapper = mountComponent()
    const store = useAuthStore()

    store.loading = false

    expect(wrapper.text()).toContain('Sign In')
  })

  it('should have password input of type password by default', () => {
    const wrapper = mountComponent()
    const input = wrapper.find('input#password')

    expect(input.attributes('type')).toBe('password')
  })

  it('should have required attribute on inputs', () => {
    const wrapper = mountComponent()

    const usernameInput = wrapper.find('input#username')
    const passwordInput = wrapper.find('input#password')

    expect(usernameInput.attributes('required')).toBeDefined()
    expect(passwordInput.attributes('required')).toBeDefined()
  })

  it('should display footer with version info', () => {
    const wrapper = mountComponent()

    expect(wrapper.text()).toContain('Version 1.0.0')
    expect(wrapper.text()).toContain('SimPortControl')
  })
})
