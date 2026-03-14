<!--
  System View (Admin)
  SSL certificates and system info
-->
<script setup>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { systemApi } from '@/services/api'
import { useNotificationStore } from '@/stores/notifications'
import {
  ArrowLeftIcon,
  ShieldCheckIcon,
  ArrowPathIcon,
  CpuChipIcon,
  CircleStackIcon,
  ServerIcon,
  ClockIcon,
  GlobeAltIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  LockClosedIcon
} from '@heroicons/vue/24/outline'

const router = useRouter()
const notificationStore = useNotificationStore()
const systemInfo = ref(null)
const sslInfo = ref(null)
const loading = ref(true)
const refreshing = ref(false)
const renewingCert = ref(false)
const showRenewModal = ref(false)
const renewalResult = ref(null)
const dryRunMode = ref(false)
let refreshInterval = null

const cpuPercent = computed(() => systemInfo.value?.resources?.cpu?.percent || 0)
const memoryPercent = computed(() => systemInfo.value?.resources?.memory?.percent || 0)
const diskPercent = computed(() => systemInfo.value?.resources?.disk?.percent || 0)

const sslStatus = computed(() => {
  if (!sslInfo.value?.certificates?.length) return 'warning'
  const certs = sslInfo.value.certificates
  if (certs.some(c => c.days_until_expiry <= 7)) return 'error'
  if (certs.some(c => c.days_until_expiry <= 30)) return 'warning'
  return 'ok'
})

function getProgressColor(percent) {
  if (percent >= 90) return 'bg-red-500'
  if (percent >= 75) return 'bg-amber-500'
  return 'bg-emerald-500'
}

async function loadData() {
  try {
    const [infoRes, sslRes] = await Promise.all([
      systemApi.info(),
      systemApi.ssl()
    ])
    systemInfo.value = infoRes.data
    sslInfo.value = sslRes.data
  } catch (err) {
    console.error('Failed to load system info:', err)
    notificationStore.error('Failed to load system information')
  }
}

async function refresh() {
  refreshing.value = true
  await loadData()
  refreshing.value = false
}

onMounted(async () => {
  await loadData()
  loading.value = false
  // Refresh every 30 seconds
  refreshInterval = setInterval(loadData, 30000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})

function openRenewModal() {
  renewalResult.value = null
  dryRunMode.value = false
  showRenewModal.value = true
}

function closeRenewModal() {
  showRenewModal.value = false
  renewalResult.value = null
}

async function renewCertificate() {
  renewingCert.value = true
  renewalResult.value = null

  try {
    const response = await systemApi.renewSsl(dryRunMode.value)
    renewalResult.value = response.data

    if (response.data.success) {
      if (dryRunMode.value) {
        notificationStore.success('Dry run completed successfully')
      } else {
        notificationStore.success('SSL certificate renewed successfully')
        // Refresh SSL info after a delay
        setTimeout(async () => {
          const sslRes = await systemApi.ssl()
          sslInfo.value = sslRes.data
        }, 2000)
      }
    } else {
      notificationStore.error(response.data.message || 'Certificate renewal failed')
    }
  } catch (err) {
    renewalResult.value = {
      success: false,
      message: err.response?.data?.detail || err.message || 'Failed to renew certificate',
      renewal_output: ''
    }
    notificationStore.error(err.response?.data?.detail || 'Failed to renew certificate')
  } finally {
    renewingCert.value = false
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
            <div>
              <h1 class="text-2xl font-bold text-primary">System</h1>
              <p class="text-sm text-secondary">Server health, resources, and configuration</p>
            </div>
          </div>
          <button @click="refresh" :disabled="refreshing" class="btn btn-secondary flex items-center gap-2">
            <ArrowPathIcon :class="{'animate-spin': refreshing}" class="h-5 w-5" />
            Refresh
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div v-if="loading" class="flex justify-center py-12">
        <div class="spinner h-12 w-12"></div>
      </div>

      <div v-else class="space-y-6">
        <!-- System Resources Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <!-- CPU -->
          <div class="card p-4">
            <div class="flex items-center gap-3 mb-3">
              <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-500/20">
                <CpuChipIcon class="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">CPU Usage</p>
                <p class="text-xl font-bold text-primary">{{ cpuPercent.toFixed(1) }}%</p>
              </div>
            </div>
            <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div :class="getProgressColor(cpuPercent)" class="h-full rounded-full transition-all" :style="{ width: `${cpuPercent}%` }"></div>
            </div>
            <p v-if="systemInfo?.resources?.cpu" class="text-xs text-muted mt-2">
              Load: {{ systemInfo.resources.cpu.load_avg_1m }} / {{ systemInfo.resources.cpu.load_avg_5m }} / {{ systemInfo.resources.cpu.load_avg_15m }}
            </p>
          </div>

          <!-- Memory -->
          <div class="card p-4">
            <div class="flex items-center gap-3 mb-3">
              <div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-500/20">
                <CircleStackIcon class="h-5 w-5 text-purple-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">Memory</p>
                <p class="text-xl font-bold text-primary">{{ memoryPercent.toFixed(1) }}%</p>
              </div>
            </div>
            <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div :class="getProgressColor(memoryPercent)" class="h-full rounded-full transition-all" :style="{ width: `${memoryPercent}%` }"></div>
            </div>
            <p v-if="systemInfo?.resources?.memory" class="text-xs text-muted mt-2">
              {{ systemInfo.resources.memory.used_gb }} / {{ systemInfo.resources.memory.total_gb }} GB
            </p>
          </div>

          <!-- Disk -->
          <div class="card p-4">
            <div class="flex items-center gap-3 mb-3">
              <div class="p-2 rounded-lg bg-cyan-100 dark:bg-cyan-500/20">
                <ServerIcon class="h-5 w-5 text-cyan-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">Disk</p>
                <p class="text-xl font-bold text-primary">{{ diskPercent.toFixed(1) }}%</p>
              </div>
            </div>
            <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div :class="getProgressColor(diskPercent)" class="h-full rounded-full transition-all" :style="{ width: `${diskPercent}%` }"></div>
            </div>
            <p v-if="systemInfo?.resources?.disk" class="text-xs text-muted mt-2">
              {{ systemInfo.resources.disk.free_gb }} GB free of {{ systemInfo.resources.disk.total_gb }} GB
            </p>
          </div>

          <!-- Uptime -->
          <div class="card p-4">
            <div class="flex items-center gap-3 mb-3">
              <div class="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-500/20">
                <ClockIcon class="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">Uptime</p>
                <p class="text-xl font-bold text-primary">{{ systemInfo?.uptime?.uptime_formatted || 'N/A' }}</p>
              </div>
            </div>
            <p v-if="systemInfo?.uptime?.boot_time" class="text-xs text-muted mt-2">
              Since {{ new Date(systemInfo.uptime.boot_time).toLocaleString() }}
            </p>
          </div>
        </div>

        <!-- SSL Certificate Card -->
        <div class="card p-6">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-500/20">
                <LockClosedIcon class="h-6 w-6 text-emerald-500" />
              </div>
              <div>
                <h2 class="text-lg font-semibold text-primary">SSL Certificates</h2>
                <p class="text-xs text-muted">Certificate validity</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button
                @click="openRenewModal"
                :class="[
                  'px-3 py-1.5 rounded-full text-xs font-medium transition-all shadow-sm flex items-center gap-1.5',
                  sslStatus === 'ok'
                    ? 'bg-emerald-500 hover:bg-emerald-600 text-white'
                    : 'bg-amber-500 hover:bg-amber-600 text-white'
                ]"
              >
                <ArrowPathIcon class="h-3.5 w-3.5" />
                Force Renew
              </button>
              <span
                :class="[
                  'px-2 py-1 rounded-full text-xs font-medium',
                  sslStatus === 'ok'
                    ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                    : sslStatus === 'warning'
                      ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400'
                      : 'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400'
                ]"
              >
                {{ sslStatus.toUpperCase() }}
              </span>
            </div>
          </div>

          <div v-if="sslInfo?.certificates?.length" class="space-y-3">
            <div v-for="cert in sslInfo.certificates" :key="cert.domain" class="p-4 rounded-lg bg-gray-50 dark:bg-gray-700">
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p class="text-sm text-secondary">Domain</p>
                  <p class="font-medium text-primary">{{ cert.domain }}</p>
                </div>
                <div>
                  <p class="text-sm text-secondary">Days Remaining</p>
                  <p :class="{
                    'text-emerald-500': cert.days_until_expiry > 30,
                    'text-amber-500': cert.days_until_expiry > 7 && cert.days_until_expiry <= 30,
                    'text-red-500': cert.days_until_expiry <= 7
                  }" class="font-medium">
                    {{ cert.days_until_expiry }} days
                  </p>
                </div>
                <div>
                  <p class="text-sm text-secondary">Expires</p>
                  <p class="font-medium text-primary">{{ cert.valid_until }}</p>
                </div>
                <div>
                  <p class="text-sm text-secondary">Issuer</p>
                  <p class="font-medium text-primary truncate">{{ cert.issuer || 'Let\'s Encrypt' }}</p>
                </div>
              </div>
              <div v-if="cert.warning" class="mt-3 p-2 rounded bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20">
                <p class="text-xs text-amber-700 dark:text-amber-400 flex items-center gap-1">
                  <ExclamationTriangleIcon class="h-4 w-4" />
                  {{ cert.warning }}
                </p>
              </div>
            </div>
          </div>
          <div v-else-if="sslInfo?.error" class="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 text-center">
            <p class="text-red-600 dark:text-red-400">{{ sslInfo.error }}</p>
          </div>
          <div v-else class="p-4 rounded-lg bg-gray-50 dark:bg-gray-700 text-center">
            <p class="text-secondary">{{ sslInfo?.message || 'No certificate information available' }}</p>
          </div>
        </div>

        <!-- Network & System Info -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Network Info -->
          <div class="card p-6">
            <div class="flex items-center gap-3 mb-4">
              <div class="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-500/20">
                <GlobeAltIcon class="h-6 w-6 text-indigo-500" />
              </div>
              <h2 class="text-lg font-semibold text-primary">Network</h2>
            </div>

            <div v-if="systemInfo?.network" class="space-y-3">
              <div class="flex justify-between">
                <span class="text-secondary">Hostname</span>
                <span class="text-primary font-medium font-mono">{{ systemInfo.network.hostname }}</span>
              </div>

              <div v-if="systemInfo.network.interfaces?.length" class="pt-3 border-t border-gray-200 dark:border-gray-700">
                <p class="text-sm text-secondary mb-2">Interfaces</p>
                <div v-for="iface in systemInfo.network.interfaces" :key="iface.name" class="py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
                  <div class="flex items-center justify-between">
                    <span class="font-mono text-primary">{{ iface.name }}</span>
                    <span :class="iface.is_up ? 'text-emerald-500' : 'text-red-500'" class="text-xs font-medium">
                      {{ iface.is_up ? 'UP' : 'DOWN' }}
                    </span>
                  </div>
                  <div v-for="addr in iface.addresses" :key="addr.address" class="text-xs text-muted mt-1">
                    {{ addr.type.toUpperCase() }}: {{ addr.address }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- App & Database Info -->
          <div class="card p-6">
            <div class="flex items-center gap-3 mb-4">
              <div class="p-2 rounded-lg bg-amber-100 dark:bg-amber-500/20">
                <ServerIcon class="h-6 w-6 text-amber-500" />
              </div>
              <h2 class="text-lg font-semibold text-primary">Application</h2>
            </div>

            <div v-if="systemInfo" class="space-y-3">
              <div class="flex justify-between">
                <span class="text-secondary">Version</span>
                <span class="text-primary font-medium">{{ systemInfo.version }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-secondary">Environment</span>
                <span class="text-primary font-medium">{{ systemInfo.environment }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-secondary">Platform</span>
                <span class="text-primary font-medium">{{ systemInfo.platform?.system }} {{ systemInfo.platform?.release }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-secondary">Python</span>
                <span class="text-primary font-medium">{{ systemInfo.platform?.python }}</span>
              </div>

              <div class="pt-3 border-t border-gray-200 dark:border-gray-700">
                <p class="text-sm text-secondary mb-2">Database</p>
                <div class="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p class="text-xl font-bold text-primary">{{ systemInfo.database?.simulators || 0 }}</p>
                    <p class="text-xs text-muted">Simulators</p>
                  </div>
                  <div>
                    <p class="text-xl font-bold text-primary">{{ systemInfo.database?.users || 0 }}</p>
                    <p class="text-xs text-muted">Users</p>
                  </div>
                  <div>
                    <p class="text-xl font-bold text-emerald-500">{{ systemInfo.database?.active_ports || 0 }}</p>
                    <p class="text-xs text-muted">Active Ports</p>
                  </div>
                </div>
              </div>

              <div class="pt-3 border-t border-gray-200 dark:border-gray-700">
                <div class="flex justify-between items-center">
                  <span class="text-secondary">Scheduler</span>
                  <span :class="systemInfo.scheduler?.status === 'running' ? 'text-emerald-500' : 'text-red-500'" class="font-medium flex items-center gap-1">
                    <span :class="systemInfo.scheduler?.status === 'running' ? 'bg-emerald-500' : 'bg-red-500'" class="w-2 h-2 rounded-full"></span>
                    {{ systemInfo.scheduler?.status }}
                  </span>
                </div>
                <p v-if="systemInfo.scheduler?.pending_jobs" class="text-xs text-muted mt-1">
                  {{ systemInfo.scheduler.pending_jobs }} pending jobs
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- SSL Renewal Modal -->
    <Teleport to="body">
      <div
        v-if="showRenewModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="fixed inset-0 bg-black/50 backdrop-blur-sm"></div>
        <div class="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-lg w-full p-6 border border-gray-200 dark:border-gray-700">
          <div class="flex items-center gap-3 mb-4">
            <div class="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-500/20">
              <LockClosedIcon class="h-6 w-6 text-emerald-500" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-primary">Force Renew SSL Certificate</h3>
              <p class="text-sm text-muted">Request new certificate from Let's Encrypt</p>
            </div>
          </div>

          <!-- Current Certificate Info -->
          <div v-if="!renewalResult" class="space-y-4">
            <div class="p-4 rounded-lg bg-gray-50 dark:bg-gray-700">
              <h4 class="text-sm font-medium text-primary mb-3">Current Certificate</h4>
              <div v-if="sslInfo?.certificates?.length" class="space-y-2">
                <div v-for="cert in sslInfo.certificates" :key="cert.domain" class="text-sm">
                  <div class="flex justify-between mb-1">
                    <span class="text-secondary">Domain</span>
                    <span class="font-medium text-primary">{{ cert.domain }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-secondary">Expires In</span>
                    <span
                      :class="[
                        'font-medium',
                        cert.days_until_expiry > 30 ? 'text-emerald-500' :
                        cert.days_until_expiry > 7 ? 'text-amber-500' : 'text-red-500'
                      ]"
                    >
                      {{ cert.days_until_expiry }} days
                    </span>
                  </div>
                </div>
              </div>
              <div v-else class="text-sm text-muted">
                No certificate information available
              </div>
            </div>

            <div class="p-3 rounded-lg bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20">
              <div class="flex gap-2">
                <ExclamationTriangleIcon class="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div class="text-sm text-amber-700 dark:text-amber-400">
                  <p class="font-medium mb-1">Important:</p>
                  <ul class="list-disc list-inside space-y-1 text-xs">
                    <li>This will request a new certificate from Let's Encrypt</li>
                    <li>Let's Encrypt has rate limits (5 certificates per domain per week)</li>
                    <li>Nginx will be automatically reloaded after renewal</li>
                    <li>This may take 60-90 seconds to complete</li>
                  </ul>
                </div>
              </div>
            </div>

            <!-- Dry Run Checkbox -->
            <div class="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700">
              <input
                type="checkbox"
                id="dryRunCheckbox"
                v-model="dryRunMode"
                class="h-4 w-4 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500"
              />
              <label for="dryRunCheckbox" class="text-sm text-primary cursor-pointer">
                <span class="font-medium">Dry run</span>
                <span class="text-muted ml-1">(test without making changes)</span>
              </label>
            </div>
          </div>

          <!-- Renewal Result -->
          <div v-else class="space-y-4">
            <div
              :class="[
                'p-4 rounded-lg',
                renewalResult.success
                  ? 'bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30'
                  : 'bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30'
              ]"
            >
              <div class="flex items-center gap-2 mb-2">
                <CheckCircleIcon v-if="renewalResult.success" class="h-5 w-5 text-emerald-500" />
                <XCircleIcon v-else class="h-5 w-5 text-red-500" />
                <span
                  :class="[
                    'font-medium',
                    renewalResult.success ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400'
                  ]"
                >
                  {{ renewalResult.success ? 'Renewal Successful' : 'Renewal Failed' }}
                </span>
              </div>
              <p class="text-sm text-secondary">{{ renewalResult.message }}</p>
              <div v-if="renewalResult.nginx_reloaded" class="mt-2 text-xs text-emerald-600 dark:text-emerald-400">
                Nginx has been reloaded to apply the new certificate.
              </div>
            </div>

            <!-- Detailed Output - Always shown -->
            <div v-if="renewalResult.renewal_output" class="mt-4">
              <p class="text-sm text-secondary mb-2">Certbot Output:</p>
              <pre class="p-3 rounded-lg bg-gray-900 text-gray-100 text-xs overflow-auto max-h-64 font-mono whitespace-pre-wrap">{{ renewalResult.renewal_output }}</pre>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-3 justify-end mt-6">
            <button
              @click="closeRenewModal"
              :disabled="renewingCert"
              class="btn btn-secondary"
            >
              {{ renewalResult ? 'Close' : 'Cancel' }}
            </button>
            <button
              v-if="!renewalResult"
              @click="renewCertificate"
              :disabled="renewingCert"
              :class="[
                'btn flex items-center gap-2',
                dryRunMode ? 'btn-secondary' : 'btn-primary'
              ]"
            >
              <ArrowPathIcon v-if="renewingCert" class="h-4 w-4 animate-spin" />
              {{ renewingCert ? 'Running...' : (dryRunMode ? 'Run Dry Test' : 'Force Renew') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
