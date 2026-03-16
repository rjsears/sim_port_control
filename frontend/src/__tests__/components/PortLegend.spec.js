import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PortLegend from '@/components/PortLegend.vue'

describe('PortLegend', () => {
  it('should render all status indicators', () => {
    const wrapper = mount(PortLegend)

    expect(wrapper.text()).toContain('In Use')
    expect(wrapper.text()).toContain('Available')
    expect(wrapper.text()).toContain('Assigned/Off')
    expect(wrapper.text()).toContain('Active (timer)')
    expect(wrapper.text()).toContain('Error')
  })

  it('should render colored dots for each status', () => {
    const wrapper = mount(PortLegend)

    // Check for the colored dot elements
    expect(wrapper.find('.bg-red-500').exists()).toBe(true)
    expect(wrapper.find('.bg-gray-400').exists()).toBe(true)
    expect(wrapper.find('.bg-blue-500').exists()).toBe(true)
    expect(wrapper.find('.bg-emerald-500').exists()).toBe(true)
    expect(wrapper.find('.bg-yellow-500').exists()).toBe(true)
  })

  it('should have proper container styling', () => {
    const wrapper = mount(PortLegend)

    const container = wrapper.find('.port-legend')
    expect(container.exists()).toBe(true)
    expect(container.classes()).toContain('flex')
  })

  it('should render five legend items', () => {
    const wrapper = mount(PortLegend)

    // Each legend item has a colored dot with rounded-full class
    const dots = wrapper.findAll('.rounded-full')
    expect(dots).toHaveLength(5)
  })
})
