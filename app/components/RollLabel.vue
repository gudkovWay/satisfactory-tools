<script setup lang="ts">
defineProps<{ text: string }>()
</script>
<template><span class="roll-label"><span>{{ text }}</span><span aria-hidden="true">{{ text }}</span></span></template>
