<script setup lang="ts">
import { SelectValue as RekaSelectValue, type SelectValueProps } from 'reka-ui'
const props = defineProps<SelectValueProps>()
</script>

<template>
  <RekaSelectValue v-bind="props"><slot /></RekaSelectValue>
</template>
