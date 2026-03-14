<!--
  Admin View - Admin Dashboard
  Landing page with navigation to admin sections
-->
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  ArrowLeftIcon,
  UsersIcon,
  ServerIcon,
  CircleStackIcon,
  SignalIcon,
  MagnifyingGlassCircleIcon,
  ClipboardDocumentListIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  KeyIcon
} from '@heroicons/vue/24/outline'
import ChangePasswordModal from '@/components/ChangePasswordModal.vue'

const router = useRouter()
const authStore = useAuthStore()

// Change password modal
const showChangePasswordModal = ref(false)

const menuItems = [
  {
    name: 'Users',
    description: 'Manage user accounts and simulator assignments',
    icon: UsersIcon,
    route: 'admin-users',
    color: 'bg-blue-500'
  },
  {
    name: 'Simulators',
    description: 'Configure flight simulators and FTDs',
    icon: ServerIcon,
    route: 'admin-simulators',
    color: 'bg-purple-500'
  },
  {
    name: 'Switches',
    description: 'Manage Cisco switch connections',
    icon: CircleStackIcon,
    route: 'admin-switches',
    color: 'bg-green-500'
  },
  {
    name: 'Port Assignments',
    description: 'Configure port to simulator mappings',
    icon: SignalIcon,
    route: 'admin-ports',
    color: 'bg-amber-500'
  },
  {
    name: 'Discovered Ports',
    description: 'View and scan switch ports',
    icon: MagnifyingGlassCircleIcon,
    route: 'admin-discovered-ports',
    color: 'bg-indigo-500'
  },
  {
    name: 'Activity Logs',
    description: 'View port control history',
    icon: ClipboardDocumentListIcon,
    route: 'admin-logs',
    color: 'bg-cyan-500'
  },
  {
    name: 'System',
    description: 'SSL certificates and system info',
    icon: Cog6ToothIcon,
    route: 'admin-system',
    color: 'bg-red-500'
  }
]

async function handleLogout() {
  await authStore.logout()
  router.push({ name: 'login' })
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
              <h1 class="text-2xl font-bold text-primary">Administration</h1>
              <p class="text-secondary text-sm">SimPortControl System Management</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
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
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="item in menuItems"
          :key="item.route"
          @click="router.push({ name: item.route })"
          class="card p-6 cursor-pointer hover:shadow-lg transition-shadow"
        >
          <div class="flex items-start gap-4">
            <div :class="[item.color, 'p-3 rounded-lg']">
              <component :is="item.icon" class="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 class="font-semibold text-primary">{{ item.name }}</h3>
              <p class="text-sm text-secondary mt-1">{{ item.description }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="mt-8">
        <h2 class="text-lg font-semibold text-primary mb-4">Quick Access</h2>
        <button
          @click="router.push({ name: 'home' })"
          class="btn btn-primary"
        >
          Go to Internet Access Control
        </button>
      </div>
    </main>

    <!-- Change Password Modal -->
    <ChangePasswordModal
      :open="showChangePasswordModal"
      @close="showChangePasswordModal = false"
    />
  </div>
</template>
