<!--
  Activity Logs View (Admin)
-->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { logsApi } from '@/services/api'
import { ArrowLeftIcon, TrashIcon, FunnelIcon } from '@heroicons/vue/24/outline'

const router = useRouter()
const logs = ref([])
const loading = ref(true)
const showClearModal = ref(false)
const clearing = ref(false)

// Filter state
const filterAction = ref('')
const filterUser = ref('')
const filterSimulator = ref('')

// Get unique values for filter dropdowns
const uniqueActions = computed(() => [...new Set(logs.value.map(l => l.action))].sort())
const uniqueUsers = computed(() => [...new Set(logs.value.map(l => l.username))].sort())
const uniqueSimulators = computed(() => [...new Set(logs.value.map(l => l.simulator_name).filter(Boolean))].sort())

// Filtered logs
const filteredLogs = computed(() => {
  return logs.value.filter(log => {
    if (filterAction.value && log.action !== filterAction.value) return false
    if (filterUser.value && log.username !== filterUser.value) return false
    if (filterSimulator.value && log.simulator_name !== filterSimulator.value) return false
    return true
  })
})

const hasActiveFilters = computed(() => filterAction.value || filterUser.value || filterSimulator.value)

function clearFilters() {
  filterAction.value = ''
  filterUser.value = ''
  filterSimulator.value = ''
}

async function loadLogs() {
  loading.value = true
  try {
    const response = await logsApi.list({ limit: 100 })
    logs.value = response.data.logs
  } catch (err) {
    console.error('Failed to load logs:', err)
  } finally {
    loading.value = false
  }
}

onMounted(loadLogs)

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleString()
}

async function clearLogs() {
  clearing.value = true
  try {
    await logsApi.clear()
    logs.value = []
    showClearModal.value = false
  } catch (err) {
    console.error('Failed to clear logs:', err)
  } finally {
    clearing.value = false
  }
}
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
            <h1 class="text-2xl font-bold text-primary">Activity Logs</h1>
          </div>
          <button
            v-if="logs.length > 0"
            @click="showClearModal = true"
            class="btn btn-danger flex items-center gap-2"
          >
            <TrashIcon class="h-5 w-5" />
            Clear Logs
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Filters -->
      <div class="card p-4 mb-6">
        <div class="flex items-center gap-4 flex-wrap">
          <div class="flex items-center gap-2">
            <FunnelIcon class="h-5 w-5 text-gray-400" />
            <span class="text-sm font-medium text-primary">Filters:</span>
          </div>
          <div class="flex-1 flex gap-4 flex-wrap">
            <select
              v-model="filterAction"
              class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary text-sm"
            >
              <option value="">All Actions</option>
              <option v-for="action in uniqueActions" :key="action" :value="action">{{ action }}</option>
            </select>
            <select
              v-model="filterUser"
              class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary text-sm"
            >
              <option value="">All Users</option>
              <option v-for="user in uniqueUsers" :key="user" :value="user">{{ user }}</option>
            </select>
            <select
              v-model="filterSimulator"
              class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary text-sm"
            >
              <option value="">All Simulators</option>
              <option v-for="sim in uniqueSimulators" :key="sim" :value="sim">{{ sim }}</option>
            </select>
          </div>
          <button
            v-if="hasActiveFilters"
            @click="clearFilters"
            class="btn btn-secondary text-sm"
          >
            Clear Filters
          </button>
        </div>
        <div v-if="hasActiveFilters" class="mt-2 text-sm text-secondary">
          Showing {{ filteredLogs.length }} of {{ logs.length }} logs
        </div>
      </div>

      <div v-if="loading" class="flex justify-center py-12">
        <div class="spinner h-12 w-12"></div>
      </div>

      <div v-else class="card overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Simulator</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Port</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reason</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-for="log in filteredLogs" :key="log.id" class="bg-white dark:bg-gray-800">
              <td class="px-6 py-4 text-sm text-secondary">{{ formatDate(log.timestamp) }}</td>
              <td class="px-6 py-4 text-primary">{{ log.username }}</td>
              <td class="px-6 py-4">
                <span :class="{
                  'bg-emerald-100 text-emerald-800': log.action === 'enable',
                  'bg-red-100 text-red-800': log.action === 'disable',
                  'bg-amber-100 text-amber-800': log.action === 'auto_disable',
                  'bg-orange-100 text-orange-800': log.action === 'force_enable',
                  'bg-blue-100 text-blue-800': log.action === 'port_discovered',
                  'bg-purple-100 text-purple-800': log.action === 'port_assigned',
                  'bg-gray-100 text-gray-800': log.action === 'port_released',
                  'bg-yellow-100 text-yellow-800': log.action === 'port_error',
                  'bg-teal-100 text-teal-800': log.action === 'port_recovered'
                }" class="px-2 py-1 rounded-full text-xs font-medium">
                  {{ log.action }}
                </span>
              </td>
              <td class="px-6 py-4 text-secondary">{{ log.simulator_name }}</td>
              <td class="px-6 py-4 text-secondary">{{ log.port_number }}</td>
              <td class="px-6 py-4 text-secondary text-sm">{{ log.details?.reason || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>

    <!-- Clear Logs Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showClearModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6">
          <div class="flex items-center gap-4 mb-4">
            <div class="p-3 rounded-full bg-red-100 dark:bg-red-500/20">
              <TrashIcon class="h-8 w-8 text-red-500" />
            </div>
            <h3 class="text-xl font-bold text-primary">Clear All Logs</h3>
          </div>

          <p class="text-secondary mb-6">
            Are you sure you want to delete all {{ logs.length }} activity logs? This action cannot be undone.
          </p>

          <div class="flex justify-end gap-3">
            <button @click="showClearModal = false" class="btn btn-secondary" :disabled="clearing">
              Cancel
            </button>
            <button
              @click="clearLogs"
              :disabled="clearing"
              class="btn btn-danger flex items-center gap-2"
            >
              <span v-if="clearing" class="spinner h-4 w-4"></span>
              Clear All Logs
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
