<!-- frontend/src/components/PortLegend.vue -->
<script setup>
// No props needed - static legend
</script>

<template>
  <div class="port-legend flex items-center justify-center gap-6 py-3 px-4 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm">
    <div class="flex items-center gap-2">
      <span class="w-3 h-3 rounded-full bg-red-500"></span>
      <span class="text-secondary">In Use</span>
    </div>
    <div class="flex items-center gap-2">
      <span class="w-3 h-3 rounded-full bg-gray-400"></span>
      <span class="text-secondary">Available</span>
    </div>
    <div class="flex items-center gap-2">
      <span class="w-3 h-3 rounded-full bg-blue-500"></span>
      <span class="text-secondary">Assigned/Off</span>
    </div>
    <div class="flex items-center gap-2">
      <span class="w-3 h-3 rounded-full bg-emerald-500"></span>
      <span class="text-secondary">Active (timer)</span>
    </div>
    <div class="flex items-center gap-2">
      <span class="w-3 h-3 rounded-full bg-yellow-500"></span>
      <span class="text-secondary">Error</span>
    </div>
  </div>
</template>
