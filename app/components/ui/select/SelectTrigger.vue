<script setup lang="ts">
import { type HTMLAttributes, computed } from 'vue'
import { SelectIcon, SelectTrigger as RekaSelectTrigger, type SelectTriggerProps, useForwardProps } from 'reka-ui'
import { ChevronDown } from '@lucide/vue'
import { cn } from '~/lib/utils/shadcn'

const props = defineProps<SelectTriggerProps & { class?: HTMLAttributes['class'] }>()
const delegatedProps = computed(() => {
  const { class: _, ...delegated } = props
  return delegated
})
const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <RekaSelectTrigger v-bind="forwardedProps" data-slot="select-trigger" :class="cn(
    'atlas-select-trigger group flex min-h-12 w-full min-w-0 items-center justify-between gap-3 rounded-lg border border-elements-border bg-transparent px-4 py-3 text-base font-normal text-foreground outline-none hover:border-foreground focus-visible:border-branded disabled:cursor-not-allowed disabled:opacity-50 data-placeholder:text-elements-foreground data-[state=open]:border-branded',
    props.class,
  )">
    <slot />
    <SelectIcon as-child><ChevronDown aria-hidden="true" class="size-4 shrink-0 text-label-foreground transition-transform duration-300 ease-[cubic-bezier(.22,1,.36,1)] group-data-[state=open]:rotate-180 motion-reduce:transition-none" /></SelectIcon>
  </RekaSelectTrigger>
</template>
