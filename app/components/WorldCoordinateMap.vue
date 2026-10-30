<script setup lang="ts">
import type { WorldNode, WorldSite } from '~~/shared/types/world'
const props = defineProps<{ sites: WorldSite[]; nodes: WorldNode[]; bounds: [number, number, number, number]; gridMeters: number; selected: string }>()
const emit = defineEmits<{ select: [id: string] }>()
const id = useId()
const scale = computed(() => Math.min(680 / (props.bounds[1] - props.bounds[0]), 688 / (props.bounds[3] - props.bounds[2])))
const x = (value: number) => (value - props.bounds[0]) * scale.value + 60
const y = (value: number) => (value - props.bounds[2]) * scale.value + 50
</script>
<template>
  <div class="island-map-scroll" tabindex="0" aria-label="Координатная карта; подробности доступны в списке районов">
    <svg viewBox="0 0 800 800" role="group" :aria-labelledby="`${id}-title ${id}-desc`">
      <title :id="`${id}-title`">Ресурсы и районы</title><desc :id="`${id}-desc`">Ноды из сейва; пунктирные конверты — предлагаемые площадки, не подтверждённый рельеф.</desc>
      <defs><pattern :id="`${id}-grid`" :width="gridMeters * scale" :height="gridMeters * scale" patternUnits="userSpaceOnUse"><path :d="`M${gridMeters * scale} 0H0V${gridMeters * scale}`" fill="none" stroke="var(--line)" stroke-width="1" /></pattern></defs>
      <rect x="40" y="30" width="720" height="710" :fill="`url(#${id}-grid)`" />
      <g v-for="(site, index) in sites" :key="site.id" class="map-site" role="button" tabindex="0" :aria-label="site.label" :aria-pressed="selected === site.id" @click="emit('select', site.id)" @keydown.enter.prevent="emit('select', site.id)" @keydown.space.prevent="emit('select', site.id)">
        <title>{{ site.label }} · {{ site.width }} × {{ site.depth }} м</title>
        <rect :x="x(site.x - site.width / 2)" :y="y(site.y - site.depth / 2)" :width="site.width * scale" :height="site.depth * scale" :fill="selected === site.id ? 'var(--accent-soft)' : 'var(--surface)'" :stroke="selected === site.id ? 'var(--accent)' : 'var(--control-border)'" :stroke-width="selected === site.id ? 3 : 1.5" stroke-dasharray="5 3" />
        <text :x="x(site.x)" :y="y(site.y)" text-anchor="middle" fill="var(--ink)" font-size="14" pointer-events="none">{{ index + 1 }}</text>
      </g>
      <g v-for="node in nodes" :key="node.id" pointer-events="none"><title>{{ node.id }} · {{ node.resource }} · {{ node.purity }}</title><circle :cx="x(node.xyz_m[0]!)" :cy="y(node.xyz_m[1]!)" r="5" fill="var(--success)" /><text :x="x(node.xyz_m[0]!) + 8" :y="y(node.xyz_m[1]!) - 8" fill="var(--ink)" font-size="12">{{ node.id.replace('BP_ResourceNode_', '') }}</text></g>
      <text x="45" y="775" fill="var(--muted)" font-size="14">● Нода из сейва · ▭ Район · сетка {{ gridMeters }} м</text>
    </svg>
  </div>
</template>
