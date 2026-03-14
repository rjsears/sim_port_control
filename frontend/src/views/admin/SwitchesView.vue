<!--
  Switches Management View (Admin)
  Full CRUD for managing Cisco switches
-->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { switchesApi } from '@/services/api'
import { ArrowLeftIcon, PlusIcon, PlayIcon, PencilIcon, TrashIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/vue/24/outline'
import BaseModal from '@/components/BaseModal.vue'

const router = useRouter()
const switches = ref([])
const loading = ref(true)

// Modal state
const showAddModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const showTestResultModal = ref(false)
const selectedSwitch = ref(null)
const formError = ref('')
const formLoading = ref(false)
const testingSwitch = ref(null)
const testResultSuccess = ref(false)
const testResultMessage = ref('')

const formData = ref({
  name: '',
  ip_address: '',
  username: '',
  password: '',
  device_type: 'cisco_ios'
})

function resetForm() {
  formData.value = {
    name: '',
    ip_address: '',
    username: '',
    password: '',
    device_type: 'cisco_ios'
  }
  formError.value = ''
}

function openAddModal() {
  resetForm()
  showAddModal.value = true
}

function openEditModal(sw) {
  selectedSwitch.value = sw
  formData.value = {
    name: sw.name,
    ip_address: sw.ip_address,
    username: sw.username,
    password: '', // Don't show existing password
    device_type: sw.device_type
  }
  formError.value = ''
  showEditModal.value = true
}

function openDeleteModal(sw) {
  selectedSwitch.value = sw
  showDeleteModal.value = true
}

async function fetchSwitches() {
  try {
    const response = await switchesApi.list()
    switches.value = response.data.switches
  } catch (err) {
    console.error('Failed to load switches:', err)
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  formLoading.value = true
  formError.value = ''
  try {
    await switchesApi.create(formData.value)
    showAddModal.value = false
    await fetchSwitches()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Failed to create switch'
  } finally {
    formLoading.value = false
  }
}

async function handleUpdate() {
  formLoading.value = true
  formError.value = ''
  try {
    const updateData = { ...formData.value }
    // Only send password if it was changed
    if (!updateData.password) {
      delete updateData.password
    }
    await switchesApi.update(selectedSwitch.value.id, updateData)
    showEditModal.value = false
    await fetchSwitches()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Failed to update switch'
  } finally {
    formLoading.value = false
  }
}

async function handleDelete() {
  formLoading.value = true
  try {
    await switchesApi.delete(selectedSwitch.value.id)
    showDeleteModal.value = false
    await fetchSwitches()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Failed to delete switch'
  } finally {
    formLoading.value = false
  }
}

async function testConnection(sw) {
  testingSwitch.value = sw.id
  try {
    const response = await switchesApi.test(sw.id)
    testResultSuccess.value = response.data.success
    testResultMessage.value = response.data.success
      ? 'Successfully connected to ' + sw.name
      : 'Connection failed: ' + response.data.message
  } catch (err) {
    testResultSuccess.value = false
    testResultMessage.value = 'Connection test failed: ' + (err.response?.data?.detail || err.message)
  } finally {
    testingSwitch.value = null
    showTestResultModal.value = true
  }
}

onMounted(fetchSwitches)
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
            <h1 class="text-2xl font-bold text-primary">Switch Management</h1>
          </div>
          <button @click="openAddModal" class="btn btn-primary flex items-center gap-2">
            <PlusIcon class="h-5 w-5" />
            Add Switch
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div v-if="loading" class="flex justify-center py-12">
        <div class="spinner h-12 w-12"></div>
      </div>

      <div v-else-if="switches.length === 0" class="card p-8 text-center">
        <p class="text-secondary">No switches configured.</p>
        <button @click="openAddModal" class="btn btn-primary mt-4">
          Add First Switch
        </button>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div
          v-for="sw in switches"
          :key="sw.id"
          class="card p-6 cursor-pointer hover:ring-2 hover:ring-blue-400 transition-all"
          @click="router.push({ name: 'admin-discovered-ports', query: { switch: sw.id } })"
        >
          <div class="flex justify-between items-start">
            <div class="flex-1">
              <h3 class="font-semibold text-primary">{{ sw.name }}</h3>
              <p class="text-sm text-secondary">{{ sw.ip_address }}</p>
              <p class="text-sm text-muted">{{ sw.port_count || 0 }} ports assigned</p>
              <p class="text-xs text-muted mt-1">{{ sw.device_type }}</p>
              <p class="text-xs text-blue-500 mt-2">Click to view ports →</p>
            </div>
            <div class="flex items-center gap-2">
              <button
                @click.stop="testConnection(sw)"
                :disabled="testingSwitch === sw.id"
                class="btn btn-secondary p-2"
                title="Test Connection"
              >
                <span v-if="testingSwitch === sw.id" class="spinner h-5 w-5"></span>
                <PlayIcon v-else class="h-5 w-5" />
              </button>
              <button @click.stop="openEditModal(sw)" class="btn btn-secondary p-2" title="Edit">
                <PencilIcon class="h-5 w-5" />
              </button>
              <button @click.stop="openDeleteModal(sw)" class="btn btn-secondary p-2 text-red-600" title="Delete">
                <TrashIcon class="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Add Switch Modal -->
    <BaseModal :open="showAddModal" title="Add Switch" @close="showAddModal = false">
      <div v-if="formError" class="mb-4 p-3 bg-red-100 text-red-700 rounded">
        {{ formError }}
      </div>
      <form @submit.prevent="handleCreate" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Name</label>
          <input v-model="formData.name" type="text" required maxlength="100"
            placeholder="e.g., Sim Bay Switch 1"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">IP Address</label>
          <input v-model="formData.ip_address" type="text" required
            placeholder="e.g., 192.168.1.100"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Username</label>
          <input v-model="formData.username" type="text" required
            placeholder="SSH username"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Password</label>
          <input v-model="formData.password" type="password" required
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Device Type</label>
          <select v-model="formData.device_type"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary">
            <option value="cisco_ios">Cisco IOS</option>
            <option value="cisco_ios_telnet">Cisco IOS (Telnet)</option>
          </select>
        </div>
      </form>
      <template #footer>
        <button @click="showAddModal = false" class="btn btn-secondary">Cancel</button>
        <button @click="handleCreate" :disabled="formLoading" class="btn btn-primary">
          {{ formLoading ? 'Creating...' : 'Create Switch' }}
        </button>
      </template>
    </BaseModal>

    <!-- Edit Switch Modal -->
    <BaseModal :open="showEditModal" title="Edit Switch" @close="showEditModal = false">
      <div v-if="formError" class="mb-4 p-3 bg-red-100 text-red-700 rounded">
        {{ formError }}
      </div>
      <form @submit.prevent="handleUpdate" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Name</label>
          <input v-model="formData.name" type="text" required maxlength="100"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">IP Address</label>
          <input v-model="formData.ip_address" type="text" required
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Username</label>
          <input v-model="formData.username" type="text" required
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Password (leave blank to keep current)</label>
          <input v-model="formData.password" type="password"
            placeholder="Enter new password or leave blank"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Device Type</label>
          <select v-model="formData.device_type"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary">
            <option value="cisco_ios">Cisco IOS</option>
            <option value="cisco_ios_telnet">Cisco IOS (Telnet)</option>
          </select>
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
    <BaseModal :open="showDeleteModal" title="Delete Switch" size="sm" @close="showDeleteModal = false">
      <p class="text-secondary">
        Are you sure you want to delete <strong class="text-primary">{{ selectedSwitch?.name }}</strong>?
      </p>
      <p class="text-sm text-red-600 mt-2">
        This will also remove all port assignments associated with this switch.
      </p>
      <template #footer>
        <button @click="showDeleteModal = false" class="btn btn-secondary">Cancel</button>
        <button @click="handleDelete" :disabled="formLoading" class="btn bg-red-600 hover:bg-red-700 text-white">
          {{ formLoading ? 'Deleting...' : 'Delete' }}
        </button>
      </template>
    </BaseModal>

    <!-- Test Connection Result Modal -->
    <BaseModal :open="showTestResultModal" title="Connection Test" size="sm" @close="showTestResultModal = false">
      <div class="flex flex-col items-center text-center py-4">
        <CheckCircleIcon v-if="testResultSuccess" class="h-16 w-16 text-green-500 mb-4" />
        <XCircleIcon v-else class="h-16 w-16 text-red-500 mb-4" />
        <p :class="testResultSuccess ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'" class="font-medium">
          {{ testResultMessage }}
        </p>
      </div>
      <template #footer>
        <button @click="showTestResultModal = false" class="btn btn-primary">OK</button>
      </template>
    </BaseModal>
  </div>
</template>
