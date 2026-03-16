import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ToastContainer from '@/components/ToastContainer.vue'
import { useNotificationStore } from '@/stores/notifications'

describe('ToastContainer', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should render without toasts', () => {
    const wrapper = mount(ToastContainer)
    expect(wrapper.find('.fixed').exists()).toBe(true)
  })

  it('should render toasts from store', () => {
    const store = useNotificationStore()
    store.addToast('Test message', 'info', 0)

    const wrapper = mount(ToastContainer)
    expect(wrapper.text()).toContain('Test message')
  })

  it('should render multiple toasts', () => {
    const store = useNotificationStore()
    store.addToast('First toast', 'info', 0)
    store.addToast('Second toast', 'success', 0)
    store.addToast('Third toast', 'error', 0)

    const wrapper = mount(ToastContainer)
    expect(wrapper.text()).toContain('First toast')
    expect(wrapper.text()).toContain('Second toast')
    expect(wrapper.text()).toContain('Third toast')
  })

  it('should apply success styling for success toasts', () => {
    const store = useNotificationStore()
    store.addToast('Success!', 'success', 0)

    const wrapper = mount(ToastContainer)
    const toast = wrapper.find('[class*="border-l-emerald"]')
    expect(toast.exists()).toBe(true)
  })

  it('should apply error styling for error toasts', () => {
    const store = useNotificationStore()
    store.addToast('Error!', 'error', 0)

    const wrapper = mount(ToastContainer)
    const toast = wrapper.find('[class*="border-l-red"]')
    expect(toast.exists()).toBe(true)
  })

  it('should apply warning styling for warning toasts', () => {
    const store = useNotificationStore()
    store.addToast('Warning!', 'warning', 0)

    const wrapper = mount(ToastContainer)
    const toast = wrapper.find('[class*="border-l-amber"]')
    expect(toast.exists()).toBe(true)
  })

  it('should apply info styling for info toasts', () => {
    const store = useNotificationStore()
    store.addToast('Info!', 'info', 0)

    const wrapper = mount(ToastContainer)
    const toast = wrapper.find('[class*="border-l-blue"]')
    expect(toast.exists()).toBe(true)
  })

  it('should remove toast when close button clicked', async () => {
    const store = useNotificationStore()
    store.addToast('Removable', 'info', 0)

    const wrapper = mount(ToastContainer)
    expect(store.toasts).toHaveLength(1)

    await wrapper.find('button').trigger('click')

    expect(store.toasts).toHaveLength(0)
  })
})
