<script setup lang="ts">
import type { ProjectDocument } from '~~/shared/types/project'

const props = defineProps<{ project: ProjectDocument }>()
const { horizontal, vertical, floorHeight, coordinateLabel } = useConstructionUnits(() => props.project)
const route = useRoute()
const atlas = computed(() => props.project.zoneAtlas)
const views = computed(() => atlas.value?.views ?? [])
const selected = computed(() => views.value.find(view => view.id === route.query.zone)
  ?? views.value.find(view => view.id === 'F1-00') ?? views.value[0])
const selectedIndex = computed(() => views.value.findIndex(view => view.id === selected.value?.id))
const levelViews = computed(() => views.value.filter(view => view.levelId === selected.value?.levelId))
const level = computed(() => atlas.value?.levels.find(item => item.id === selected.value?.levelId))
const zoneLevelOptions = computed(() => (atlas.value?.levels ?? []).map(item => ({ value: item.id, label: `${item.id} · ${item.name}` })))
const zoneViewOptions = computed(() => levelViews.value.map(view => ({ value: view.id, label: `${view.id} · ${view.title}` })))
const processMap = computed(() => new Map((props.project.production?.processes ?? []).map(item => [item.id, item])))
const parts = computed(() => props.project.parts.items.filter(part => selected.value?.partCodes.includes(part.code)))
const placements = computed(() => props.project.placements.filter(item => selected.value?.placementIds.includes(item.id)))
const placementRows = computed(() => placements.value.map(item => [item.id, item.processId, item.levelId,
  `${horizontal(item.x)} / ${horizontal(item.y)} / ${vertical(item.z)}`, `${formatRate(item.clock * 100, 6)}%`]))
const referenceIds = computed(() => new Set([...(selected.value?.referenceIds ?? []),
  'ficsit-stairs', 'painted-beam', 'railing', 'wall-outlet']))
const references = computed(() => (atlas.value?.references ?? []).filter(item => referenceIds.value.has(item.id)))
const copied = ref(false)
const copyError = ref('')
const imagePending = ref(false)
const imageError = ref(false)
const picture = useTemplateRef<HTMLImageElement>('picture')

function syncImage() {
  imagePending.value = picture.value ? !picture.value.complete : false
  imageError.value = Boolean(picture.value?.complete && !picture.value.naturalWidth)
}
onMounted(syncImage)
watch(() => selected.value?.id, async () => {
  copied.value = false
  copyError.value = ''
  imagePending.value = true
  imageError.value = false
  await nextTick()
  syncImage()
})
function choose(id: string) {
  if (views.value.some(view => view.id === id)) {
    void navigateTo({ path: route.path, query: { ...route.query, zone: id } })
  }
}
function chooseLevel(value: string | number) {
  const view = views.value.find(item => item.levelId === value)
  if (view) choose(view.id)
}
function move(offset: number) {
  const view = views.value[selectedIndex.value + offset]
  if (view) choose(view.id)
}
async function copyLink() {
  if (!selected.value) return
  const url = new URL(window.location.href)
  url.searchParams.set('zone', selected.value.id)
  try { await navigator.clipboard.writeText(url.href); copied.value = true; copyError.value = '' }
  catch { copyError.value = `Скопируй ссылку вручную: ${url.href}` }
}
const zoom = useTemplateRef<HTMLDialogElement>('zoom')
let zoomTrigger: HTMLElement | null = null
function openZoom(event: Event) {
  zoomTrigger = event.currentTarget as HTMLElement
  zoom.value?.showModal()
}
function closeZoom() { zoom.value?.close() }
function restoreFocus() { zoomTrigger?.focus(); zoomTrigger = null }
</script>

<template>
  <section v-if="atlas && selected" class="panel zone-atlas" aria-labelledby="zone-atlas-title">
    <header class="zone-intro">
      <h2 id="zone-atlas-title">Виды зон</h2>
      <p class="muted">AI-виды для ориентира. Точные размеры и координаты ниже.</p>
    </header>
    <div class="split zone-selectors">
      <div class="field">
        <label for="zone-level">Уровень или инфраструктура</label>
        <TheSelect trigger-id="zone-level" :model-value="selected.levelId" :options="zoneLevelOptions" @update:model-value="chooseLevel" />
      </div>
      <div class="field">
        <label for="zone-view">Рабочая зона</label>
        <TheSelect trigger-id="zone-view" :model-value="selected.id" :options="zoneViewOptions" @update:model-value="choose(String($event))" />
      </div>
    </div>
    <div class="zone-filmstrip" role="group" aria-label="Виды выбранного уровня">
      <button v-for="view in levelViews" :key="view.id" class="zone-thumbnail" type="button" :aria-pressed="view.id === selected.id" @click="choose(view.id)">
        <img :src="view.image.src" alt="" :width="152" :height="101" loading="lazy">
        <span><strong>{{ view.id }}</strong> {{ view.title }}</span>
      </button>
    </div>
    <div class="section-heading"><h3 class="zone-title">{{ selected.id }} · {{ selected.title }}</h3><span class="fine" aria-live="polite">Вид {{ selectedIndex + 1 }} из {{ views.length }}</span></div>
    <figure class="zone-picture">
      <p v-if="imagePending" role="status">Загружаем вид зоны.</p>
      <p v-if="imageError" class="notice notice-warning" role="alert">Изображение не загрузилось. Инструкция и размерная привязка доступны ниже.</p>
      <img ref="picture" :src="selected.image.src" :alt="`${selected.id}: ${selected.title}. Приближённая AI-иллюстрация.`" :width="selected.width" :height="selected.height" @load="syncImage" @error="imagePending = false; imageError = true">
      <figcaption>{{ atlas.fidelity }}</figcaption>
    </figure>
    <p v-if="selected.variance" class="notice notice-warning">{{ constructionText(selected.variance) }}</p>
    <div class="button-row zone-actions">
      <Button :disabled="selectedIndex === 0" variant="outline" @click="move(-1)">Предыдущая зона</Button>
      <Button :disabled="selectedIndex === views.length - 1" variant="outline" @click="move(1)">Следующая зона</Button>
      <Button @click="openZoom">Увеличить вид зоны</Button>
      <Button variant="outline" @click="copyLink">{{ copied ? 'Ссылка скопирована' : 'Скопировать ссылку на зону' }}</Button>
      <a class="text-link" :href="selected.image.src" :download="`${selected.id}.webp`">Скачать вид</a>
      <a class="text-link" :href="selected.sheet.src" download>Скачать исходный лист</a>
    </div>
    <p v-if="copyError" role="status" class="fine">{{ copyError }}</p>
    <div class="split zone-instructions">
      <section><h3>Порядок сборки</h3><ol><li v-for="(action, index) in selected.actions" :key="index">{{ constructionText(action) }}</li></ol></section>
      <section><h3>Коммуникации и проходы</h3><p>{{ constructionText(selected.network) }}</p><p v-if="level?.z !== null && level?.z !== undefined" class="fine">{{ level.id }} · пол {{ floorHeight(level.z) }}. Координаты машин локальные, не мировые.</p></section>
    </div>
    <section v-if="selected.groups.length" class="zone-processes" aria-label="Точные группы этой зоны">
      <article v-for="group in selected.groups" :key="group.processId" class="zone-process">
        <h3>{{ group.processId }} · {{ processMap.get(group.processId)?.recipeName }}</h3>
        <p><strong>{{ group.machines }} × {{ processMap.get(group.processId)?.machineName }}</strong>, одинаковая частота {{ formatRate((processMap.get(group.processId)?.clock ?? 0) * 100, 6) }}%.</p>
        <div class="split"><div><h4>Вход зоны в минуту</h4><FlowList :flows="group.inputs" /></div><div><h4>Выход зоны в минуту</h4><FlowList :flows="group.outputs" /></div></div>
        <p class="fine">На одну машину раздели потоки на {{ group.machines }}. Рецепт: <code>{{ processMap.get(group.processId)?.recipeKey }}</code>.</p>
      </article>
    </section>
    <p v-else class="fine">Это обзор или сервисная зона. Видимые соседние станки не прибавляются повторно к {{ project.placements.length }} производственным машинам.</p>
    <section v-if="selected.position || placements.length" class="zone-position">
      <h3>Точная привязка зоны</h3><p class="fine">Жёлтые ячейки на размерной сетке относятся к выбранным машинам. Числа и подключения бери отсюда, не из иллюстрации.</p>
      <img v-if="selected.position" :src="selected.position.src" :alt="selected.position.alt" width="850" height="360" loading="lazy">
      <DataTable v-if="placements.length" :columns="['Машина', 'Группа', 'Этаж', coordinateLabel, 'Частота']" :rows="placementRows" :caption="`Размещения ${selected.id}`" />
    </section>
    <section class="zone-parts"><h3>Детали для этой зоны</h3>
      <ul><li v-for="part in parts" :key="part.code"><strong>{{ part.code }}</strong> · {{ part.name }} <span class="fine">({{ part.mod }})</span><details><summary>Найти деталь {{ part.code }}</summary><p>{{ part.role }}</p><p class="recipe-path">{{ part.recipePath }}</p></details></li></ul>
      <NuxtLink class="text-link" :to="projectUrl(project.saveId, project.id, 'parts')">Вся спецификация проекта</NuxtLink>
    </section>
    <details class="zone-reference-details"><summary>Настоящие игровые референсы оборудования и деталей</summary><p class="fine">Это игровые иконки-референсы. Они не подтверждают точность модовых мешей, портов или AI-кадра.</p>
      <div class="zone-reference-grid"><figure v-for="reference in references" :key="reference.id"><img :src="reference.image.src" :alt="reference.name" width="128" height="128" loading="lazy"><figcaption><a class="text-link" :href="reference.sourceUrl" target="_blank" rel="noopener noreferrer">{{ reference.name }}</a></figcaption></figure></div>
    </details>
    <dialog ref="zoom" class="atlas-dialog zone-zoom" aria-labelledby="zone-zoom-title" @close="restoreFocus">
      <div class="dialog-heading"><h2 id="zone-zoom-title">{{ selected.id }} · {{ selected.title }}</h2><Button variant="outline" @click="closeZoom">Закрыть вид зоны</Button></div>
      <img :src="selected.image.src" :alt="selected.image.alt" :width="selected.width" :height="selected.height"><p class="fine">{{ atlas.fidelity }}</p>
    </dialog>
  </section>
</template>

<style scoped>
.zone-atlas { min-width: 0; }
.zone-intro, .zone-selectors, .zone-filmstrip, .zone-actions, .zone-instructions, .zone-processes, .zone-position, .zone-parts, .zone-reference-details { margin-bottom: 1.5rem; }
 .zone-filmstrip { display: flex; gap: .65rem; overflow-x: auto; padding: .25rem; }
 .zone-thumbnail { flex: 0 0 164px; border: 1px solid var(--control-border); border-radius: 9px; background: var(--surface); color: var(--ink); padding: .35rem; text-align: left; min-height: 44px; overflow: hidden; }
 .zone-thumbnail[aria-pressed="true"] { border-color: var(--accent); background: var(--accent-soft); }
 .zone-thumbnail img { width: 100%; height: 94px; object-fit: cover; border-radius: 5px; transition: transform 200ms var(--ease-out); }
 .zone-thumbnail span { display: block; padding: .5rem .35rem; font-size: .75rem; overflow-wrap: anywhere; }
.zone-title { font-size: 1.35rem; }
.zone-picture { margin: 0 0 1rem; padding: .65rem; background: var(--surface); border-radius: 14px; }
.zone-picture > img { width: 100%; max-height: 75vh; object-fit: contain; background: var(--surface-raised); border-radius: 9px; }
.zone-picture figcaption { margin-top: .6rem; font-size: .8125rem; color: var(--muted); }
.zone-instructions li + li, .zone-parts li + li { margin-top: .65rem; }
.zone-process { border-top: 1px solid var(--line); padding-block: 1.25rem; }
.zone-process p, .zone-parts p { overflow-wrap: anywhere; }
.zone-reference-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(min(100%,8rem),1fr)); gap: 1rem; margin-top: 1rem; }
.zone-reference-grid figure { margin: 0; min-width: 0; }
.zone-reference-grid img { height: 128px; object-fit: contain; }
.zone-reference-grid figcaption { margin-top: .5rem; font-size: .8125rem; }
.zone-zoom { width: min(80rem,calc(100vw - 2rem)); }
.zone-zoom > img { width: 100%; max-height: 72vh; object-fit: contain; }
@media (max-width: 649px) { .zone-selectors { grid-template-columns: repeat(2,minmax(0,1fr)); gap: .75rem; } .zone-selectors .field { font-size: .75rem; } }
@media print { .zone-selectors, .zone-filmstrip, .zone-actions { display: none; } }
</style>
