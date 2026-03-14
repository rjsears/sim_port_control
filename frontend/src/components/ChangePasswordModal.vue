<!--
  ChangePasswordModal - Modal for users to change their password
-->
<script setup>
import { ref, watch } from 'vue'
import BaseModal from '@/components/BaseModal.vue'
import { authApi } from '@/services/api'
import { useNotificationStore } from '@/stores/notifications'

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])
const notificationStore = useNotificationStore()

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')

// Reset form when modal opens/closes
watch(() => props.open, (isOpen) => {
  if (isOpen) {
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    error.value = ''
  }
})

async function handleSubmit() {
  error.value = ''

  // Validate passwords match
  if (newPassword.value !== confirmPassword.value) {
    error.value = 'New passwords do not match'
    return
  }

  // Validate password length
  if (newPassword.value.length < 6) {
    error.value = 'New password must be at least 6 characters'
    return
  }

  loading.value = true
  try {
    await authApi.changePassword(currentPassword.value, newPassword.value)
    notificationStore.success('Password changed successfully')
    emit('close')
  } catch (err) {
    const message = err.response?.data?.detail || 'Failed to change password'
    error.value = message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <BaseModal :open="open" title="Change Password" size="sm" @close="emit('close')">
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Error Message -->
      <div v-if="error" class="p-3 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg text-sm">
        {{ error }}
      </div>

      <!-- Current Password -->
      <div>
        <label class="block text-sm font-medium text-primary mb-1">
          Current Password
        </label>
        <input
          v-model="currentPassword"
          type="password"
          required
          class="input w-full"
          placeholder="Enter current password"
        />
      </div>

      <!-- New Password -->
      <div>
        <label class="block text-sm font-medium text-primary mb-1">
          New Password
        </label>
        <input
          v-model="newPassword"
          type="password"
          required
          minlength="6"
          class="input w-full"
          placeholder="Enter new password (min 6 characters)"
        />
      </div>

      <!-- Confirm New Password -->
      <div>
        <label class="block text-sm font-medium text-primary mb-1">
          Confirm New Password
        </label>
        <input
          v-model="confirmPassword"
          type="password"
          required
          class="input w-full"
          placeholder="Confirm new password"
        />
      </div>

      <!-- Submit Button -->
      <div class="flex justify-end gap-3 pt-4">
        <button
          type="button"
          @click="emit('close')"
          class="btn btn-secondary"
          :disabled="loading"
        >
          Cancel
        </button>
        <button
          type="submit"
          class="btn btn-primary"
          :disabled="loading"
        >
          <span v-if="loading" class="spinner h-4 w-4 mr-2"></span>
          {{ loading ? 'Changing...' : 'Change Password' }}
        </button>
      </div>
    </form>
  </BaseModal>
</template>
