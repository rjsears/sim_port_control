import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PortStatusBadge from '@/components/PortStatusBadge.vue'

describe('PortStatusBadge', () => {
  describe('status display', () => {
    it('should display "In Use" for in_use status', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'in_use' }
      })

      expect(wrapper.text()).toContain('In Use')
    })

    it('should display capitalized status for other statuses', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'available' }
      })

      expect(wrapper.text()).toContain('Available')
    })

    it('should display "Assigned" for assigned status', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'assigned' }
      })

      expect(wrapper.text()).toContain('Assigned')
    })

    it('should display "Enabled" for enabled status', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'enabled' }
      })

      expect(wrapper.text()).toContain('Enabled')
    })

    it('should display "Error" for error status', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'error' }
      })

      expect(wrapper.text()).toContain('Error')
    })
  })

  describe('color classes', () => {
    it('should apply red classes for in_use status', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'in_use' }
      })

      expect(wrapper.html()).toContain('bg-red-100')
      expect(wrapper.html()).toContain('text-red-700')
    })

    it('should apply gray classes for available status', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'available' }
      })

      expect(wrapper.html()).toContain('bg-gray-100')
      expect(wrapper.html()).toContain('text-gray-700')
    })

    it('should apply blue classes for assigned status', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'assigned' }
      })

      expect(wrapper.html()).toContain('bg-blue-100')
      expect(wrapper.html()).toContain('text-blue-700')
    })

    it('should apply emerald classes for enabled status', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'enabled' }
      })

      expect(wrapper.html()).toContain('bg-emerald-100')
      expect(wrapper.html()).toContain('text-emerald-700')
    })

    it('should apply yellow classes for error status', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'error' }
      })

      expect(wrapper.html()).toContain('bg-yellow-100')
      expect(wrapper.html()).toContain('text-yellow-700')
    })
  })

  describe('time formatting', () => {
    it('should display time remaining when enabled with seconds', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'enabled', secondsRemaining: 3600 }
      })

      expect(wrapper.text()).toContain('1h 0m')
    })

    it('should display minutes only when less than an hour', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'enabled', secondsRemaining: 1800 }
      })

      expect(wrapper.text()).toContain('30m')
    })

    it('should display hours and minutes', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'enabled', secondsRemaining: 5400 }
      })

      expect(wrapper.text()).toContain('1h 30m')
    })

    it('should display status text when no time remaining', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'enabled', secondsRemaining: 0 }
      })

      expect(wrapper.text()).toContain('Enabled')
    })

    it('should display status text when secondsRemaining is null', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'enabled', secondsRemaining: null }
      })

      expect(wrapper.text()).toContain('Enabled')
    })
  })

  describe('badge structure', () => {
    it('should have rounded-full class for pill shape', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'available' }
      })

      expect(wrapper.find('.rounded-full').exists()).toBe(true)
    })

    it('should have an icon', () => {
      const wrapper = mount(PortStatusBadge, {
        props: { status: 'available' }
      })

      // Icons have h-4 w-4 classes
      expect(wrapper.find('.h-4.w-4').exists()).toBe(true)
    })
  })
})
