<script setup lang="ts">
import { ArrowUpRight, Layers } from '@lucide/vue'
import { useMediaQuery } from '@vueuse/core'
import type { ProjectDocument } from '~~/shared/types/project'
const props = defineProps<{ project: ProjectDocument }>()
const { floorHeight } = useConstructionUnits(() => props.project)
const floors = computed(() => (props.project.zoneAtlas?.levels ?? []).map(level => ({
  ...level,
  view: props.project.zoneAtlas?.views.find(view => view.levelId === level.id && view.id.endsWith('-overall'))
    ?? props.project.zoneAtlas?.views.find(view => view.levelId === level.id)
})).filter(level => Boolean(level.view)))
const selectedId = ref('')
const selected = computed(() => floors.value.find(floor => floor.id === selectedId.value) ?? floors.value[0])
const vertical = useMediaQuery('(min-width: 650px)')
function selectByKey(event: KeyboardEvent, index: number) {
  const forward = vertical.value ? 'ArrowDown' : 'ArrowRight'
  const backward = vertical.value ? 'ArrowUp' : 'ArrowLeft'
  if (![forward, backward, 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? floors.value.length - 1 : (index + (event.key === forward ? 1 : -1) + floors.value.length) % floors.value.length
  const floor = floors.value[next]
  if (floor) { selectedId.value = floor.id; document.getElementById(`floor-preview-${floor.id}`)?.focus() }
}
</script>

<template>
  <section v-if="selected?.view" class="floor-preview" aria-labelledby="floor-preview-heading">
    <div class="section-heading"><div><h2 id="floor-preview-heading">Завод по уровням</h2><p class="muted">Общие виды этажей и рабочие зоны.</p></div><Layers :size="24" class="muted" aria-hidden="true" /></div>
    <div class="floor-explorer">
      <div class="floor-tabs" role="tablist" aria-label="Уровни завода" :aria-orientation="vertical ? 'vertical' : 'horizontal'"><button v-for="(floor, index) in floors" :id="`floor-preview-${floor.id}`" :key="floor.id" type="button" role="tab" :tabindex="floor.id === selected.id ? 0 : -1" :aria-selected="floor.id === selected.id" aria-controls="floor-preview-panel" @click="selectedId = floor.id" @keydown="selectByKey($event, index)"><span class="floor-code">{{ floor.id }}</span><span>{{ floor.name }}</span><span class="floor-height">{{ floor.z == null ? '' : floorHeight(floor.z) }}</span></button></div>
      <div id="floor-preview-panel" class="floor-panel" role="tabpanel" :aria-labelledby="`floor-preview-${selected.id}`">
        <Transition name="picture" mode="out-in"><NuxtLink :key="selected.id" :to="{ path: projectUrl(project.saveId, project.id, 'drawings'), query: { zone: selected.view.id } }" class="floor-image"><img :src="selected.view.image.src" :alt="`${selected.name}. Приближённая AI-иллюстрация.`" width="1280" height="800" loading="lazy"><span class="floor-open">Открыть зону <ArrowUpRight :size="16" aria-hidden="true" /></span></NuxtLink></Transition>
        <p class="fine">AI-концепт уровня. Размеры и координаты бери из чертежей.</p>
      </div>
    </div>
  </section>
</template>
