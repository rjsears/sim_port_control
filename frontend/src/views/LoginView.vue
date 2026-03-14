<!--
  Login View
  Simple login form for SimPortControl
-->
<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { LockClosedIcon, UserIcon, ExclamationCircleIcon } from '@heroicons/vue/24/outline'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const showPassword = ref(false)

async function handleLogin() {
  const success = await authStore.login(username.value, password.value)
  if (success) {
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-map bg-gray-100 dark:bg-gray-900 px-4">
    <div class="max-w-md w-full">
      <!-- Logo/Title -->
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">SimPortControl</h1>
        <p class="mt-2 text-gray-600 dark:text-gray-400">Simulator Network Access Management</p>
      </div>

      <!-- Login Card -->
      <div class="card p-8">
        <form @submit.prevent="handleLogin" class="space-y-6">
          <!-- Error Message -->
          <div v-if="authStore.error" class="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400">
            <ExclamationCircleIcon class="h-5 w-5" />
            <span>{{ authStore.error }}</span>
          </div>

          <!-- Username -->
          <div>
            <label for="username" class="label">Username</label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <UserIcon class="h-5 w-5 text-gray-400" />
              </div>
              <input
                id="username"
                v-model="username"
                type="text"
                required
                autocomplete="username"
                class="input pl-10"
                placeholder="Enter username"
              />
            </div>
          </div>

          <!-- Password -->
          <div>
            <label for="password" class="label">Password</label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <LockClosedIcon class="h-5 w-5 text-gray-400" />
              </div>
              <input
                id="password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                required
                autocomplete="current-password"
                class="input pl-10"
                placeholder="Enter password"
              />
            </div>
          </div>

          <!-- Submit -->
          <button
            type="submit"
            :disabled="authStore.loading"
            class="w-full btn btn-primary flex items-center justify-center gap-2"
          >
            <span v-if="authStore.loading" class="spinner h-5 w-5"></span>
            <span>{{ authStore.loading ? 'Signing in...' : 'Sign In' }}</span>
          </button>
        </form>
      </div>

      <!-- Footer -->
      <div class="mt-6 text-center text-sm text-gray-500 dark:text-gray-400 space-y-0.5">
        <p>Version 1.0.0 | March 2026</p>
        <p>© 2026 SimPortControl. All rights reserved.</p>
        <p>Richard J. Sears - richardjsears@protonmail.com</p>
      </div>
    </div>
  </div>
</template>
