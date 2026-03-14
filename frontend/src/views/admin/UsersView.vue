<!--
  Users Management View (Admin)
-->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usersApi, simulatorsApi } from '@/services/api'
import { ArrowLeftIcon, PlusIcon, PencilIcon, TrashIcon } from '@heroicons/vue/24/outline'
import BaseModal from '@/components/BaseModal.vue'

const router = useRouter()
const users = ref([])
const simulators = ref([])
const loading = ref(true)

// Modal state
const showAddModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const selectedUser = ref(null)
const formError = ref('')
const formLoading = ref(false)

// Form data
const formData = ref({
  username: '',
  password: '',
  role: 'simtech',
  assigned_simulator_ids: []
})

function resetForm() {
  formData.value = {
    username: '',
    password: '',
    role: 'simtech',
    assigned_simulator_ids: []
  }
  formError.value = ''
}

function openAddModal() {
  resetForm()
  showAddModal.value = true
}

function openEditModal(user) {
  selectedUser.value = user
  formData.value = {
    username: user.username,
    password: '',
    role: user.role,
    assigned_simulator_ids: user.assigned_simulators?.map(s => s.id) || []
  }
  formError.value = ''
  showEditModal.value = true
}

function openDeleteModal(user) {
  selectedUser.value = user
  showDeleteModal.value = true
}

async function fetchData() {
  try {
    const [usersRes, simsRes] = await Promise.all([
      usersApi.list(),
      simulatorsApi.list()
    ])
    users.value = usersRes.data
    simulators.value = simsRes.data.simulators
  } catch (err) {
    console.error('Failed to load data:', err)
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  formLoading.value = true
  formError.value = ''
  try {
    await usersApi.create(formData.value)
    showAddModal.value = false
    await fetchData()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Failed to create user'
  } finally {
    formLoading.value = false
  }
}

async function handleUpdate() {
  formLoading.value = true
  formError.value = ''
  try {
    const updateData = { ...formData.value }
    if (!updateData.password) {
      delete updateData.password
    }
    await usersApi.update(selectedUser.value.id, updateData)
    showEditModal.value = false
    await fetchData()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Failed to update user'
  } finally {
    formLoading.value = false
  }
}

async function handleDelete() {
  formLoading.value = true
  try {
    await usersApi.delete(selectedUser.value.id)
    showDeleteModal.value = false
    await fetchData()
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Failed to delete user'
  } finally {
    formLoading.value = false
  }
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
            <h1 class="text-2xl font-bold text-primary">User Management</h1>
          </div>
          <button @click="openAddModal" class="btn btn-primary flex items-center gap-2">
            <PlusIcon class="h-5 w-5" />
            Add User
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div v-if="loading" class="flex justify-center py-12">
        <div class="spinner h-12 w-12"></div>
      </div>

      <div v-else class="card overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Username</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assigned Simulators</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-for="user in users" :key="user.id" class="bg-white dark:bg-gray-800">
              <td class="px-6 py-4 whitespace-nowrap text-primary">{{ user.username }}</td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="user.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'" class="px-2 py-1 rounded-full text-xs font-medium">
                  {{ user.role }}
                </span>
              </td>
              <td class="px-6 py-4 text-secondary">
                <span v-if="user.role === 'admin'" class="text-purple-600 dark:text-purple-400 font-medium">All Simulators</span>
                <span v-else>{{ user.assigned_simulators?.map(s => s.short_name).join(', ') || '-' }}</span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right">
                <button @click="openEditModal(user)" class="text-blue-600 hover:text-blue-900 mr-3">
                  <PencilIcon class="h-5 w-5" />
                </button>
                <button @click="openDeleteModal(user)" class="text-red-600 hover:text-red-900">
                  <TrashIcon class="h-5 w-5" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>

    <!-- Add User Modal -->
    <BaseModal :open="showAddModal" title="Add User" @close="showAddModal = false">
      <div v-if="formError" class="mb-4 p-3 bg-red-100 text-red-700 rounded">
        {{ formError }}
      </div>
      <form @submit.prevent="handleCreate" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Username</label>
          <input v-model="formData.username" type="text" required minlength="3" maxlength="50"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Password</label>
          <input v-model="formData.password" type="password" required minlength="8"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Role</label>
          <select v-model="formData.role"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary">
            <option value="simtech">Sim Tech</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div v-if="formData.role === 'admin'" class="p-3 bg-purple-50 dark:bg-purple-900/30 rounded-lg">
          <p class="text-sm text-purple-700 dark:text-purple-300">
            Admin users automatically have access to all simulators.
          </p>
        </div>
        <div v-else>
          <label class="block text-sm font-medium text-primary mb-1">Assigned Simulators</label>
          <div class="space-y-2 max-h-40 overflow-y-auto">
            <label v-for="sim in simulators" :key="sim.id" class="flex items-center gap-2">
              <input type="checkbox" :value="sim.id" v-model="formData.assigned_simulator_ids"
                class="rounded border-gray-300" />
              <span class="text-secondary">{{ sim.name }} ({{ sim.short_name }})</span>
            </label>
          </div>
        </div>
      </form>
      <template #footer>
        <button @click="showAddModal = false" class="btn btn-secondary">Cancel</button>
        <button @click="handleCreate" :disabled="formLoading" class="btn btn-primary">
          {{ formLoading ? 'Creating...' : 'Create User' }}
        </button>
      </template>
    </BaseModal>

    <!-- Edit User Modal -->
    <BaseModal :open="showEditModal" title="Edit User" @close="showEditModal = false">
      <div v-if="formError" class="mb-4 p-3 bg-red-100 text-red-700 rounded">
        {{ formError }}
      </div>
      <form @submit.prevent="handleUpdate" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Username</label>
          <input v-model="formData.username" type="text" required minlength="3" maxlength="50"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Password (leave blank to keep current)</label>
          <input v-model="formData.password" type="password" minlength="8"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary" />
        </div>
        <div>
          <label class="block text-sm font-medium text-primary mb-1">Role</label>
          <select v-model="formData.role"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-primary">
            <option value="simtech">Sim Tech</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div v-if="formData.role === 'admin'" class="p-3 bg-purple-50 dark:bg-purple-900/30 rounded-lg">
          <p class="text-sm text-purple-700 dark:text-purple-300">
            Admin users automatically have access to all simulators.
          </p>
        </div>
        <div v-else>
          <label class="block text-sm font-medium text-primary mb-1">Assigned Simulators</label>
          <div class="space-y-2 max-h-40 overflow-y-auto">
            <label v-for="sim in simulators" :key="sim.id" class="flex items-center gap-2">
              <input type="checkbox" :value="sim.id" v-model="formData.assigned_simulator_ids"
                class="rounded border-gray-300" />
              <span class="text-secondary">{{ sim.name }} ({{ sim.short_name }})</span>
            </label>
          </div>
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
    <BaseModal :open="showDeleteModal" title="Delete User" size="sm" @close="showDeleteModal = false">
      <p class="text-secondary">
        Are you sure you want to delete <strong class="text-primary">{{ selectedUser?.username }}</strong>?
        This action cannot be undone.
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
