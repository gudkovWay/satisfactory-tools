<script setup lang="ts">
const world = useWorld()
const map = computed(() => world.value.manifest.map)
const nodes = computed(() => world.value.analyses.find(item => item.id === map.value?.nodeAnalysisId)?.nodes ?? [])
const sites = computed(() => world.value.analyses.find(item => item.id === map.value?.siteAnalysisId)?.sites ?? [])
const selected = ref(sites.value[0]?.id || '')
const active = computed(() => sites.value.find(site => site.id === selected.value) ?? sites.value[0])
const view = ref('spatial')
const unavailable = ref(false)
</script>
<template>
  <section v-if="map" class="world-district-map" aria-labelledby="island-map-heading">
    <div class="map-workspace">
      <div class="map-heading"><div><p class="section-kicker">01 / ПРОСТРАНСТВО МИРА</p><h2 id="island-map-heading">Остров в плане.</h2></div><div class="map-view-controls" role="group" aria-label="Вид карты"><button type="button" :aria-pressed="view === 'spatial' && !unavailable" :disabled="unavailable" @click="view = 'spatial'">Объём</button><button type="button" :aria-pressed="view === 'coordinates' || unavailable" @click="view = 'coordinates'">Координаты</button></div></div>
      <WorldCoordinateMap v-if="view === 'coordinates' || unavailable" :sites="sites" :nodes="nodes" :bounds="map.bounds" :grid-meters="map.gridMeters" :selected="selected" @select="selected = $event" />
      <ClientOnly v-else><WorldScene :sites="sites" :nodes="nodes" :bounds="map.bounds" :selected="selected" @select="selected = $event" @unavailable="unavailable = true" /><template #fallback><WorldCoordinateMap :sites="sites" :nodes="nodes" :bounds="map.bounds" :grid-meters="map.gridMeters" :selected="selected" @select="selected = $event" /></template></ClientOnly>
      <div v-if="view === 'spatial' && !unavailable" class="print-coordinate-map"><WorldCoordinateMap :sites="sites" :nodes="nodes" :bounds="map.bounds" :grid-meters="map.gridMeters" :selected="selected" @select="selected = $event" /></div>
      <p v-if="unavailable" class="fine" role="status">Объёмная графика недоступна. Координатная карта и все районы работают без WebGL.</p>
      <p class="map-disclosure">{{ map.caption }} <span v-if="view === 'spatial' && !unavailable">Высота блоков условная: это указатель площадок, не модель рельефа.</span></p>
    </div>
    <div class="map-districts"><div class="district-index-heading"><span>Районы острова</span><span>{{ String(sites.length).padStart(2, '0') }}</span></div><ol><li v-for="(site, index) in sites" :key="site.id"><button type="button" :aria-pressed="selected === site.id" @click="selected = site.id"><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ site.label }}</button></li></ol><article v-if="active" class="district-detail" aria-live="polite"><p class="section-kicker">ВЫБРАННАЯ ПЛОЩАДКА</p><Transition name="district" mode="out-in"><div :key="active.id"><h3>{{ active.label }}</h3><p>{{ constructionText(active.role) }}</p><p class="fine">{{ active.width }} × {{ active.depth }} м · центр {{ formatRate(active.x) }} / {{ formatRate(active.y) }} · {{ active.verified ? 'позиция из сейва' : 'кандидат площадки' }}</p><NuxtLink v-if="active.projectId" class="text-link" :to="projectUrl(world.manifest, active.projectId)">Открыть строительный план ↗</NuxtLink></div></Transition></article></div>
  </section>
</template>
