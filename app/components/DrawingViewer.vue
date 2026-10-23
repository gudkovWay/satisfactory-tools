<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Drawing, Level, ProjectDocument } from '~~/shared/types/project'

const props = defineProps<{ project: ProjectDocument }>()
const { blockGrid, horizontal, vertical, floorHeight } = useConstructionUnits(() => props.project)

const route = useRoute()

const familyOrder: Drawing['family'][] = ['floors', 'volumes', 'technical', 'facades', 'assembly']
const familyLabels: Record<Drawing['family'], string> = {
  floors: 'Планы этажей',
  volumes: 'Объёмы',
  technical: 'Технические этажи',
  facades: 'Фасады',
  assembly: 'Сборка и генплан',
}

function firstQueryValue(value: unknown): string | null {
  if (typeof value === 'string') return value
  if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  return null
}

const requestedDrawing = props.project.drawings.find(
  drawing => drawing.id === firstQueryValue(route.query.drawing)
)

const familyFilter = ref<string>('all')
const levelFilter = ref<string>('all')
const selectedId = ref<string>(requestedDrawing?.id ?? '')

const availableFamilies = computed(() =>
  familyOrder.filter(family => props.project.drawings.some(drawing => drawing.family === family))
)
const familyOptions = computed(() => [{ value: 'all', label: 'Все семейства' }, ...availableFamilies.value.map(family => ({ value: family, label: familyLabels[family] }))])

const levelMap = computed(() => new Map(props.project.levels.map(level => [level.id, level])))
const processNames = computed(() => new Map(
  (props.project.production?.processes ?? []).map(process => [
    process.id,
    `${process.recipeName} (${process.machineName})`,
  ])
))

const levelOptions = computed(() => {
  const used = new Set(
    props.project.drawings
      .map(drawing => drawing.levelId)
      .filter((levelId): levelId is string => Boolean(levelId))
  )
  return props.project.levels.filter(level => used.has(level.id))
})
const levelSelectOptions = computed(() => [{ value: 'all', label: 'Все этажи' }, ...levelOptions.value.map(level => ({ value: level.id, label: `${level.id} · ${level.name}` }))])

const visibleDrawings = computed(() => props.project.drawings.filter(drawing => {
  const familyMatches = familyFilter.value === 'all' || drawing.family === familyFilter.value
  const levelMatches = levelFilter.value === 'all' || drawing.levelId === levelFilter.value
  return familyMatches && levelMatches
}))

const selectedDrawing = computed<Drawing | null>(() => {
  const visible = visibleDrawings.value
  return visible.find(drawing => drawing.id === selectedId.value) ?? visible[0] ?? null
})

watch([familyFilter, levelFilter], () => {
  const visible = visibleDrawings.value
  if (visible.length && !visible.some(drawing => drawing.id === selectedId.value)) {
    selectedId.value = visible[0]?.id ?? ''
  }
})

watch(() => route.query.drawing, rawValue => {
  const id = firstQueryValue(rawValue)
  if (!id) return
  const drawing = props.project.drawings.find(candidate => candidate.id === id)
  if (!drawing) return
  selectedId.value = drawing.id
  if (!visibleDrawings.value.some(candidate => candidate.id === drawing.id)) {
    familyFilter.value = drawing.family
    levelFilter.value = 'all'
  }
})

function selectDrawing(id: string) {
  const drawing = props.project.drawings.find(candidate => candidate.id === id)
  if (!drawing) return
  selectedId.value = drawing.id
  void navigateTo({ path: route.path, query: { ...route.query, drawing: drawing.id } }, { replace: true })
}

const conceptAsset = computed(() => props.project.overview.concept ?? null)
const isConcept = computed(() =>
  Boolean(conceptAsset.value && selectedDrawing.value && conceptAsset.value.src === selectedDrawing.value.svg)
)

const disclosure = computed(() => blockGrid.value
  ? 'X/Y в фундаментах CC Block 8x8x2, H в слоях толщины блока. Дробные центры не округлять.'
  : 'Показана инженерная разметка. Размеры в метрах.')
const conceptDisclosure = computed(() => {
  if (!isConcept.value || !conceptAsset.value) return ''
  return `ИИ-концепт, не точная сборка: ${conceptAsset.value.caption}`
})

const captionText = computed(() => {
  if (!selectedDrawing.value) return ''
  return [
    selectedDrawing.value.caption,
    disclosure.value,
    conceptDisclosure.value,
  ].filter(Boolean).join(' ')
})

const imageAlt = computed(() => {
  if (!selectedDrawing.value) return ''
  const base = `${selectedDrawing.value.label}: ${selectedDrawing.value.caption}. Инженерная схема.`
  return isConcept.value ? `${base} ИИ-концепт, не точная сборка.` : base
})

const detailLevel = computed<Level | null>(() => {
  const levelId = selectedDrawing.value?.levelId
    ?? (levelFilter.value !== 'all' ? levelFilter.value : null)
  if (!levelId) return null
  return levelMap.value.get(levelId) ?? null
})

const levelPlacements = computed(() => {
  if (!detailLevel.value) return []
  return props.project.placements.filter(placement => placement.levelId === detailLevel.value?.id)
})


function percent(value: number) {
  return Number.isFinite(value) ? `${(value * 100).toFixed(1).replace('.', ',')}%` : 'нет данных'
}

function processLabel(id: string) {
  return processNames.value.get(id) ?? id
}

const placementColumns = computed(() => [
  'Машина', 'Группа', 'Тип',
  blockGrid.value ? 'X, ф.' : 'X, м',
  blockGrid.value ? 'Y, ф.' : 'Y, м',
  blockGrid.value ? 'H, сл.' : 'Z, м',
  blockGrid.value ? 'Ширина / глубина, ф.; высота, сл.' : 'Ширина / глубина / высота, м',
  'Частота',
])
const placementRows = computed(() => levelPlacements.value.map(placement => [
  placement.id,
  processLabel(placement.processId),
  placement.kind,
  horizontal(placement.x),
  horizontal(placement.y),
  vertical(placement.z),
  `${horizontal(placement.width)} × ${horizontal(placement.depth)} × ${vertical(placement.height)}`,
  percent(placement.clock),
]))

const zoomDialog = ref<HTMLDialogElement | null>(null)
let zoomTrigger: HTMLElement | null = null

function openZoom(event?: Event) {
  const target = event?.currentTarget
  zoomTrigger = target instanceof HTMLElement ? target : null
  const dialog = zoomDialog.value
  if (dialog && !dialog.open) dialog.showModal()
}

function closeZoom() {
  zoomDialog.value?.close()
}

function onZoomClose() {
  if (zoomTrigger?.isConnected) zoomTrigger.focus()
  zoomTrigger = null
}

function downloadName(url: string) {
  const withoutQuery = url.split('?')[0] ?? ''
  const withoutHash = withoutQuery.split('#')[0] ?? ''
  const slash = withoutHash.lastIndexOf('/')
  const name = slash >= 0 ? withoutHash.slice(slash + 1) : withoutHash
  return name || 'drawing'
}
</script>

<template>
  <section class="panel drawing-viewer" aria-labelledby="drawing-viewer-heading">
    <header class="stack">
      <h2 id="drawing-viewer-heading" class="section-heading">Размерные чертежи</h2>
      <p class="muted">Выбери вид и этаж. Размеры в метрах; это инженерные схемы, не игровые скриншоты.</p>
    </header>

    <div v-if="!project.drawings.length" class="empty-state">
      В опубликованном проекте нет чертежей.
    </div>

    <template v-else>
      <div class="split drawing-controls">
        <div class="field">
          <label for="drawing-family">Семейство</label>
          <TheSelect trigger-id="drawing-family" :model-value="familyFilter" :options="familyOptions" @update:model-value="familyFilter = String($event)" />
        </div>
        <div class="field">
          <label for="drawing-level">Этаж</label>
          <TheSelect trigger-id="drawing-level" :model-value="levelFilter" :options="levelSelectOptions" @update:model-value="levelFilter = String($event)" />
        </div>
      </div>

      <p class="muted drawing-count" role="status">
        Показано {{ visibleDrawings.length }} из {{ project.drawings.length }} чертежей.
      </p>

      <ul class="drawing-list" tabindex="0" aria-label="Список чертежей, прокрутка внутри списка">
        <li v-for="drawing in visibleDrawings" :key="drawing.id">
          <button
            type="button"
            class="drawing-choice"
            :class="{ 'drawing-choice-current': selectedDrawing?.id === drawing.id }"
            :aria-pressed="selectedDrawing?.id === drawing.id"
            @click="selectDrawing(drawing.id)"
          >
            <span class="drawing-choice-label">{{ drawing.label }}</span>
            <span class="fine">{{ drawing.caption }}</span>
          </button>
        </li>
      </ul>
      <p v-if="!visibleDrawings.length" class="empty-state">
        Для выбранного семейства и этажа нет чертежей. Сбросьте фильтр этажа или выберите
        «Все семейства».
      </p>

      <template v-if="selectedDrawing">
        <figure class="drawing-frame drawing-preview">
          <div class="drawing-image-wrap">
            <img
              :src="selectedDrawing.svg"
              :alt="imageAlt"
              loading="lazy"
              decoding="async"
            >
          </div>
          <figcaption>
            <strong>{{ selectedDrawing.label }}</strong>
            <span>{{ captionText }}</span>
          </figcaption>
        </figure>

        <div class="button-row drawing-actions">
          <Button type="button" class="min-h-11" @click="openZoom">Увеличить</Button>
          <a
            class="download-link"
            :href="selectedDrawing.svg"
            :download="downloadName(selectedDrawing.svg)"
          >
            Скачать SVG
          </a>
          <a
            v-if="selectedDrawing.png"
            class="download-link"
            :href="selectedDrawing.png"
            :download="downloadName(selectedDrawing.png)"
          >
            Скачать PNG
          </a>
        </div>

        <section v-if="detailLevel" class="stack level-detail" aria-labelledby="drawing-level-heading">
          <h3 id="drawing-level-heading" class="eyebrow">
            {{ detailLevel.id }} · {{ detailLevel.name }}
          </h3>
          <p>Отметка пола: {{ floorHeight(detailLevel.z) }}. {{ detailLevel.purpose }}</p>
          <DataTable
            :columns="placementColumns"
            :rows="placementRows"
            :caption="`Размещение машин: ${detailLevel.id} · ${detailLevel.name}`"
          />
        </section>
        <p v-else class="muted">
          Для выбранного вида этаж не указан, поэтому размещение машин не привязано.
        </p>
      </template>
    </template>

    <dialog
      ref="zoomDialog"
      class="zoom-dialog"
      aria-labelledby="drawing-zoom-heading"
      @close="onZoomClose"
    >
      <div v-if="selectedDrawing" class="stack">
        <h2 id="drawing-zoom-heading">{{ selectedDrawing.label }}</h2>
        <p class="zoom-caption">{{ captionText }}</p>
        <img
          class="zoom-image"
          :src="selectedDrawing.svg"
          :alt="imageAlt"
          decoding="async"
        >
        <div class="button-row">
          <a
            class="download-link"
            :href="selectedDrawing.svg"
            :download="downloadName(selectedDrawing.svg)"
          >
            Скачать SVG
          </a>
          <a
            v-if="selectedDrawing.png"
            class="download-link"
            :href="selectedDrawing.png"
            :download="downloadName(selectedDrawing.png)"
          >
            Скачать PNG
          </a>
          <Button type="button" variant="outline" class="min-h-11" @click="closeZoom">Закрыть</Button>
        </div>
      </div>
    </dialog>
  </section>
</template>

<style scoped>
.drawing-controls {
  align-items: end;
}

.drawing-count {
  margin-block: 0.75rem;
}

.drawing-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 15rem), 1fr));
  gap: 0.5rem;
  max-height: 16rem;
  overflow: auto;
  padding: 0.35rem;
  margin: 0 0 1.5rem;
  list-style: none;
}

.drawing-choice {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  width: 100%;
  min-height: 44px;
  padding: 0.6rem 0.75rem;
  text-align: start;
  border: 1px solid var(--control-border);
  border-radius: 0.6rem;
  background: var(--surface);
  color: var(--ink);
  cursor: pointer;
}

.drawing-choice-current {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--ink);
}

.drawing-choice-label {
  font-weight: 600;
}

.drawing-preview {
  margin: 0;
}

.drawing-image-wrap {
  overflow: auto;
  max-width: 100%;
  background: var(--surface-raised);
}

.drawing-image-wrap img {
  display: block;
  width: 100%;
  height: auto;
}

.drawing-preview figcaption {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding-top: 0.75rem;
  color: var(--ink);
}

.drawing-actions {
  margin-block: 1rem 1.5rem;
}

.download-link {
  display: inline-flex;
  width: auto;
  min-height: 44px;
  align-items: center;
  padding-inline: 0.9rem;
  border: 1px solid var(--control-border);
  border-radius: 0.35rem;
  text-decoration: none;
}

.download-link:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}

.level-detail {
  border-top: 1px solid var(--line);
  padding-top: 1rem;
}

.zoom-dialog {
  width: min(80rem, calc(100vw - 2rem));
  max-height: calc(100vh - 2rem);
  padding: 1.5rem;
  color: var(--ink);
  background: var(--surface);
  border: 1px solid var(--control-border);
  border-radius: 1rem;
}

.zoom-dialog::backdrop {
  background: rgb(0 0 0 / 65%);
}

.zoom-image {
  display: block;
  width: 100%;
  height: auto;
  max-height: 70vh;
  object-fit: contain;
  background: var(--surface-raised);
}

.zoom-caption {
  max-width: 70ch;
}
</style>
