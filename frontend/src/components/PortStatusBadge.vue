<!-- frontend/src/components/PortStatusBadge.vue -->
<script setup>
import { computed } from 'vue'
import { SignalIcon, SignalSlashIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: (v) => ['in_use', 'available', 'assigned', 'enabled', 'error'].includes(v)
  },
  secondsRemaining: {
    type: Number,
    default: null
  }
})

const colorClasses = computed(() => {
  switch (props.status) {
    case 'in_use':
      return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
    case 'available':
      return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
    case 'assigned':
      return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
    case 'enabled':
      return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
    case 'error':
      return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
    default:
      return 'bg-gray-100 text-gray-700'
  }
})

const iconColorClasses = computed(() => {
  switch (props.status) {
    case 'in_use':
      return 'text-red-500'
    case 'available':
      return 'text-gray-400'
    case 'assigned':
      return 'text-blue-500'
    case 'enabled':
      return 'text-emerald-500'
    case 'error':
      return 'text-yellow-500'
    default:
      return 'text-gray-400'
  }
})

function formatTime(seconds) {
  if (!seconds || seconds <= 0) return ''
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}
</script>

<template>
  <div
    class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium"
    :class="colorClasses"
  >
    <ExclamationTriangleIcon v-if="status === 'error'" class="h-4 w-4" :class="iconColorClasses" />
    <SignalSlashIcon v-else-if="status === 'assigned' || status === 'in_use'" class="h-4 w-4" :class="iconColorClasses" />
    <SignalIcon v-else class="h-4 w-4" :class="iconColorClasses" />

    <span v-if="status === 'enabled' && secondsRemaining">
      {{ formatTime(secondsRemaining) }}
    </span>
    <span v-else>
      {{ status === 'in_use' ? 'In Use' : status.charAt(0).toUpperCase() + status.slice(1) }}
    </span>
  </div>
</template>
