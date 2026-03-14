# Admin CRUD Functionality Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up existing admin views (Users, Simulators, Switches) with full CRUD functionality using modals and existing API methods.

**Architecture:** Create a reusable BaseModal component, then add modal state and forms to each admin view. Forms submit to existing API methods in `src/services/api.js`.

**Tech Stack:** Vue 3 (Composition API), Tailwind CSS, Heroicons

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/components/BaseModal.vue` | Create | Reusable modal dialog |
| `frontend/src/views/admin/UsersView.vue` | Modify | Add/Edit/Delete user modals |
| `frontend/src/views/admin/SimulatorsManageView.vue` | Modify | Add simulator modal |
| `frontend/src/views/admin/SwitchesView.vue` | Modify | Add switch modal |

---

## Chunk 1: BaseModal Component

### Task 1: Create BaseModal Component

**Files:**
- Create: `frontend/src/components/BaseModal.vue`

- [ ] **Step 1: Create the BaseModal component**

```vue
<!--
  BaseModal - Reusable modal dialog component
-->
<script setup>
import { watch } from 'vue'
import { XMarkIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  }
})

const emit = defineEmits(['close'])

// Close on escape key
watch(() => props.open, (isOpen) => {
  if (isOpen) {
    document.addEventListener('keydown', handleEscape)
  } else {
    document.removeEventListener('keydown', handleEscape)
  }
})

function handleEscape(e) {
  if (e.key === 'Escape') {
    emit('close')
  }
}

function handleBackdropClick(e) {
  if (e.target === e.currentTarget) {
    emit('close')
  }
}

const sizeClasses = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl'
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
        @click="handleBackdropClick"
      >
        <div
          :class="[sizeClasses[size], 'w-full bg-white dark:bg-gray-800 rounded-lg shadow-xl']"
          @click.stop
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 class="text-lg font-semibold text-primary">{{ title }}</h3>
            <button
              @click="emit('close')"
              class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded"
            >
              <XMarkIcon class="h-5 w-5" />
            </button>
          </div>

          <!-- Body -->
          <div class="px-6 py-4">
            <slot></slot>
          </div>

          <!-- Footer -->
          <div v-if="$slots.footer" class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
            <slot name="footer"></slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
```

- [ ] **Step 2: Verify component renders**

Run: `cd frontend && npm run dev`

Open browser, import BaseModal in any view temporarily to verify it renders.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/BaseModal.vue
git commit -m "feat: add BaseModal component for admin dialogs"
```

---

## Chunk 2: UsersView CRUD

### Task 2: Add User Modal State and Form

**Files:**
- Modify: `frontend/src/views/admin/UsersView.vue`

- [ ] **Step 1: Add imports and modal state**

Replace lines 1-23 with:

```vue
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
```

- [ ] **Step 2: Update template with button handlers and modals**

Replace lines 26-85 (the entire template) with:

```vue
<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
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
                {{ user.assigned_simulators?.map(s => s.short_name).join(', ') || '-' }}
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
        <div>
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
        <div>
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
```

- [ ] **Step 3: Verify UsersView works**

Run: `cd frontend && npm run dev`

Test: Navigate to Admin > Users, click Add User, fill form, submit.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/admin/UsersView.vue
git commit -m "feat: add CRUD functionality to UsersView"
```

---

## Chunk 3: SimulatorsManageView Add Modal

### Task 3: Add Simulator Modal

**Files:**
- Modify: `frontend/src/views/admin/SimulatorsManageView.vue`

- [ ] **Step 1: Replace entire file with updated version**

```vue
<!--
  Simulators Management View (Admin)
-->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { simulatorsApi } from '@/services/api'
import { ArrowLeftIcon, PlusIcon } from '@heroicons/vue/24/outline'
import BaseModal from '@/components/BaseModal.vue'

const router = useRouter()
const simulators = ref([])
const loading = ref(true)

// Modal state
const showAddModal = ref(false)
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

onMounted(fetchSimulators)
</script>

<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
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
          <h3 class="font-semibold text-primary">{{ sim.name }}</h3>
          <p class="text-sm text-secondary">{{ sim.short_name }}</p>
          <p class="text-sm text-muted mt-2">{{ sim.ports?.length || 0 }} ports configured</p>
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
  </div>
</template>
```

- [ ] **Step 2: Verify SimulatorsManageView works**

Run: `cd frontend && npm run dev`

Test: Navigate to Admin > Simulators, click Add Simulator, fill form, submit.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/admin/SimulatorsManageView.vue
git commit -m "feat: add create functionality to SimulatorsManageView"
```

---

## Chunk 4: SwitchesView Add Modal

### Task 4: Add Switch Modal

**Files:**
- Modify: `frontend/src/views/admin/SwitchesView.vue`

- [ ] **Step 1: Replace entire file with updated version**

```vue
<!--
  Switches Management View (Admin)
-->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { switchesApi } from '@/services/api'
import { ArrowLeftIcon, PlusIcon, PlayIcon } from '@heroicons/vue/24/outline'
import BaseModal from '@/components/BaseModal.vue'

const router = useRouter()
const switches = ref([])
const loading = ref(true)

// Modal state
const showAddModal = ref(false)
const formError = ref('')
const formLoading = ref(false)

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

async function testConnection(switchId) {
  try {
    const response = await switchesApi.test(switchId)
    alert(response.data.message)
  } catch (err) {
    alert('Connection test failed: ' + (err.response?.data?.detail || err.message))
  }
}

onMounted(fetchSwitches)
</script>

<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
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

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div v-for="sw in switches" :key="sw.id" class="card p-6">
          <div class="flex justify-between items-start">
            <div>
              <h3 class="font-semibold text-primary">{{ sw.name }}</h3>
              <p class="text-sm text-secondary">{{ sw.ip_address }}</p>
              <p class="text-sm text-muted">{{ sw.port_count }} ports assigned</p>
            </div>
            <button @click="testConnection(sw.id)" class="btn btn-secondary p-2" title="Test Connection">
              <PlayIcon class="h-5 w-5" />
            </button>
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
  </div>
</template>
```

- [ ] **Step 2: Verify SwitchesView works**

Run: `cd frontend && npm run dev`

Test: Navigate to Admin > Switches, click Add Switch, fill form, submit.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/admin/SwitchesView.vue
git commit -m "feat: add create functionality to SwitchesView"
```

---

## Final Steps

- [ ] **Push branch and create PR**

```bash
git push -u origin feature/admin-crud-functionality
gh pr create --title "feat: add admin CRUD functionality" --body "Adds working Add/Edit/Delete functionality to admin views:
- BaseModal reusable component
- Users: full CRUD (add, edit, delete)
- Simulators: add
- Switches: add

Closes the admin stub views issue."
```
