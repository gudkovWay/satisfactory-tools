<script setup lang="ts">
const world = useWorld()
const map = computed(() => world.value.manifest.map)
const nodes = computed(() => world.value.analyses.find(item => item.id === map.value?.nodeAnalysisId)?.nodes ?? [])
const sites = computed(() => world.value.analyses.find(item => item.id === map.value?.siteAnalysisId)?.sites ?? [])
const selected = ref(sites.value[0]?.id || '')
const active = computed(() => sites.value.find(site => site.id === selected.value) ?? sites.value[0])
const scale = computed(() => map.value ? Math.min(680 / (map.value.bounds[1] - map.value.bounds[0]), 688 / (map.value.bounds[3] - map.value.bounds[2])) : 1)
const x = (value: number) => (value - (map.value?.bounds[0] ?? 0)) * scale.value + 60
const y = (value: number) => (value - (map.value?.bounds[2] ?? 0)) * scale.value + 50
</script>
<template>
  <section v-if="map" class="world-district-map" aria-labelledby="island-map-heading">
    <div class="map-workspace"><div class="map-heading"><h2 id="island-map-heading">Ноды и районы</h2><span class="fine">X / Y, м · север {{ map.north }}</span></div>
      <div class="island-map-scroll" tabindex="0" aria-label="Координатная карта; подробности доступны в списке районов"><svg viewBox="0 0 800 800" role="img" aria-labelledby="map-title map-desc"><title id="map-title">Ресурсы и районы: {{ world.manifest.title }}</title><desc id="map-desc">Ноды из сейва; пунктирные конверты — предлагаемые площадки, не подтверждённый рельеф.</desc><defs><pattern id="island-grid" :width="map.gridMeters * scale" :height="map.gridMeters * scale" patternUnits="userSpaceOnUse"><path :d="`M${map.gridMeters * scale} 0H0V${map.gridMeters * scale}`" fill="none" stroke="var(--line)" stroke-width="1" /></pattern></defs><rect x="40" y="30" width="720" height="710" fill="url(#island-grid)" />
        <g v-for="(site, index) in sites" :key="site.id"><rect :x="x(site.x - site.width / 2)" :y="y(site.y - site.depth / 2)" :width="site.width * scale" :height="site.depth * scale" :fill="selected === site.id ? 'var(--accent-soft)' : 'var(--surface)'" :stroke="selected === site.id ? 'var(--accent)' : 'var(--control-border)'" stroke-dasharray="5 3" /><text :x="x(site.x)" :y="y(site.y)" text-anchor="middle" fill="var(--ink)" font-size="12">{{ index + 1 }}</text></g>
        <g v-for="node in nodes" :key="node.id"><circle :cx="x(node.xyz_m[0]!)" :cy="y(node.xyz_m[1]!)" r="5" fill="var(--success)" /><text :x="x(node.xyz_m[0]!) + 8" :y="y(node.xyz_m[1]!) - 8" fill="var(--ink)" font-size="11">{{ node.id.replace('BP_ResourceNode_', '') }}</text></g><text x="45" y="775" fill="var(--muted)" font-size="14">● Нода из сейва · ▭ Конверт · сетка {{ map.gridMeters }} м</text>
      </svg></div><p class="fine">{{ map.caption }}</p>
    </div>
    <div class="map-districts"><ol><li v-for="(site, index) in sites" :key="site.id"><button type="button" :aria-pressed="selected === site.id" @click="selected = site.id"><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ site.label }}</button></li></ol><article v-if="active" class="district-detail"><h3>{{ active.label }}</h3><p>{{ constructionText(active.role) }}</p><p class="fine">{{ active.width }} × {{ active.depth }} м · центр {{ formatRate(active.x) }} / {{ formatRate(active.y) }} · {{ active.verified ? 'позиция из сейва' : 'кандидат площадки' }}</p><NuxtLink v-if="active.projectId" class="text-link" :to="projectUrl(world.manifest, active.projectId)">Открыть строительный план →</NuxtLink></article></div>
  </section>
</template>
