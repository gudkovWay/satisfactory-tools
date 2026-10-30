<script setup lang="ts">
import { type HTMLAttributes, computed } from 'vue'
import {
  SelectContent as RekaSelectContent, type SelectContentEmits, type SelectContentProps,
  SelectPortal, SelectViewport, useForwardPropsEmits,
} from 'reka-ui'
import SelectScrollDownButton from './SelectScrollDownButton.vue'
import SelectScrollUpButton from './SelectScrollUpButton.vue'
import { cn } from '~/lib/utils/shadcn'

defineOptions({ inheritAttrs: false })
const props = withDefaults(defineProps<SelectContentProps & { class?: HTMLAttributes['class'] }>(), { position: 'popper', sideOffset: 8, collisionPadding: 12 })
const emits = defineEmits<SelectContentEmits>()
const delegatedProps = computed(() => {
  const { class: _, ...delegated } = props
  return delegated
})
const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <SelectPortal>
    <RekaSelectContent v-bind="{ ...forwarded, ...$attrs }" data-slot="select-content" :class="cn(
      'relative z-50 max-h-(--reka-select-content-available-height) w-(--reka-select-trigger-width) min-w-0 max-w-[calc(100vw-1.5rem)] overflow-hidden rounded-xl border border-elements-border bg-background text-popover-foreground shadow-xl outline-none',
      props.class,
    )">
      <SelectScrollUpButton />
      <SelectViewport class="w-full p-1.5"><slot /></SelectViewport>
      <SelectScrollDownButton />
    </RekaSelectContent>
  </SelectPortal>
</template>

<style>
[data-slot="select-content"] { transform-origin: var(--reka-select-content-transform-origin); }
[data-slot="select-content"][data-state="open"] { animation: select-appear 240ms var(--ease-out); }
[data-slot="select-content"][data-state="closed"] { animation: select-disappear 160ms ease-in; }
@keyframes select-appear { from { opacity: 0; transform: translateY(-6px) scale(.97); } to { opacity: 1; transform: none; } }
@keyframes select-disappear { from { opacity: 1; transform: none; } to { opacity: 0; transform: translateY(-4px) scale(.98); } }
@media (prefers-reduced-motion: reduce) { [data-slot="select-content"][data-state] { animation: none; } }
</style>
