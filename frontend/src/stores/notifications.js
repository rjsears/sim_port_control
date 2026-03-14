/**
 * Notifications Store
 * Toast notifications for the app
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNotificationStore = defineStore('notifications', () => {
  const toasts = ref([])
  let nextId = 1

  function addToast(message, type = 'info', duration = 5000) {
    const id = nextId++
    toasts.value.push({ id, message, type })

    if (duration > 0) {
      setTimeout(() => removeToast(id), duration)
    }
    return id
  }

  function removeToast(id) {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  function success(message, duration = 5000) {
    return addToast(message, 'success', duration)
  }

  function error(message, duration = 8000) {
    return addToast(message, 'error', duration)
  }

  function warning(message, duration = 6000) {
    return addToast(message, 'warning', duration)
  }

  function info(message, duration = 5000) {
    return addToast(message, 'info', duration)
  }

  return {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info
  }
})
