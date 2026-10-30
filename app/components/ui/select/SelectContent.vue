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
const props = withDefaults(defineProps<SelectContentProps & { class?: HTMLAttributes['class'] }>(), { position: 'popper', sideOffset: 4, collisionPadding: 8 })
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
      'relative z-50 max-h-(--reka-select-content-available-height) w-(--reka-select-trigger-width) min-w-0 max-w-[calc(100vw-1rem)] overflow-hidden rounded-md border border-based-border bg-background text-popover-foreground shadow-md outline-none',
      props.class,
    )">
      <SelectScrollUpButton />
      <SelectViewport class="w-full p-1"><slot /></SelectViewport>
      <SelectScrollDownButton />
    </RekaSelectContent>
  </SelectPortal>
</template>

<style scoped>
[data-slot="select-content"][data-state="open"] { animation: select-appear 120ms ease-out; }
@keyframes select-appear { from { opacity: 0; transform: translateY(-3px); } to { opacity: 1; transform: translateY(0); } }
@media (prefers-reduced-motion: reduce) { [data-slot="select-content"][data-state="open"] { animation: none; } }
</style>
