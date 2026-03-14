<!--
  Simulators View (Main Dashboard)
  Shows grid of simulators that user has access to
-->
<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSimulatorsStore } from '@/stores/simulators'
import {
  ArrowRightOnRectangleIcon,
  Cog6ToothIcon,
  KeyIcon,
  QuestionMarkCircleIcon,
  LockClosedIcon
} from '@heroicons/vue/24/outline'
import ChangePasswordModal from '@/components/ChangePasswordModal.vue'

const router = useRouter()
const authStore = useAuthStore()
const simulatorsStore = useSimulatorsStore()

// Change password modal
const showChangePasswordModal = ref(false)

// Placeholder icon for simulators without custom icon
const defaultIcon = '/icons/placeholder.svg'

// Local countdown state - tracks seconds remaining for each port
const localCountdowns = ref({})

/**
 * Initialize local countdowns from simulator data
 */
function initLocalCountdowns() {
  const countdowns = {}
  for (const sim of simulatorsStore.simulators) {
    if (sim.port_assignments) {
      for (const port of sim.port_assignments) {
        if (port.seconds_remaining && port.seconds_remaining > 0) {
          countdowns[port.id] = port.seconds_remaining
        }
      }
    }
  }
  localCountdowns.value = countdowns
}

/**
 * Get seconds remaining for a port (from local state)
 */
function getPortSecondsRemaining(portId) {
  return localCountdowns.value[portId] || 0
}

/**
 * Get all active port times for a simulator.
 * Returns array of { portNumber, time } objects or empty array if no active ports.
 */
function getActivePortTimes(simulator) {
  if (!simulator.port_assignments?.length) return []

  const enabledPorts = simulator.port_assignments.filter(p => p.status === 'enabled' && !p.force_enabled)
  if (!enabledPorts.length) return []

  return enabledPorts
    .map(p => ({
      portNumber: p.port_number,
      seconds: getPortSecondsRemaining(p.id),
      time: formatTime(getPortSecondsRemaining(p.id))
    }))
    .filter(p => p.seconds > 0)
    .sort((a, b) => a.seconds - b.seconds) // Show shortest time first
}

function formatTime(seconds) {
  if (!seconds || seconds <= 0) return '0:00'

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

/**
 * Check if any port on the simulator is force-enabled (locked on).
 */
function hasLockedPort(simulator) {
  if (!simulator.port_assignments?.length) return false
  return simulator.port_assignments.some(p => p.force_enabled && p.status === 'enabled')
}

/**
 * Determine icon path to use based on simulator status.
 * Returns white/color version for active simulators, gray for inactive.
 *
 * @param {Object} simulator - Simulator object with icon_path and has_active_ports
 * @returns {string} Icon path to use
 */
function getSimulatorIcon(simulator) {
  if (!simulator.icon_path) return defaultIcon

  const basePath = simulator.icon_path
  const isActive = simulator.has_active_ports

  // Icon naming convention: *_wht.png (active), *_gray.png (inactive)
  if (isActive) {
    return basePath.replace('_gray', '_wht')
  }
  return basePath.includes('_gray') ? basePath : basePath.replace('_wht', '_gray')
}

function navigateToSimulator(simulator) {
  router.push({ name: 'simulator', params: { id: simulator.id } })
}

async function handleLogout() {
  await authStore.logout()
  router.push({ name: 'login' })
}

// Intervals
let countdownInterval = null
let refreshInterval = null

onMounted(async () => {
  await simulatorsStore.fetchSimulators()
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
        if (countdowns[portId] === 0) {
          timerExpired = true
        }
      }
    }

    if (hasChanges) {
      localCountdowns.value = countdowns
    }

    // If any timer expired, refresh from server
    if (timerExpired) {
      await simulatorsStore.fetchSimulators()
      initLocalCountdowns()
    }
  }, 1000)

  // Sync with server every 60 seconds
  refreshInterval = setInterval(async () => {
    await simulatorsStore.fetchSimulators()
    initLocalCountdowns()
  }, 60000)
})

onUnmounted(() => {
  if (countdownInterval) {
    clearInterval(countdownInterval)
  }
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<template>
  <div class="min-h-screen bg-map bg-gray-100 dark:bg-gray-900">
    <!-- Header -->
    <header class="bg-white dark:bg-gray-800 shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-primary">SimPortControl</h1>
            <p class="text-secondary text-sm">Welcome, {{ authStore.username }}</p>
          </div>
          <div class="flex items-center gap-4">
            <!-- Help/Manual Link -->
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
            <!-- Admin Button (if admin) -->
            <button
              v-if="authStore.isAdmin"
              @click="router.push({ name: 'admin' })"
              class="btn btn-secondary flex items-center gap-2"
            >
              <Cog6ToothIcon class="h-5 w-5" />
              <span class="hidden sm:inline">Admin</span>
            </button>
            <!-- Change Password -->
            <button
              @click="showChangePasswordModal = true"
              class="btn btn-secondary flex items-center gap-2"
              title="Change Password"
            >
              <KeyIcon class="h-5 w-5" />
              <span class="hidden sm:inline">Password</span>
            </button>
            <!-- Logout -->
            <button
              @click="handleLogout"
              class="btn btn-secondary flex items-center gap-2"
            >
              <ArrowRightOnRectangleIcon class="h-5 w-5" />
              <span class="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Loading State -->
      <div v-if="simulatorsStore.loading" class="flex justify-center py-12">
        <div class="spinner h-12 w-12"></div>
      </div>

      <!-- Error State -->
      <div v-else-if="simulatorsStore.error" class="text-center py-12">
        <p class="text-red-500">{{ simulatorsStore.error }}</p>
        <button @click="simulatorsStore.fetchSimulators()" class="btn btn-primary mt-4">
          Retry
        </button>
      </div>

      <!-- Empty State -->
      <div v-else-if="simulatorsStore.simulators.length === 0" class="text-center py-12">
        <SignalSlashIcon class="h-16 w-16 mx-auto text-gray-400" />
        <h3 class="mt-4 text-lg font-medium text-primary">No Simulators Assigned</h3>
        <p class="mt-2 text-secondary">Contact an administrator to get access to simulators.</p>
      </div>

      <!-- Simulators Grid -->
      <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-6">
        <div
          v-for="simulator in simulatorsStore.simulators"
          :key="simulator.id"
          @click="navigateToSimulator(simulator)"
          class="simulator-card card p-6 flex flex-col items-center text-center"
        >
          <!-- Icon with prominent green halo when active -->
          <div
            class="w-24 h-24 mb-3 rounded-2xl p-2 transition-all duration-300"
            :class="{
              'shadow-[0_0_30px_8px_rgba(16,185,129,0.5)] ring-2 ring-emerald-400 bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/40 dark:to-emerald-800/30': simulator.has_active_ports,
              'bg-gray-50 dark:bg-gray-800': !simulator.has_active_ports
            }"
          >
            <img
              :src="getSimulatorIcon(simulator)"
              :alt="simulator.name"
              class="w-full h-full object-contain"
              @error="(e) => e.target.src = defaultIcon"
            />
          </div>

          <!-- Name -->
          <h3 class="font-semibold text-primary">{{ simulator.short_name }}</h3>

          <!-- Internet Active Badge -->
          <div v-if="simulator.has_active_ports" class="mt-2 flex flex-col items-center gap-1">
            <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gradient-to-r from-emerald-500 to-green-500 text-white text-xs font-bold shadow-lg">
              <span class="relative flex h-2 w-2">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-white"></span>
              </span>
              Internet Active
            </div>
            <!-- Locked indicator for force-enabled ports -->
            <div v-if="hasLockedPort(simulator)" class="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400 font-semibold">
              <LockClosedIcon class="h-3.5 w-3.5" />
              Locked On
            </div>
            <!-- Time remaining for non-locked ports -->
            <div v-else-if="getActivePortTimes(simulator).length" class="flex flex-col items-center gap-0.5">
              <!-- Single port: just show time -->
              <div
                v-if="getActivePortTimes(simulator).length === 1"
                class="text-xs font-mono text-emerald-600 dark:text-emerald-400 font-semibold"
              >
                {{ getActivePortTimes(simulator)[0].time }}
              </div>
              <!-- Multiple ports: show port number with each time -->
              <div
                v-else
                v-for="portTime in getActivePortTimes(simulator)"
                :key="portTime.portNumber"
                class="text-xs font-mono text-emerald-600 dark:text-emerald-400 font-semibold"
              >
                {{ portTime.portNumber }}: {{ portTime.time }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Change Password Modal -->
    <ChangePasswordModal
      :open="showChangePasswordModal"
      @close="showChangePasswordModal = false"
    />
  </div>
</template>
