<!--
  Discovered Ports View (Admin)
  Shows all discovered ports across all switches
-->
<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { discoveryApi, switchesApi, simulatorsApi } from '@/services/api'
import { ArrowLeftIcon, ArrowPathIcon, SignalIcon, PlusIcon } from '@heroicons/vue/24/outline'
import BaseModal from '@/components/BaseModal.vue'

const router = useRouter()
const route = useRoute()
const ports = ref([])
const switches = ref([])
const simulators = ref([])
const loading = ref(true)
const scanning = ref(false)
const selectedSwitch = ref('')
const statusFilter = ref('')

// Assign modal state
const showAssignModal = ref(false)
const selectedPort = ref(null)
const selectedSimulator = ref('')
const assigning = ref(false)
const assignError = ref('')

// Watch for query param changes and update filter
watch(() => route.query.switch, (switchId) => {
  if (switchId) {
    selectedSwitch.value = switchId
  }
}, { immediate: true })

const filteredPorts = computed(() => {
  let result = ports.value
  if (selectedSwitch.value) {
    result = result.filter(p => p.switch_id == selectedSwitch.value)
  }
  if (statusFilter.value) {
    result = result.filter(p => p.status === statusFilter.value)
  }
  return result
})

const stats = computed(() => ({
  total: ports.value.length,
  available: ports.value.filter(p => p.status === 'available').length,
  assigned: ports.value.filter(p => p.status === 'assigned').length,
  error: ports.value.filter(p => p.status === 'error').length
}))

async function fetchData() {
  loading.value = true
  try {
    const [portsRes, switchesRes, simulatorsRes] = await Promise.all([
      discoveryApi.getAllPorts(),
      switchesApi.list(),
      simulatorsApi.list()
    ])
    ports.value = portsRes.data.ports || []
    switches.value = switchesRes.data.switches || []
    simulators.value = simulatorsRes.data.simulators || []
  } catch (err) {
    console.error('Failed to load data:', err)
  } finally {
    loading.value = false
  }
}

async function scanAllSwitches() {
  scanning.value = true
  try {
    for (const sw of switches.value) {
      await discoveryApi.scanSwitch(sw.id)
    }
    await fetchData()
  } catch (err) {
    alert('Scan failed: ' + (err.response?.data?.detail || err.message))
  } finally {
    scanning.value = false
  }
}

async function scanSwitch(switchId) {
  scanning.value = true
  try {
    await discoveryApi.scanSwitch(switchId)
    await fetchData()
  } catch (err) {
    alert('Scan failed: ' + (err.response?.data?.detail || err.message))
  } finally {
    scanning.value = false
  }
}

async function refreshPort(portId) {
  try {
    await discoveryApi.refreshPort(portId)
    await fetchData()
  } catch (err) {
    alert('Refresh failed: ' + (err.response?.data?.detail || err.message))
  }
}

function openAssignModal(port) {
  selectedPort.value = port
  selectedSimulator.value = ''
  assignError.value = ''
  showAssignModal.value = true
}

async function handleAssign() {
  if (!selectedSimulator.value) {
    assignError.value = 'Please select a simulator'
    return
  }
  assigning.value = true
  assignError.value = ''
  try {
    await discoveryApi.assignPort({
      discovered_port_id: selectedPort.value.id,
      simulator_id: parseInt(selectedSimulator.value)
    })
    showAssignModal.value = false
    await fetchData()
  } catch (err) {
    assignError.value = err.response?.data?.detail || 'Failed to assign port'
  } finally {
    assigning.value = false
  }
}

function getStatusConfig(status) {
  switch (status) {
    case 'available':
      return {
        bg: 'bg-gray-100 dark:bg-gray-700',
        text: 'text-gray-700 dark:text-gray-300',
        dot: 'bg-gray-500',
        label: 'Available'
      }
    case 'assigned':
      return {
        bg: 'bg-blue-100 dark:bg-blue-900/30',
        text: 'text-blue-700 dark:text-blue-300',
        dot: 'bg-blue-500',
        label: 'Assigned'
      }
    case 'in_use':
      return {
        bg: 'bg-emerald-100 dark:bg-emerald-900/30',
        text: 'text-emerald-700 dark:text-emerald-300',
        dot: 'bg-emerald-500',
        label: 'In Use'
      }
    case 'error':
      return {
        bg: 'bg-yellow-100 dark:bg-yellow-900/30',
        text: 'text-yellow-700 dark:text-yellow-300',
        dot: 'bg-yellow-500',
        label: 'Error'
      }
    default:
      return {
        bg: 'bg-gray-100 dark:bg-gray-700',
        text: 'text-gray-700 dark:text-gray-300',
        dot: 'bg-gray-400',
        label: status || 'Unknown'
      }
  }
}

// Get current switch name for header
const currentSwitchName = computed(() => {
  if (!selectedSwitch.value) return null
  const sw = switches.value.find(s => s.id == selectedSwitch.value)
  return sw?.name || null
})

onMounted(fetchData)
</script>

<template>
  <div class="min-h-screen bg-map bg-gray-100 dark:bg-gray-900">
    <header class="bg-white dark:bg-gray-800 shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <button @click="selectedSwitch ? router.push({ name: 'admin-switches' }) : router.push({ name: 'admin' })" class="btn btn-secondary p-2">
              <ArrowLeftIcon class="h-5 w-5" />
            </button>
            <div>
              <h1 class="text-2xl font-bold text-primary">
                {{ currentSwitchName ? currentSwitchName + ' Ports' : 'Discovered Ports' }}
              </h1>
              <p v-if="currentSwitchName" class="text-sm text-secondary">Switch port overview</p>
            </div>
          </div>
          <button @click="scanAllSwitches" :disabled="scanning" class="btn btn-primary flex items-center gap-2">
            <ArrowPathIcon :class="{'animate-spin': scanning}" class="h-5 w-5" />
            {{ scanning ? 'Scanning...' : 'Scan All Switches' }}
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Stats -->
      <div class="grid grid-cols-4 gap-4 mb-6">
        <div class="card p-4 text-center">
          <p class="text-2xl font-bold text-primary">{{ stats.total }}</p>
          <p class="text-sm text-secondary">Total Ports</p>
        </div>
        <div class="card p-4 text-center">
          <p class="text-2xl font-bold text-gray-600">{{ stats.available }}</p>
          <p class="text-sm text-secondary">Available</p>
        </div>
        <div class="card p-4 text-center">
          <p class="text-2xl font-bold text-blue-600">{{ stats.assigned }}</p>
          <p class="text-sm text-secondary">Assigned</p>
        </div>
        <div class="card p-4 text-center">
          <p class="text-2xl font-bold text-yellow-600">{{ stats.error }}</p>
          <p class="text-sm text-secondary">Errors</p>
        </div>
      </div>

      <!-- Filters -->
      <div class="card p-4 mb-6">
        <div class="flex gap-4">
          <div class="flex-1">
            <label class="block text-sm font-medium text-primary mb-1">Switch</label>
            <select v-model="selectedSwitch" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary">
              <option value="">All Switches</option>
              <option v-for="sw in switches" :key="sw.id" :value="sw.id">
                {{ sw.name }} ({{ sw.ip_address }})
              </option>
            </select>
          </div>
          <div class="flex-1">
            <label class="block text-sm font-medium text-primary mb-1">Status</label>
            <select v-model="statusFilter" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary">
              <option value="">All Statuses</option>
              <option value="available">Available</option>
              <option value="assigned">Assigned</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex justify-center py-12">
        <div class="spinner h-12 w-12"></div>
      </div>

      <!-- Ports Table -->
      <div v-else-if="filteredPorts.length > 0" class="card overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status / Port</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Switch</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assigned To</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-for="port in filteredPorts" :key="port.id" class="bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700/50">
              <td class="px-6 py-4">
                <div class="flex items-center gap-3">
                  <!-- Status indicator with colored dot and badge -->
                  <div :class="[getStatusConfig(port.status).bg, 'flex items-center gap-2 px-3 py-1.5 rounded-full']">
                    <span :class="[getStatusConfig(port.status).dot, 'w-2.5 h-2.5 rounded-full']"></span>
                    <span :class="[getStatusConfig(port.status).text, 'text-xs font-semibold']">
                      {{ getStatusConfig(port.status).label }}
                    </span>
                  </div>
                  <span class="font-mono font-medium text-primary">{{ port.short_name || port.port_name }}</span>
                </div>
              </td>
              <td class="px-6 py-4 text-secondary">{{ port.switch_name }}</td>
              <td class="px-6 py-4 text-secondary">{{ port.description || '-' }}</td>
              <td class="px-6 py-4 text-secondary">{{ port.assigned_simulator_name || '-' }}</td>
              <td class="px-6 py-4 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button
                    v-if="port.status === 'available'"
                    @click="openAssignModal(port)"
                    class="btn btn-primary btn-sm flex items-center gap-1"
                    title="Assign to Simulator"
                  >
                    <PlusIcon class="h-4 w-4" />
                    Assign
                  </button>
                  <button @click="refreshPort(port.id)" class="text-blue-600 hover:text-blue-900" title="Refresh status">
                    <ArrowPathIcon class="h-5 w-5" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Empty State -->
      <div v-else class="card p-8 text-center">
        <SignalIcon class="h-12 w-12 mx-auto text-gray-400 mb-4" />
        <p class="text-secondary">No ports discovered yet.</p>
        <p class="text-sm text-muted mt-2">Click "Scan All Switches" to discover available ports.</p>
      </div>

      <!-- Legend -->
      <div class="mt-6 card p-4">
        <p class="text-sm font-medium text-primary mb-3">Port Status Legend</p>
        <div class="flex flex-wrap items-center justify-center gap-4 text-sm">
          <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-100 dark:bg-gray-700">
            <span class="w-2.5 h-2.5 rounded-full bg-gray-500"></span>
            <span class="text-gray-700 dark:text-gray-300 font-medium">Available</span>
          </div>
          <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-100 dark:bg-blue-900/30">
            <span class="w-2.5 h-2.5 rounded-full bg-blue-500"></span>
            <span class="text-blue-700 dark:text-blue-300 font-medium">Assigned</span>
          </div>
          <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30">
            <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span class="text-emerald-700 dark:text-emerald-300 font-medium">In Use</span>
          </div>
          <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-yellow-100 dark:bg-yellow-900/30">
            <span class="w-2.5 h-2.5 rounded-full bg-yellow-500"></span>
            <span class="text-yellow-700 dark:text-yellow-300 font-medium">Error</span>
          </div>
        </div>
      </div>
    </main>

    <!-- Assign Port Modal -->
    <BaseModal :open="showAssignModal" title="Assign Port to Simulator" size="sm" @close="showAssignModal = false">
      <div v-if="assignError" class="mb-4 p-3 bg-red-100 text-red-700 rounded">
        {{ assignError }}
      </div>
      <div class="space-y-4">
        <div>
          <p class="text-sm text-secondary mb-2">Port:</p>
          <p class="font-mono font-medium text-primary">
            {{ selectedPort?.short_name || selectedPort?.port_name }} on {{ selectedPort?.switch_name }}
          </p>
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Assign to Simulator</label>
          <select
            v-model="selectedSimulator"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary"
          >
            <option value="">Select a simulator...</option>
            <option v-for="sim in simulators" :key="sim.id" :value="sim.id">
              {{ sim.name }} ({{ sim.short_name }})
            </option>
          </select>
        </div>
      </div>
      <template #footer>
        <button @click="showAssignModal = false" class="btn btn-secondary">Cancel</button>
        <button @click="handleAssign" :disabled="assigning || !selectedSimulator" class="btn btn-primary">
          {{ assigning ? 'Assigning...' : 'Assign Port' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>
