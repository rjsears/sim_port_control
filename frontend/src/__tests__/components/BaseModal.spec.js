import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseModal from '@/components/BaseModal.vue'

describe('BaseModal', () => {
  const defaultProps = {
    open: true,
    title: 'Test Modal'
  }

  // Stub Teleport so content renders in place for testing
  const globalConfig = {
    global: {
      stubs: {
        Teleport: true
      }
    }
  }

  it('should not render when closed', () => {
    const wrapper = mount(BaseModal, {
      props: { ...defaultProps, open: false },
      ...globalConfig
    })

    expect(wrapper.find('.fixed').exists()).toBe(false)
  })

  it('should render when open', () => {
    const wrapper = mount(BaseModal, {
      props: defaultProps,
      ...globalConfig
    })

    expect(wrapper.find('.fixed').exists()).toBe(true)
  })

  it('should display the title', () => {
    const wrapper = mount(BaseModal, {
      props: { ...defaultProps, title: 'My Title' },
      ...globalConfig
    })

    expect(wrapper.text()).toContain('My Title')
  })

  it('should render slot content', () => {
    const wrapper = mount(BaseModal, {
      props: defaultProps,
      slots: {
        default: '<p>Modal content</p>'
      },
      ...globalConfig
    })

    expect(wrapper.html()).toContain('Modal content')
  })

  it('should render footer slot when provided', () => {
    const wrapper = mount(BaseModal, {
      props: defaultProps,
      slots: {
        default: '<p>Body</p>',
        footer: '<button>Save</button>'
      },
      ...globalConfig
    })

    expect(wrapper.html()).toContain('Save')
  })

  it('should emit close when close button clicked', async () => {
    const wrapper = mount(BaseModal, {
      props: defaultProps,
      ...globalConfig
    })

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('should apply correct size class', () => {
    const wrapperSm = mount(BaseModal, {
      props: { ...defaultProps, size: 'sm' },
      ...globalConfig
    })
    const wrapperLg = mount(BaseModal, {
      props: { ...defaultProps, size: 'lg' },
      ...globalConfig
    })

    expect(wrapperSm.html()).toContain('max-w-md')
    expect(wrapperLg.html()).toContain('max-w-2xl')
  })

  it('should not close on backdrop click when persistent', async () => {
    const wrapper = mount(BaseModal, {
      props: { ...defaultProps, persistent: true },
      ...globalConfig
    })

    // Click the backdrop (the outer fixed div)
    await wrapper.find('.fixed').trigger('click')

    expect(wrapper.emitted('close')).toBeFalsy()
  })

  it('should close on backdrop click when not persistent', async () => {
    const wrapper = mount(BaseModal, {
      props: { ...defaultProps, persistent: false },
      ...globalConfig
    })

    await wrapper.find('.fixed').trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('should default to persistent mode', () => {
    const wrapper = mount(BaseModal, {
      props: { open: true, title: 'Test' },
      ...globalConfig
    })

    // Check the component's props
    expect(wrapper.props('persistent')).toBe(true)
  })
})
