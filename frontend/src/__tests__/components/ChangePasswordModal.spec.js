import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ChangePasswordModal from '@/components/ChangePasswordModal.vue'

// Mock the api module
vi.mock('@/services/api', () => ({
  authApi: {
    changePassword: vi.fn()
  }
}))

import { authApi } from '@/services/api'

describe('ChangePasswordModal', () => {
  const globalConfig = {
    global: {
      stubs: {
        Teleport: true
      }
    }
  }

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should not render when closed', () => {
    const wrapper = mount(ChangePasswordModal, {
      props: { open: false },
      ...globalConfig
    })

    expect(wrapper.find('form').exists()).toBe(false)
  })

  it('should render form when open', () => {
    const wrapper = mount(ChangePasswordModal, {
      props: { open: true },
      ...globalConfig
    })

    expect(wrapper.find('form').exists()).toBe(true)
  })

  it('should have three password input fields', () => {
    const wrapper = mount(ChangePasswordModal, {
      props: { open: true },
      ...globalConfig
    })

    const passwordInputs = wrapper.findAll('input[type="password"]')
    expect(passwordInputs).toHaveLength(3)
  })

  it('should display error when passwords do not match', async () => {
    const wrapper = mount(ChangePasswordModal, {
      props: { open: true },
      ...globalConfig
    })

    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[0].setValue('currentpass')
    await inputs[1].setValue('newpass123')
    await inputs[2].setValue('differentpass')

    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('New passwords do not match')
  })

  it('should display error when password is too short', async () => {
    const wrapper = mount(ChangePasswordModal, {
      props: { open: true },
      ...globalConfig
    })

    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[0].setValue('currentpass')
    await inputs[1].setValue('short')
    await inputs[2].setValue('short')

    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('New password must be at least 6 characters')
  })

  it('should call API on valid submission', async () => {
    authApi.changePassword.mockResolvedValueOnce({})

    const wrapper = mount(ChangePasswordModal, {
      props: { open: true },
      ...globalConfig
    })

    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[0].setValue('currentpass')
    await inputs[1].setValue('newpassword123')
    await inputs[2].setValue('newpassword123')

    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(authApi.changePassword).toHaveBeenCalledWith('currentpass', 'newpassword123')
  })

  it('should emit close after successful password change', async () => {
    authApi.changePassword.mockResolvedValueOnce({})

    const wrapper = mount(ChangePasswordModal, {
      props: { open: true },
      ...globalConfig
    })

    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[0].setValue('currentpass')
    await inputs[1].setValue('newpassword123')
    await inputs[2].setValue('newpassword123')

    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('should display API error message on failure', async () => {
    authApi.changePassword.mockRejectedValueOnce({
      response: { data: { detail: 'Current password is incorrect' } }
    })

    const wrapper = mount(ChangePasswordModal, {
      props: { open: true },
      ...globalConfig
    })

    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[0].setValue('wrongpass')
    await inputs[1].setValue('newpassword123')
    await inputs[2].setValue('newpassword123')

    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('Current password is incorrect')
  })

  it('should have cancel button that emits close', async () => {
    const wrapper = mount(ChangePasswordModal, {
      props: { open: true },
      ...globalConfig
    })

    const cancelButton = wrapper.find('button[type="button"]')
    await cancelButton.trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('should show loading state during submission', async () => {
    // Never resolves to keep loading state
    authApi.changePassword.mockImplementationOnce(() => new Promise(() => {}))

    const wrapper = mount(ChangePasswordModal, {
      props: { open: true },
      ...globalConfig
    })

    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[0].setValue('currentpass')
    await inputs[1].setValue('newpassword123')
    await inputs[2].setValue('newpassword123')

    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.text()).toContain('Changing...')
  })

  it('should disable buttons during loading', async () => {
    authApi.changePassword.mockImplementationOnce(() => new Promise(() => {}))

    const wrapper = mount(ChangePasswordModal, {
      props: { open: true },
      ...globalConfig
    })

    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[0].setValue('currentpass')
    await inputs[1].setValue('newpassword123')
    await inputs[2].setValue('newpassword123')

    await wrapper.find('form').trigger('submit.prevent')

    const submitButton = wrapper.find('button[type="submit"]')
    const cancelButton = wrapper.find('button[type="button"]')

    expect(submitButton.attributes('disabled')).toBeDefined()
    expect(cancelButton.attributes('disabled')).toBeDefined()
  })
})
