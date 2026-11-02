<script setup lang="ts">
import type { CampusConnection, CampusEndpoint, Drawing, ProjectDocument } from '~~/shared/types/project'

const props = defineProps<{ project: ProjectDocument; drawing: Drawing }>()
const world = useWorld()
const uid = useId()
const selected = defineModel<string>({ default: '' })
const descriptor = computed(() => props.drawing.id.match(/campus-(freight|power)(?:-(.+))?-(\d+)$/))
const power = computed(() => descriptor.value?.[1] === 'power')
const state = computed(() => props.drawing.networkState ?? descriptor.value?.[2] ?? 'steady')
const edges = computed(() => {
  const records = power.value ? props.project.layout?.powerConnections : props.project.layout?.externalLinks
  const page = Math.max(1, Number(descriptor.value?.[3] ?? 1))
  return (records ?? []).filter(edge => edge.operatingStates?.includes(state.value))
    .sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0).slice((page - 1) * 6, page * 6)
})
const active = computed(() => edges.value.find(edge => edge.id === selected.value) ?? edges.value[0])
watch(() => props.drawing.id, () => { selected.value = '' })
const bounds = computed(() => {
  const points = edges.value.flatMap(edge => edge.pointsWorldXYRelativeZ)
  if (!points.length) return { x: 0, y: 0, width: 1, height: 1 }
  const xs = points.map(point => point[0]), ys = points.map(point => point[1])
  return { x: Math.min(...xs), y: Math.min(...ys), width: Math.max(1, Math.max(...xs) - Math.min(...xs)), height: Math.max(1, Math.max(...ys) - Math.min(...ys)) }
})
const scale = computed(() => Math.min(620 / bounds.value.width, 360 / bounds.value.height))
const x = (value: number) => 70 + (620 - bounds.value.width * scale.value) / 2 + (value - bounds.value.x) * scale.value
const y = (value: number) => 70 + (360 - bounds.value.height * scale.value) / 2 + (bounds.value.y + bounds.value.height - value) * scale.value
function points(edge: CampusConnection) { return edge.pointsWorldXYRelativeZ.map(point => `${x(point[0])},${y(point[1])}`).join(' ') }
function endpoint(edge: CampusConnection, side: 'from' | 'to') {
  const endpoint: CampusEndpoint = edge[side] ?? {}
  const projectId = endpoint.projectId ?? edge[`${side}ProjectId`]
  const project = world.value.manifest.projects.find(item => item.id === projectId)
  const place = endpoint.placementId ?? edge[`${side}PlacementId`] ?? endpoint.interfaceId ?? edge[`${side}InterfaceId`]
  return [project?.title.replace(/^Прежняя редакция · /, '') ?? projectId, place].filter(Boolean).join(' · ')
}
function rate(edge: CampusConnection) { return edge.stateRates?.[state.value] ?? edge.rate }
function label(edge: CampusConnection) { return edge.itemId ? atlasLabel(edge.itemId) : `${endpoint(edge, 'from')} ↔ ${endpoint(edge, 'to')}` }
const activePoints = computed(() => active.value?.pointsWorldXYRelativeZ.map((point, index) => [String(index + 1), ...point.map(value => formatRate(value, 6))]) ?? [])
</script>

<template>
  <section class="campus-sheet" :aria-labelledby="`${uid}-heading`">
    <header class="campus-sheet-heading"><h4 :id="`${uid}-heading`">{{ power ? 'Питание заводов' : 'Материальные соединения' }}</h4><span>{{ atlasLabel(state) }}</span></header>
    <div v-if="!edges.length" class="empty-state">В данных нет линий для этого листа и режима.</div>
    <template v-else>
      <div class="campus-sheet-workspace">
        <div class="campus-line-list" role="group" aria-label="Линии на чертеже">
          <button v-for="(edge, index) in edges" :key="edge.id" type="button" :aria-pressed="active?.id === edge.id" @click="selected = edge.id"><span>{{ index + 1 }}</span><span>{{ label(edge) }}<small v-if="rate(edge) !== undefined">{{ formatRate(rate(edge)!) }} шт/мин</small></span></button>
        </div>
        <svg viewBox="0 0 760 500" role="img" :aria-labelledby="`${uid}-title ${uid}-desc`">
          <title :id="`${uid}-title`">{{ power ? 'Схема электроснабжения' : 'Схема доставки материалов' }}</title>
          <desc :id="`${uid}-desc`">{{ edges.length }} линий. Выбранная линия выделена. Точные координаты доступны под схемой.</desc>
          <defs><marker :id="`${uid}-arrow`" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="var(--accent)" /></marker></defs>
          <path d="M35 100V45H90" fill="none" stroke="var(--muted)" stroke-width="1.5" /><text x="20" y="35" fill="var(--muted)" font-size="14">Y</text><text x="98" y="49" fill="var(--muted)" font-size="14">X</text>
          <polyline v-for="edge in edges.filter(edge => edge.id !== active?.id)" :key="edge.id" :points="points(edge)" fill="none" stroke="var(--control-border)" stroke-width="2" />
          <polyline v-if="active" :points="points(active)" fill="none" stroke="var(--accent)" stroke-width="3" :marker-end="power ? undefined : `url(#${uid}-arrow)`" />
          <g v-for="(edge, index) in edges" :key="`${edge.id}-number`"><circle :cx="x(edge.pointsWorldXYRelativeZ[0]![0])" :cy="y(edge.pointsWorldXYRelativeZ[0]![1])" r="12" fill="var(--surface)" :stroke="active?.id === edge.id ? 'var(--accent)' : 'var(--control-border)'" /><text :x="x(edge.pointsWorldXYRelativeZ[0]![0])" :y="y(edge.pointsWorldXYRelativeZ[0]![1]) + 5" text-anchor="middle" fill="var(--ink)" font-size="14">{{ index + 1 }}</text></g>
          <g v-if="active"><g v-for="(point, index) in active.pointsWorldXYRelativeZ" :key="index"><rect :x="x(point[0]) - 3" :y="y(point[1]) - 3" width="6" height="6" fill="var(--accent)" /><title>Точка {{ index + 1 }}: {{ point.join(', ') }} м</title></g></g>
          <text x="35" y="480" fill="var(--muted)" font-size="14">Координаты мира · метры</text>
        </svg>
      </div>
      <div v-if="active" class="campus-line-detail"><strong>{{ label(active) }}</strong><p>{{ endpoint(active, 'from') }} {{ power ? '↔' : '→' }} {{ endpoint(active, 'to') }}</p><p v-if="rate(active) !== undefined">Поток: {{ formatRate(rate(active)!) }} шт/мин<span v-if="active.capacity"> · Предел линии: {{ formatRate(active.capacity) }} шт/мин</span></p><p v-else-if="active.schematicLength_m !== undefined">Длина по схеме: {{ formatRate(active.schematicLength_m, 2) }} м</p>
        <details class="reference-disclosure"><summary>Координаты и данные линии</summary><p class="fine">X и Y относятся к миру. Z отсчитывается от общего уровня строительства; абсолютная высота не задана. Пересечение линий на виде сверху не означает соединение.</p><p class="fine">Линия: {{ active.id }} · Проект учёта: {{ active.ownerProjectId }}</p><DataTable :columns="['Точка', 'X, м', 'Y, м', 'Z, м']" :rows="activePoints" caption="Вершины выбранной линии" /></details>
      </div>
    </template>
  </section>
</template>

<style scoped>
.campus-sheet { width: 100%; min-width: 0; color: var(--ink); background: var(--surface); }
.campus-sheet-heading { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: .5rem; padding: 1rem; border-bottom: 1px solid var(--line); }
.campus-sheet-heading h4 { margin: 0; }.campus-sheet-heading>span { font-size: .8125rem; color: var(--muted); }
.campus-sheet-workspace { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(0, 3fr); }
.campus-line-list { padding: .5rem; border-right: 1px solid var(--line); }
.campus-line-list button { display: flex; align-items: start; gap: .5rem; width: 100%; min-height: 44px; padding: .7rem; text-align: left; font-size: .8125rem; border-radius: 4px; }
.campus-line-list button>span:first-child { min-width: 1rem; color: var(--muted); }.campus-line-list button[aria-pressed=true] { background: var(--accent-soft); }
.campus-line-list small { display: block; margin-top: .25rem; }
.campus-sheet svg { display: block; width: 100%; height: auto; min-width: 0; }
.campus-line-detail { border-top: 1px solid var(--line); padding: 1rem; font-size: .875rem; }.campus-line-detail p { margin: .5rem 0; }
@media (max-width: 700px) { .campus-sheet-workspace { grid-template-columns: minmax(0, 1fr); }.campus-line-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); border-right: 0; border-bottom: 1px solid var(--line); }.campus-line-list button { overflow-wrap: anywhere; }.campus-sheet svg { min-height: 230px; } }
</style>
