<!--
  Port Assignments View (Admin)
  Full CRUD for managing port-to-simulator assignments
-->
<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { portsApi, simulatorsApi, switchesApi, discoveryApi } from '@/services/api'
import { ArrowLeftIcon, PlusIcon, PencilIcon, TrashIcon, ArrowPathIcon } from '@heroicons/vue/24/outline'
import BaseModal from '@/components/BaseModal.vue'

const router = useRouter()
const ports = ref([])
const simulators = ref([])
const switches = ref([])
const availablePorts = ref([])
const loading = ref(true)
const loadingPorts = ref(false)
const scanningSwitch = ref(null)

// Modal state
const showAddModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const selectedPort = ref(null)
const formError = ref('')
const formLoading = ref(false)

// Form data
const formData = ref({
  simulator_id: '',
  switch_id: '',
  discovered_port_id: '',
  vlan: 30,
  timeout_hours: 4
})

function resetForm() {
  formData.value = {
    simulator_id: '',
    switch_id: '',
    discovered_port_id: '',
    vlan: 30,
    timeout_hours: 4
  }
  availablePorts.value = []
  formError.value = ''
}

function openAddModal() {
  resetForm()
  showAddModal.value = true
}

function openEditModal(port) {
  selectedPort.value = port
  formData.value = {
    simulator_id: port.simulator_id,
    switch_id: port.switch_id,
    discovered_port_id: port.discovered_port_id || '',
    vlan: port.vlan,
    timeout_hours: port.timeout_hours
  }
  formError.value = ''
  showEditModal.value = true
}

function openDeleteModal(port) {
  selectedPort.value = port
  showDeleteModal.value = true
}

async function fetchData() {
  try {
    const [portsRes, simsRes, switchesRes] = await Promise.all([
      portsApi.listAssignments(),
      simulatorsApi.list(),
      switchesApi.list()
    ])
    ports.value = portsRes.data.port_assignments || portsRes.data
    simulators.value = simsRes.data.simulators
    switches.value = switchesRes.data.switches
  } catch (err) {
    console.error('Failed to load data:', err)
  } finally {
    loading.value = false
  }
}

// Fetch available ports when switch is selected
async function fetchAvailablePorts(switchId) {
  if (!switchId) {
    availablePorts.value = []
    return
  }
  loadingPorts.value = true
  try {
    const response = await discoveryApi.getSwitchPorts(switchId)
    // Only show available (unassigned) ports
    availablePorts.value = response.data.ports.filter(p => p.status === 'available')
  } catch (err) {
    console.error('Failed to load ports:', err)
    availablePorts.value = []
  } finally {
    loadingPorts.value = false
  }
}

// Scan switch for ports
async function scanSwitch(switchId) {
  scanningSwitch.value = switchId
  try {
    await discoveryApi.scanSwitch(switchId)
    // Refresh available ports after scan
    if (formData.value.switch_id == switchId) {
      await fetchAvailablePorts(switchId)
    }
  } catch (err) {
    alert('Scan failed: ' + (err.response?.data?.detail || err.message))
  } finally {
    scanningSwitch.value = null
  }
}

// Watch for switch selection changes
watch(() => formData.value.switch_id, (newSwitchId) => {
  formData.value.discovered_port_id = ''
  fetchAvailablePorts(newSwitchId)
})

async function handleCreate() {
  formLoading.value = true
  formError.value = ''
  try {
    await discoveryApi.assignPort({
      discovered_port_id: parseInt(formData.value.discovered_port_id),
      simulator_id: parseInt(formData.value.simulator_id),
      vlan: parseInt(formData.value.vlan),
      timeout_hours: parseInt(formData.value.timeout_hours)
    })
    showAddModal.value = false
    await fetchData()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Failed to create port assignment'
  } finally {
    formLoading.value = false
  }
}

async function handleUpdate() {
  formLoading.value = true
  formError.value = ''
  try {
    await portsApi.updateAssignment(selectedPort.value.id, {
      vlan: parseInt(formData.value.vlan),
      timeout_hours: parseInt(formData.value.timeout_hours)
    })
    showEditModal.value = false
    await fetchData()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Failed to update port assignment'
  } finally {
    formLoading.value = false
  }
}

async function handleDelete() {
  formLoading.value = true
  try {
    await discoveryApi.releasePort(selectedPort.value.id)
    showDeleteModal.value = false
    await fetchData()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Failed to release port assignment'
  } finally {
    formLoading.value = false
  }
}

// Helper to get simulator/switch name
function getSimulatorName(id) {
  const sim = simulators.value.find(s => s.id === id)
  return sim ? sim.name : 'Unknown'
}

function getSwitchName(id) {
  const sw = switches.value.find(s => s.id === id)
  return sw ? sw.name : 'Unknown'
}

onMounted(fetchData)
</script>

<template>
  <div class="min-h-screen bg-map bg-gray-100 dark:bg-gray-900">
    <header class="bg-white dark:bg-gray-800 shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <button @click="router.push({ name: 'admin' })" class="btn btn-secondary p-2">
              <ArrowLeftIcon class="h-5 w-5" />
            </button>
            <h1 class="text-2xl font-bold text-primary">Port Assignments</h1>
          </div>
          <button @click="openAddModal" class="btn btn-primary flex items-center gap-2">
            <PlusIcon class="h-5 w-5" />
            Add Assignment
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div v-if="loading" class="flex justify-center py-12">
        <div class="spinner h-12 w-12"></div>
      </div>

      <div v-else-if="ports.length === 0" class="card p-8 text-center">
        <p class="text-secondary">No port assignments configured.</p>
        <button @click="openAddModal" class="btn btn-primary mt-4">
          Create First Assignment
        </button>
      </div>

      <div v-else class="card overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Simulator</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Switch</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Port</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">VLAN</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timeout</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-for="port in ports" :key="port.id" class="bg-white dark:bg-gray-800">
              <td class="px-6 py-4 text-primary">{{ port.simulator_name || getSimulatorName(port.simulator_id) }}</td>
              <td class="px-6 py-4 text-secondary">{{ port.switch_name || getSwitchName(port.switch_id) }}</td>
              <td class="px-6 py-4 text-secondary font-mono">{{ port.port_number }}</td>
              <td class="px-6 py-4 text-secondary">{{ port.vlan }}</td>
              <td class="px-6 py-4 text-secondary">{{ port.timeout_hours }}h</td>
              <td class="px-6 py-4">
                <span :class="port.status === 'enabled' ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-800'" class="px-2 py-1 rounded-full text-xs font-medium">
                  {{ port.status }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right">
                <button @click="openEditModal(port)" class="text-blue-600 hover:text-blue-900 mr-3">
                  <PencilIcon class="h-5 w-5" />
                </button>
                <button @click="openDeleteModal(port)" class="text-red-600 hover:text-red-900">
                  <TrashIcon class="h-5 w-5" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>

    <!-- Add Port Assignment Modal -->
    <BaseModal :open="showAddModal" title="Add Port Assignment" size="lg" @close="showAddModal = false">
      <div v-if="formError" class="mb-4 p-3 bg-red-100 text-red-700 rounded">
        {{ formError }}
      </div>
      <form @submit.prevent="handleCreate" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Simulator</label>
          <select v-model="formData.simulator_id" required
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary">
            <option value="">Select a simulator...</option>
            <option v-for="sim in simulators" :key="sim.id" :value="sim.id">
              {{ sim.name }} ({{ sim.short_name }})
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Switch</label>
          <div class="flex gap-2">
            <select v-model="formData.switch_id" required
              class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary">
              <option value="">Select a switch...</option>
              <option v-for="sw in switches" :key="sw.id" :value="sw.id">
                {{ sw.name }} ({{ sw.ip_address }})
              </option>
            </select>
            <button
              v-if="formData.switch_id"
              type="button"
              @click="scanSwitch(formData.switch_id)"
              :disabled="scanningSwitch === formData.switch_id"
              class="btn btn-secondary p-2"
              title="Scan switch for ports"
            >
              <ArrowPathIcon :class="{'animate-spin': scanningSwitch === formData.switch_id}" class="h-5 w-5" />
            </button>
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Port</label>
          <select v-model="formData.discovered_port_id" required :disabled="!formData.switch_id || loadingPorts"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary">
            <option value="">{{ loadingPorts ? 'Loading ports...' : (formData.switch_id ? 'Select a port...' : 'Select a switch first') }}</option>
            <option v-for="port in availablePorts" :key="port.id" :value="port.id">
              {{ port.port_name }} {{ port.description ? '- ' + port.description : '' }}
            </option>
          </select>
          <p v-if="formData.switch_id && !loadingPorts && availablePorts.length === 0" class="text-sm text-amber-600 mt-1">
            No available ports. Click the refresh button to scan the switch.
          </p>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-primary mb-1">VLAN</label>
            <input v-model="formData.vlan" type="number" required min="1" max="4094"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
          </div>
          <div>
            <label class="block text-sm font-medium text-primary mb-1">Timeout (hours)</label>
            <input v-model="formData.timeout_hours" type="number" required min="1" max="24"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
          </div>
        </div>
      </form>
      <template #footer>
        <button @click="showAddModal = false" class="btn btn-secondary">Cancel</button>
        <button @click="handleCreate" :disabled="formLoading" class="btn btn-primary">
          {{ formLoading ? 'Creating...' : 'Create Assignment' }}
        </button>
      </template>
    </BaseModal>

    <!-- Edit Port Assignment Modal -->
    <BaseModal :open="showEditModal" title="Edit Port Assignment" @close="showEditModal = false">
      <div v-if="formError" class="mb-4 p-3 bg-red-100 text-red-700 rounded">
        {{ formError }}
      </div>
      <div class="mb-4 p-3 bg-gray-100 dark:bg-gray-700 rounded">
        <p class="text-sm text-secondary">
          <strong>Port:</strong> {{ selectedPort?.port_number }} on {{ selectedPort?.switch_name || getSwitchName(selectedPort?.switch_id) }}
        </p>
        <p class="text-sm text-secondary">
          <strong>Simulator:</strong> {{ selectedPort?.simulator_name || getSimulatorName(selectedPort?.simulator_id) }}
        </p>
      </div>
      <form @submit.prevent="handleUpdate" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-primary mb-1">VLAN</label>
          <input v-model="formData.vlan" type="number" required min="1" max="4094"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Timeout (hours)</label>
          <input v-model="formData.timeout_hours" type="number" required min="1" max="24"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
      </form>
      <template #footer>
        <button @click="showEditModal = false" class="btn btn-secondary">Cancel</button>
        <button @click="handleUpdate" :disabled="formLoading" class="btn btn-primary">
          {{ formLoading ? 'Saving...' : 'Save Changes' }}
        </button>
      </template>
    </BaseModal>

    <!-- Delete Confirmation Modal -->
    <BaseModal :open="showDeleteModal" title="Delete Port Assignment" size="sm" @close="showDeleteModal = false">
      <p class="text-secondary">
        Are you sure you want to delete the port assignment for
        <strong class="text-primary">{{ selectedPort?.port_number }}</strong>
        on <strong class="text-primary">{{ selectedPort?.simulator_name || getSimulatorName(selectedPort?.simulator_id) }}</strong>?
      </p>
      <p class="text-sm text-red-600 mt-2">This will remove the port from the simulator.</p>
      <template #footer>
        <button @click="showDeleteModal = false" class="btn btn-secondary">Cancel</button>
        <button @click="handleDelete" :disabled="formLoading" class="btn bg-red-600 hover:bg-red-700 text-white">
          {{ formLoading ? 'Deleting...' : 'Delete' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>
