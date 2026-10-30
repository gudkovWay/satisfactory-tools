<script setup lang="ts">
import { type HTMLAttributes, computed } from 'vue'
import { SelectScrollDownButton as RekaSelectScrollDownButton, type SelectScrollDownButtonProps, useForwardProps } from 'reka-ui'
import { ChevronDown } from '@lucide/vue'
import { cn } from '~/lib/utils/shadcn'
const props = defineProps<SelectScrollDownButtonProps & { class?: HTMLAttributes['class'] }>()
const delegatedProps = computed(() => {
  const { class: _, ...delegated } = props
  return delegated
})
const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <RekaSelectScrollDownButton v-bind="forwardedProps" :class="cn('flex items-center justify-center bg-background py-1 text-label-foreground', props.class)"><slot><ChevronDown aria-hidden="true" class="size-4" /></slot></RekaSelectScrollDownButton>
</template>
