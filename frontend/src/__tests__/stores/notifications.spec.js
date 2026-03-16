import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useNotificationStore } from '@/stores/notifications'

describe('Notifications Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('initial state', () => {
    it('should have empty toasts array initially', () => {
      const store = useNotificationStore()
      expect(store.toasts).toEqual([])
    })
  })

  describe('addToast', () => {
    it('should add a toast with default type info', () => {
      const store = useNotificationStore()
      const id = store.addToast('Test message')

      expect(store.toasts).toHaveLength(1)
      expect(store.toasts[0]).toEqual({
        id,
        message: 'Test message',
        type: 'info'
      })
    })

    it('should add a toast with specified type', () => {
      const store = useNotificationStore()
      const id = store.addToast('Error message', 'error')

      expect(store.toasts[0].type).toBe('error')
    })

    it('should return unique IDs for each toast', () => {
      const store = useNotificationStore()
      const id1 = store.addToast('First')
      const id2 = store.addToast('Second')
      const id3 = store.addToast('Third')

      expect(id1).not.toBe(id2)
      expect(id2).not.toBe(id3)
      expect(id1).not.toBe(id3)
    })

    it('should auto-remove toast after duration', () => {
      const store = useNotificationStore()
      store.addToast('Test', 'info', 5000)

      expect(store.toasts).toHaveLength(1)

      vi.advanceTimersByTime(5000)

      expect(store.toasts).toHaveLength(0)
    })

    it('should not auto-remove toast with duration 0', () => {
      const store = useNotificationStore()
      store.addToast('Persistent', 'info', 0)

      expect(store.toasts).toHaveLength(1)

      vi.advanceTimersByTime(10000)

      expect(store.toasts).toHaveLength(1)
    })
  })

  describe('removeToast', () => {
    it('should remove a toast by ID', () => {
      const store = useNotificationStore()
      const id = store.addToast('Test', 'info', 0)

      expect(store.toasts).toHaveLength(1)

      store.removeToast(id)

      expect(store.toasts).toHaveLength(0)
    })

    it('should not throw when removing non-existent toast', () => {
      const store = useNotificationStore()
      expect(() => store.removeToast(999)).not.toThrow()
    })

    it('should only remove the specified toast', () => {
      const store = useNotificationStore()
      const id1 = store.addToast('First', 'info', 0)
      const id2 = store.addToast('Second', 'info', 0)
      const id3 = store.addToast('Third', 'info', 0)

      store.removeToast(id2)

      expect(store.toasts).toHaveLength(2)
      expect(store.toasts.find(t => t.id === id1)).toBeDefined()
      expect(store.toasts.find(t => t.id === id2)).toBeUndefined()
      expect(store.toasts.find(t => t.id === id3)).toBeDefined()
    })
  })

  describe('convenience methods', () => {
    it('success should add toast with success type', () => {
      const store = useNotificationStore()
      store.success('Success!')

      expect(store.toasts[0].type).toBe('success')
      expect(store.toasts[0].message).toBe('Success!')
    })

    it('error should add toast with error type', () => {
      const store = useNotificationStore()
      store.error('Error!')

      expect(store.toasts[0].type).toBe('error')
    })

    it('warning should add toast with warning type', () => {
      const store = useNotificationStore()
      store.warning('Warning!')

      expect(store.toasts[0].type).toBe('warning')
    })

    it('info should add toast with info type', () => {
      const store = useNotificationStore()
      store.info('Info!')

      expect(store.toasts[0].type).toBe('info')
    })

    it('error should have longer default duration', () => {
      const store = useNotificationStore()
      store.error('Error message')

      expect(store.toasts).toHaveLength(1)

      // Error has 8000ms default, should still exist at 7000ms
      vi.advanceTimersByTime(7000)
      expect(store.toasts).toHaveLength(1)

      // Should be gone after 8000ms
      vi.advanceTimersByTime(1000)
      expect(store.toasts).toHaveLength(0)
    })

    it('success should have default 5000ms duration', () => {
      const store = useNotificationStore()
      store.success('Success message')

      vi.advanceTimersByTime(4999)
      expect(store.toasts).toHaveLength(1)

      vi.advanceTimersByTime(1)
      expect(store.toasts).toHaveLength(0)
    })
  })
})
