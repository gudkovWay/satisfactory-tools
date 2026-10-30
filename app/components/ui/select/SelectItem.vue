<script setup lang="ts">
import { type HTMLAttributes, computed } from 'vue'
import { SelectItem as RekaSelectItem, SelectItemIndicator, type SelectItemProps, SelectItemText, useForwardProps } from 'reka-ui'
import { Check } from '@lucide/vue'
import { cn } from '~/lib/utils/shadcn'

const props = defineProps<SelectItemProps & { class?: HTMLAttributes['class'] }>()
const delegatedProps = computed(() => {
  const { class: _, ...delegated } = props
  return delegated
})
const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <RekaSelectItem v-bind="forwardedProps" data-slot="select-item" :class="cn(
    'relative flex min-h-11 w-full min-w-0 cursor-pointer items-center rounded-lg py-2 pr-3 pl-9 text-sm font-normal text-foreground outline-none select-none data-[highlighted]:bg-selection data-[highlighted]:text-branded data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
    props.class,
  )">
    <span class="absolute left-3 flex size-4 items-center justify-center"><SelectItemIndicator><Check aria-hidden="true" class="size-4" /></SelectItemIndicator></span>
    <SelectItemText class="min-w-0 whitespace-normal break-words"><slot /></SelectItemText>
  </RekaSelectItem>
</template>
