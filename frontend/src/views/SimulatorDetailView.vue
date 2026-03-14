<!--
  Simulator Detail View
  Shows port status and allows enable/disable
-->
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSimulatorsStore } from '@/stores/simulators'
import { useAuthStore } from '@/stores/auth'
import {
  ArrowLeftIcon,
  SignalIcon,
  CheckCircleIcon,
  XCircleIcon,
  PlusIcon,
  BoltIcon,
  LockClosedIcon,
  QuestionMarkCircleIcon
} from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const simulatorsStore = useSimulatorsStore()
const authStore = useAuthStore()

const simulatorId = computed(() => parseInt(route.params.id))
const simulator = computed(() => simulatorsStore.getSimulatorById(simulatorId.value))
const isAdmin = computed(() => authStore.isAdmin)
const loading = ref(false)
const actionError = ref(null)
const showConfirmModal = ref(false)
const confirmAction = ref(null)
const selectedPort = ref(null)

// Admin controls
const customTimeout = ref(null)
const forceEnableReason = ref('')
const showForceEnableModal = ref(false)

// Timeout options - basic options for all users
const baseTimeoutOptions = [
  { value: null, label: 'Default' },
  { value: 1, label: '1 hour' },
  { value: 2, label: '2 hours' },
  { value: 4, label: '4 hours' },
  { value: 8, label: '8 hours' },
  { value: 12, label: '12 hours' },
  { value: 24, label: '24 hours' },
]

// Extended options for admins only
const adminOnlyOptions = [
  { value: 48, label: '2 days' },
  { value: 72, label: '3 days' },
  { value: 168, label: '1 week' },
  { value: 'always', label: 'Always On (until manually disabled)' }
]

// Combined options based on role
const timeoutOptions = computed(() => {
  if (isAdmin.value) {
    return [...baseTimeoutOptions, ...adminOnlyOptions]
  }
  return baseTimeoutOptions
})

// Local countdown state (decremented every second)
const localCountdowns = ref({})

// Intervals for countdown and sync
let countdownInterval = null
let syncInterval = null

// Initialize local countdowns from port data
function initLocalCountdowns() {
  if (!simulator.value?.port_assignments) return
  const countdowns = {}
  for (const port of simulator.value.port_assignments) {
    if (port.seconds_remaining && port.seconds_remaining > 0) {
      countdowns[port.id] = port.seconds_remaining
    }
  }
  localCountdowns.value = countdowns
}

// Get seconds remaining for a port (from local state or server data)
function getSecondsRemaining(port) {
  if (localCountdowns.value[port.id] !== undefined) {
    return localCountdowns.value[port.id]
  }
  return port.seconds_remaining || 0
}

onMounted(async () => {
  await simulatorsStore.fetchSimulator(simulatorId.value)
  initLocalCountdowns()

  // Local countdown - decrement every second
  countdownInterval = setInterval(async () => {
    const countdowns = { ...localCountdowns.value }
    let hasChanges = false
    let timerExpired = false
    for (const portId in countdowns) {
      if (countdowns[portId] > 0) {
        countdowns[portId] -= 1
        hasChanges = true
        // Check if timer just hit zero
        if (countdowns[portId] === 0) {
          timerExpired = true
        }
      }
    }
    if (hasChanges) {
      localCountdowns.value = countdowns
    }
    // If any timer expired, refresh from server to get updated status
    if (timerExpired) {
      await simulatorsStore.fetchSimulator(simulatorId.value)
      initLocalCountdowns()
    }
  }, 1000)

  // Sync with server every 60 seconds (less frequent than before)
  syncInterval = setInterval(async () => {
    await simulatorsStore.fetchSimulator(simulatorId.value)
    initLocalCountdowns()
  }, 60000)
})

onUnmounted(() => {
  if (countdownInterval) {
    clearInterval(countdownInterval)
  }
  if (syncInterval) {
    clearInterval(syncInterval)
  }
})

function formatTimeRemaining(seconds) {
  if (!seconds || seconds <= 0) return '0:00'

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

function openConfirmModal(port, action) {
  selectedPort.value = port
  confirmAction.value = action
  customTimeout.value = null  // Reset to default
  showConfirmModal.value = true
  actionError.value = null
}

function openForceEnableModal(port) {
  selectedPort.value = port
  forceEnableReason.value = ''
  showForceEnableModal.value = true
  actionError.value = null
}

async function executeAction() {
  if (!selectedPort.value || !confirmAction.value) return

  // If "Always On" selected, switch to force enable modal
  if (confirmAction.value === 'enable' && customTimeout.value === 'always') {
    showConfirmModal.value = false
    forceEnableReason.value = ''
    showForceEnableModal.value = true
    return
  }

  loading.value = true
  actionError.value = null

  try {
    if (confirmAction.value === 'enable') {
      const options = customTimeout.value ? { timeout_hours: customTimeout.value } : {}
      await simulatorsStore.enablePort(selectedPort.value.id, options)
    } else {
      await simulatorsStore.disablePort(selectedPort.value.id)
    }
    // Return to dashboard after successful action
    router.push({ name: 'home' })
  } catch (err) {
    actionError.value = err.message
  } finally {
    loading.value = false
  }
}

async function executeForceEnable() {
  if (!selectedPort.value || !forceEnableReason.value.trim()) return

  loading.value = true
  actionError.value = null

  try {
    await simulatorsStore.forceEnablePort(selectedPort.value.id, forceEnableReason.value.trim())
    // Return to dashboard after successful action
    router.push({ name: 'home' })
  } catch (err) {
    actionError.value = err.message
  } finally {
    loading.value = false
  }
}

function closeModal() {
  showConfirmModal.value = false
  showForceEnableModal.value = false
  selectedPort.value = null
  confirmAction.value = null
  customTimeout.value = null
  forceEnableReason.value = ''
  actionError.value = null
}
</script>

<template>
  <div class="min-h-screen bg-map bg-gray-100 dark:bg-gray-900">
    <!-- Header -->
    <header class="bg-white dark:bg-gray-800 shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <button @click="router.push({ name: 'home' })" class="btn btn-secondary p-2">
              <ArrowLeftIcon class="h-5 w-5" />
            </button>
            <div>
              <h1 class="text-2xl font-bold text-primary">
                {{ simulator?.name || 'Loading...' }}
              </h1>
              <p class="text-secondary text-sm">{{ simulator?.short_name }}</p>
            </div>
          </div>
          <!-- Help Link -->
          <a
            href="/manual/index.html"
            target="_blank"
            rel="noopener noreferrer"
            class="btn btn-secondary flex items-center gap-2"
            title="User Manual"
          >
            <QuestionMarkCircleIcon class="h-5 w-5" />
            <span class="hidden sm:inline">Help</span>
          </a>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Loading -->
      <div v-if="simulatorsStore.loading && !simulator" class="flex justify-center py-12">
        <div class="spinner h-12 w-12"></div>
      </div>

      <!-- Ports List -->
      <div v-else-if="simulator" class="space-y-6">
        <div v-if="!simulator.port_assignments?.length" class="card p-8 text-center">
          <p class="text-secondary">No ports configured for this simulator.</p>
        </div>

        <!-- Multi-port list -->
        <div class="space-y-4">
          <div v-for="port in simulator.port_assignments" :key="port.id" class="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
            <!-- Port info -->
            <div class="flex items-center gap-4">
              <div
                class="w-12 h-12 rounded-lg flex items-center justify-center"
                :class="{
                  'bg-emerald-100 dark:bg-emerald-900/30': port.status === 'enabled',
                  'bg-blue-100 dark:bg-blue-900/30': port.status === 'disabled',
                  'bg-yellow-100 dark:bg-yellow-900/30': port.status === 'error'
                }"
              >
                <SignalIcon
                  class="h-6 w-6"
                  :class="{
                    'text-emerald-500': port.status === 'enabled',
                    'text-blue-500': port.status === 'disabled',
                    'text-yellow-500': port.status === 'error'
                  }"
                />
              </div>
              <div>
                <p class="font-medium">{{ port.port_number }}</p>
                <p class="text-sm text-gray-500">{{ port.switch_name }} | VLAN {{ port.vlan }}</p>
              </div>
            </div>

            <!-- Status and timer -->
            <div class="flex items-center gap-4">
              <!-- Force-enabled badge -->
              <div v-if="port.force_enabled" class="flex items-center gap-1.5 px-2 py-1 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-xs font-medium">
                <LockClosedIcon class="h-3.5 w-3.5" />
                Always On
              </div>
              <!-- Error message -->
              <div v-if="port.status === 'error'" class="text-sm text-yellow-600 dark:text-yellow-400">
                {{ port.error_message || 'Error occurred' }}
              </div>
              <!-- Timer for enabled ports (only if not force-enabled) -->
              <div v-else-if="port.status === 'enabled' && !port.force_enabled && getSecondsRemaining(port) > 0" class="text-sm text-emerald-600 dark:text-emerald-400 font-mono">
                {{ formatTimeRemaining(getSecondsRemaining(port)) }}
              </div>
              <!-- Admin force-enable button -->
              <button
                v-if="isAdmin && !port.force_enabled && port.status !== 'error'"
                @click.stop="openForceEnableModal(port)"
                :disabled="loading"
                class="btn btn-outline text-xs px-2 py-1"
                title="Enable indefinitely (maintenance mode)"
              >
                <BoltIcon class="h-4 w-4" />
              </button>
              <!-- Retry button for error state -->
              <button
                v-if="port.status === 'error'"
                @click="openConfirmModal(port, 'enable')"
                :disabled="loading"
                class="btn btn-warning"
              >
                Retry
              </button>
              <!-- Normal enable/disable button -->
              <button
                v-else
                @click="openConfirmModal(port, port.status === 'enabled' ? 'disable' : 'enable')"
                :disabled="loading"
                class="btn"
                :class="port.status === 'enabled' ? 'btn-blue' : 'btn-success'"
              >
                {{ port.status === 'enabled' ? 'Disable' : 'Enable' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Add Port button for admins - navigates to port assignments page -->
        <button
          v-if="isAdmin"
          @click="router.push({ name: 'admin-ports' })"
          class="mt-4 btn btn-outline flex items-center gap-2"
        >
          <PlusIcon class="h-5 w-5" />
          Manage Ports
        </button>
      </div>
    </main>

    <!-- Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showConfirmModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6">
          <div class="flex items-center gap-4 mb-4">
            <div
              class="p-3 rounded-full"
              :class="confirmAction === 'enable' ? 'bg-emerald-100 dark:bg-emerald-500/20' : 'bg-red-100 dark:bg-red-500/20'"
            >
              <CheckCircleIcon v-if="confirmAction === 'enable'" class="h-8 w-8 text-emerald-500" />
              <XCircleIcon v-else class="h-8 w-8 text-red-500" />
            </div>
            <h3 class="text-xl font-bold text-primary">
              {{ confirmAction === 'enable' ? 'Enable' : 'Disable' }} Internet Access
            </h3>
          </div>

          <p class="text-secondary mb-4">
            <template v-if="confirmAction === 'enable'">
              Activate internet access to <strong>{{ simulator?.name }}</strong> on port {{ selectedPort?.port_number }}?
            </template>
            <template v-else>
              Deactivate internet access to <strong>{{ simulator?.name }}</strong> on port {{ selectedPort?.port_number }}?
            </template>
          </p>

          <!-- Timeout selector (available to all users) -->
          <div v-if="confirmAction === 'enable'" class="mb-4">
            <label class="block text-sm font-medium text-primary mb-2">Duration</label>
            <select
              v-model="customTimeout"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option v-for="opt in timeoutOptions" :key="opt.value" :value="opt.value">
                {{ opt.value === null ? `Default (${selectedPort?.timeout_hours}h)` : opt.label }}
              </option>
            </select>
          </div>

          <!-- Error -->
          <div v-if="actionError" class="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400">
            {{ actionError }}
          </div>

          <div class="flex justify-end gap-3">
            <button @click="closeModal" class="btn btn-secondary" :disabled="loading">
              Cancel
            </button>
            <button
              @click="executeAction"
              :disabled="loading"
              class="btn flex items-center gap-2"
              :class="confirmAction === 'enable' ? 'btn-success' : 'btn-danger'"
            >
              <span v-if="loading" class="spinner h-4 w-4"></span>
              {{ confirmAction === 'enable' ? 'Enable' : 'Disable' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Force Enable Modal (Admin Only) -->
    <Teleport to="body">
      <div v-if="showForceEnableModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6">
          <div class="flex items-center gap-4 mb-4">
            <div class="p-3 rounded-full bg-purple-100 dark:bg-purple-500/20">
              <BoltIcon class="h-8 w-8 text-purple-500" />
            </div>
            <h3 class="text-xl font-bold text-primary">Enable Always-On Mode</h3>
          </div>

          <p class="text-secondary mb-4">
            Enable <strong>{{ simulator?.name }}</strong> on port {{ selectedPort?.port_number }} indefinitely.
            This will keep the port enabled until manually disabled.
          </p>

          <div class="mb-4">
            <label class="block text-sm font-medium text-primary mb-2">Reason (required)</label>
            <input
              v-model="forceEnableReason"
              type="text"
              placeholder="e.g., Maintenance, Testing, etc."
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>

          <!-- Error -->
          <div v-if="actionError" class="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400">
            {{ actionError }}
          </div>

          <div class="flex justify-end gap-3">
            <button @click="closeModal" class="btn btn-secondary" :disabled="loading">
              Cancel
            </button>
            <button
              @click="executeForceEnable"
              :disabled="loading || !forceEnableReason.trim()"
              class="btn btn-primary flex items-center gap-2 bg-purple-600 hover:bg-purple-700"
            >
              <span v-if="loading" class="spinner h-4 w-4"></span>
              Enable Always-On
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
