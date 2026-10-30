<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'
import { useResizeObserver } from '@vueuse/core'
const props = defineProps<{ options: Array<{ label: string; to: RouteLocationRaw }>; selected: number }>()
const track = useTemplateRef<HTMLElement>('track')
const indicator = ref<{ width: string; transform: string }>()
async function measure() {
  await nextTick()
  const active = track.value?.querySelector<HTMLElement>('[aria-current="page"]')
  if (active) indicator.value = { width: `${active.offsetWidth}px`, transform: `translateX(${active.offsetLeft}px)` }
}
useResizeObserver(track, measure)
watch(() => props.selected, measure)
onMounted(measure)
</script>

<template>
  <nav ref="track" class="route-segments" aria-label="Представление проекта">
    <span v-if="indicator" class="segment-indicator" :style="indicator" aria-hidden="true" />
    <NuxtLink v-for="(option, index) in options" :key="index" :to="option.to" :aria-current="index === selected ? 'page' : undefined">{{ option.label }}</NuxtLink>
  </nav>
</template>
