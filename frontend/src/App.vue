<!--
  SimPortControl - Main Application Component
-->
<script setup>
import { RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { onMounted } from 'vue'
import ToastContainer from '@/components/ToastContainer.vue'

const authStore = useAuthStore()

onMounted(() => {
  // Check for existing auth token
  authStore.initAuth()
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <RouterView />
    <ToastContainer />
  </div>
</template>
