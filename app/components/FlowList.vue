<script setup lang="ts">
import type { Flow } from '~~/shared/types/project'
withDefaults(defineProps<{ flows: Flow[]; divisor?: number }>(), { divisor: 1 })
</script>
<template><ul v-if="flows.length" class="flow-list"><li v-for="flow in flows" :key="flow.itemId"><span>{{ flow.label }}</span><strong>{{ formatRate(flow.rate / divisor, 6) }} <span class="fine">{{ flow.unit }}</span></strong></li></ul><p v-else class="muted">Потоков нет.</p></template>
