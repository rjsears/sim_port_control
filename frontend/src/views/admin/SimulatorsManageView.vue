<!--
  Simulators Management View (Admin)
  Full CRUD for managing flight simulators
-->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { simulatorsApi } from '@/services/api'
import { ArrowLeftIcon, PlusIcon, PencilIcon, TrashIcon } from '@heroicons/vue/24/outline'
import BaseModal from '@/components/BaseModal.vue'

const router = useRouter()
const simulators = ref([])
const loading = ref(true)

// Modal state
const showAddModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const selectedSimulator = ref(null)
const formError = ref('')
const formLoading = ref(false)

const formData = ref({
  name: '',
  short_name: '',
  icon_path: ''
})

function resetForm() {
  formData.value = {
    name: '',
    short_name: '',
    icon_path: ''
  }
  formError.value = ''
}

function openAddModal() {
  resetForm()
  showAddModal.value = true
}

function openEditModal(sim) {
  selectedSimulator.value = sim
  formData.value = {
    name: sim.name,
    short_name: sim.short_name,
    icon_path: sim.icon_path || ''
  }
  formError.value = ''
  showEditModal.value = true
}

function openDeleteModal(sim) {
  selectedSimulator.value = sim
  showDeleteModal.value = true
}

async function fetchSimulators() {
  try {
    const response = await simulatorsApi.list()
    simulators.value = response.data.simulators
  } catch (err) {
    console.error('Failed to load simulators:', err)
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  formLoading.value = true
  formError.value = ''
  try {
    const data = { ...formData.value }
    if (!data.icon_path) delete data.icon_path
    await simulatorsApi.create(data)
    showAddModal.value = false
    await fetchSimulators()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Failed to create simulator'
  } finally {
    formLoading.value = false
  }
}

async function handleUpdate() {
  formLoading.value = true
  formError.value = ''
  try {
    const data = { ...formData.value }
    if (!data.icon_path) delete data.icon_path
    await simulatorsApi.update(selectedSimulator.value.id, data)
    showEditModal.value = false
    await fetchSimulators()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Failed to update simulator'
  } finally {
    formLoading.value = false
  }
}

async function handleDelete() {
  formLoading.value = true
  try {
    await simulatorsApi.delete(selectedSimulator.value.id)
    showDeleteModal.value = false
    await fetchSimulators()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Failed to delete simulator'
  } finally {
    formLoading.value = false
  }
}

onMounted(fetchSimulators)
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
            <h1 class="text-2xl font-bold text-primary">Simulator Management</h1>
          </div>
          <button @click="openAddModal" class="btn btn-primary flex items-center gap-2">
            <PlusIcon class="h-5 w-5" />
            Add Simulator
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div v-if="loading" class="flex justify-center py-12">
        <div class="spinner h-12 w-12"></div>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="sim in simulators" :key="sim.id" class="card p-6">
          <div class="flex justify-between items-start">
            <div class="flex-1">
              <h3 class="font-semibold text-primary">{{ sim.name }}</h3>
              <p class="text-sm text-secondary">{{ sim.short_name }}</p>
              <p class="text-sm text-muted mt-2">{{ sim.port_assignments?.length || 0 }} ports configured</p>
            </div>
            <div class="flex items-center gap-2">
              <button @click="openEditModal(sim)" class="btn btn-secondary p-2" title="Edit">
                <PencilIcon class="h-5 w-5" />
              </button>
              <button @click="openDeleteModal(sim)" class="btn btn-secondary p-2 text-red-600" title="Delete">
                <TrashIcon class="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Add Simulator Modal -->
    <BaseModal :open="showAddModal" title="Add Simulator" @close="showAddModal = false">
      <div v-if="formError" class="mb-4 p-3 bg-red-100 text-red-700 rounded">
        {{ formError }}
      </div>
      <form @submit.prevent="handleCreate" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Name</label>
          <input v-model="formData.name" type="text" required maxlength="100"
            placeholder="e.g., Citation CJ3 Full Flight Simulator"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Short Name</label>
          <input v-model="formData.short_name" type="text" required maxlength="20"
            placeholder="e.g., CJ3"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Icon Path (optional)</label>
          <input v-model="formData.icon_path" type="text"
            placeholder="e.g., /icons/cj3.png"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
      </form>
      <template #footer>
        <button @click="showAddModal = false" class="btn btn-secondary">Cancel</button>
        <button @click="handleCreate" :disabled="formLoading" class="btn btn-primary">
          {{ formLoading ? 'Creating...' : 'Create Simulator' }}
        </button>
      </template>
    </BaseModal>

    <!-- Edit Simulator Modal -->
    <BaseModal :open="showEditModal" title="Edit Simulator" @close="showEditModal = false">
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
          <label class="block text-sm font-medium text-primary mb-1">Short Name</label>
          <input v-model="formData.short_name" type="text" required maxlength="20"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Icon Path (optional)</label>
          <input v-model="formData.icon_path" type="text"
            placeholder="e.g., /icons/cj3.png"
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
    <BaseModal :open="showDeleteModal" title="Delete Simulator" size="sm" @close="showDeleteModal = false">
      <p class="text-secondary">
        Are you sure you want to delete <strong class="text-primary">{{ selectedSimulator?.name }}</strong>?
      </p>
      <p class="text-sm text-red-600 mt-2">
        This will also remove all port assignments associated with this simulator.
      </p>
      <template #footer>
        <button @click="showDeleteModal = false" class="btn btn-secondary">Cancel</button>
        <button @click="handleDelete" :disabled="formLoading" class="btn bg-red-600 hover:bg-red-700 text-white">
          {{ formLoading ? 'Deleting...' : 'Delete' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>
