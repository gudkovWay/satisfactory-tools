<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { useVModel } from '@vueuse/core'
import { cn } from '~/lib/utils/shadcn'

const props = withDefaults(defineProps<{
  defaultValue?: string | number
  modelValue?: string | number
  class?: HTMLAttributes['class']
  error?: boolean
  variant?: 'default' | 'filled'
}>(), { variant: 'default' })
const emits = defineEmits<{
  (e: 'update:modelValue', payload: string | number): void
}>()
const modelValue = useVModel(props, 'modelValue', emits, {
  passive: true,
  defaultValue: props.defaultValue,
})
</script>

<template>
  <input
    v-model="modelValue"
    data-slot="input"
    :aria-invalid="props.error || undefined"
    :class="cn(
      'atlas-input flex h-12 min-h-12 w-full min-w-0 rounded-lg border border-elements-border px-4 py-3 text-base font-normal text-foreground caret-foreground outline-none placeholder:text-sm placeholder:text-elements-foreground hover:border-foreground focus-visible:border-branded file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:cursor-not-allowed disabled:opacity-50 autofill:bg-created-background autofill:text-foreground',
      { 'bg-transparent': props.variant === 'default', 'bg-elements-background': props.variant === 'filled' },
      props.class,
      { 'border-destructive hover:border-destructive focus-visible:border-destructive': props.error },
    )"
  >
</template>
