<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '~/lib/utils/shadcn'

defineOptions({ inheritAttrs: false })
const props = defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <div v-bind="$attrs" class="table-wrap data-table-region w-full max-w-full overflow-x-auto rounded-lg border border-based-border">
    <table :class="cn('w-full text-sm', props.class)"><slot /></table>
  </div>
</template>
