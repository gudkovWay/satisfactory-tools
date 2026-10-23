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
      'flex h-11 min-h-11 w-full min-w-0 rounded-md border border-elements-border px-3 py-2 text-base font-normal text-foreground caret-foreground outline-none transition-colors duration-150 placeholder:text-sm placeholder:text-elements-foreground hover:border-branded focus-visible:border-branded focus-visible:ring-2 focus-visible:ring-branded file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:cursor-not-allowed disabled:opacity-50 autofill:bg-created-background autofill:text-foreground motion-reduce:transition-none',
      { 'bg-transparent': props.variant === 'default', 'bg-elements-background': props.variant === 'filled' },
      props.class,
      { 'border-destructive hover:border-destructive focus-visible:border-destructive focus-visible:ring-destructive': props.error },
    )"
  >
</template>
