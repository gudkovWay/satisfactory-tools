<script setup lang="ts">
import { type HTMLAttributes, computed } from 'vue'
import { SelectScrollUpButton as RekaSelectScrollUpButton, type SelectScrollUpButtonProps, useForwardProps } from 'reka-ui'
import { ChevronUp } from '@lucide/vue'
import { cn } from '~/lib/utils/shadcn'
const props = defineProps<SelectScrollUpButtonProps & { class?: HTMLAttributes['class'] }>()
const delegatedProps = computed(() => {
  const { class: _, ...delegated } = props
  return delegated
})
const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <RekaSelectScrollUpButton v-bind="forwardedProps" :class="cn('flex items-center justify-center bg-background py-1 text-label-foreground', props.class)"><slot><ChevronUp aria-hidden="true" class="size-4" /></slot></RekaSelectScrollUpButton>
</template>
