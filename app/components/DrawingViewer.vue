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
const familyOptions = computed(() => [{ value: 'all', label: 'Все виды' }, ...availableFamilies.value.map(family => ({ value: family, label: familyLabels[family] }))])

const levelMap = computed(() => new Map(props.project.levels.map(level => [level.id, level])))
const processNames = computed(() => new Map(
  (props.project.production?.processes ?? []).map(process => [
    process.id,
    `${atlasLabel(process.recipeName)} (${atlasLabel(process.machineName)})`,
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
const levelSelectOptions = computed(() => [{ value: 'all', label: 'Все этажи' }, ...levelOptions.value.map(level => ({ value: level.id, label: `${level.id} · ${atlasLabel(level.name)}` }))])

const visibleDrawings = computed(() => props.project.drawings.filter(drawing => {
  const familyMatches = familyFilter.value === 'all' || drawing.family === familyFilter.value
  const levelMatches = levelFilter.value === 'all' || drawing.levelId === levelFilter.value
  return familyMatches && levelMatches
}))

const drawingOptions = computed(() => visibleDrawings.value.map(drawing => ({
  value: drawing.id,
  label: atlasLabel(drawing.label),
})))

const selectedDrawing = computed<Drawing | null>(() => {
  const visible = visibleDrawings.value
  return visible.find(drawing => drawing.id === selectedId.value) ?? visible[0] ?? null
})

const isCampusDrawing = computed(() => /(?:^|-)campus-(freight|power)/.test(selectedDrawing.value?.id ?? ''))
const campusLine = ref('')
const imageStatus = ref<'loading' | 'ready' | 'error'>(isCampusDrawing.value ? 'ready' : 'loading')
const previewImage = ref<HTMLImageElement | null>(null)
watch(() => selectedDrawing.value?.svg, () => { imageStatus.value = isCampusDrawing.value ? 'ready' : 'loading' })
watch(previewImage, image => {
  if (image?.complete) imageStatus.value = image.naturalWidth ? 'ready' : 'error'
}, { flush: 'post' })

watch([familyFilter, levelFilter], () => {
  const visible = visibleDrawings.value
  if (visible.length && !visible.some(drawing => drawing.id === selectedId.value)) {
    selectDrawing(visible[0]!.id)
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
  void navigateTo({ path: route.path, query: { ...route.query, drawing: drawing.id }, hash: route.hash }, { replace: true })
}

const conceptAsset = computed(() => props.project.overview.concept ?? null)
const isConcept = computed(() =>
  Boolean(conceptAsset.value && selectedDrawing.value && conceptAsset.value.src === selectedDrawing.value.svg)
)

const disclosure = computed(() => blockGrid.value
  ? 'X/Y: фундаменты CC Block 8×8×2. H: слои толщины блока. Дробные центры не округлять.'
  : 'Размеры в метрах.')
const conceptDisclosure = computed(() => {
  if (!isConcept.value || !conceptAsset.value) return ''
  return `Концептуальная иллюстрация. ${conceptAsset.value.caption}`
})


const detailLevel = computed<Level | null>(() => {
  const levelId = selectedDrawing.value?.levelId
    ?? (levelFilter.value !== 'all' ? levelFilter.value : null)
  if (!levelId) return null
  return levelMap.value.get(levelId) ?? null
})

const levelPlacements = computed(() => {
  if (!detailLevel.value) return []
  const stateId = selectedDrawing.value?.operatingState ?? 'steady'
  const state = props.project.layout?.stateGeometry?.[stateId]
  const placements = state?.placements ?? (state?.placementIds
    ? props.project.placements.filter(placement => state.placementIds?.includes(placement.id))
    : stateId === 'steady' ? props.project.placements : [])
  return placements.filter(placement => placement.levelId === detailLevel.value?.id)
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
  'Частота', 'Контур',
])
const placementRows = computed(() => levelPlacements.value.map(placement => [
  placement.id,
  placement.processId ? processLabel(placement.processId) : placement.componentId ?? 'Инфраструктура',
  placement.kind,
  horizontal(placement.x),
  horizontal(placement.y),
  vertical(placement.z),
  `${horizontal(placement.width)} × ${horizontal(placement.depth)} × ${vertical(placement.height)}`,
  placement.processId ? percent(placement.clock) : '—',
  placement.existing ? 'Сохраняется' : placement.baseline === false || placement.optionalGroup ? 'Опциональный' : 'Основной',
]))

const zoomDialog = ref<HTMLDialogElement | null>(null)
const zoomOpen = ref(false)
const zoomImageStatus = ref<'loading' | 'ready' | 'error'>('loading')
let zoomTrigger: HTMLElement | null = null

function openZoom(event?: Event) {
  const target = event?.currentTarget
  zoomTrigger = target instanceof HTMLElement ? target : null
  const dialog = zoomDialog.value
  if (dialog && !dialog.open) {
    zoomImageStatus.value = isCampusDrawing.value ? 'ready' : 'loading'
    zoomOpen.value = true
    dialog.showModal()
  }
}

function closeZoom() {
  zoomDialog.value?.close()
}

function onZoomClose() {
  zoomOpen.value = false
  if (zoomTrigger?.isConnected) zoomTrigger.focus({ preventScroll: true })
  zoomTrigger = null
}

function downloadName(url: string) {
  const withoutQuery = url.split('?')[0] ?? ''
  const withoutHash = withoutQuery.split('#')[0] ?? ''
  const slash = withoutHash.lastIndexOf('/')
  const name = slash >= 0 ? withoutHash.slice(slash + 1) : withoutHash
  return name || 'drawing'
}

function downloadFormat(url: string) {
  const extension = downloadName(url).split('.').pop()?.toUpperCase()
  return ['SVG', 'PNG', 'WEBP', 'JPEG', 'JPG'].includes(extension ?? '') ? extension : 'файл'
}
</script>

<template>
  <section class="panel drawing-viewer" aria-labelledby="drawing-viewer-heading">
    <header class="drawing-intro">
      <h2 id="drawing-viewer-heading" class="sr-only">Размерные чертежи</h2>
      <p class="muted">Выбери чертёж. Открой его крупно для монтажа или скачай нужный лист.</p>
    </header>

    <div v-if="!project.drawings.length" class="empty-state">
      В опубликованном проекте нет чертежей.
    </div>

    <template v-else>
      <div class="drawing-workspace" :class="{ 'drawing-workspace-single': project.drawings.length === 1 }">
        <div class="drawing-browser">
          <div class="drawing-controls">
            <div class="field">
              <label for="drawing-family">Вид</label>
              <TheSelect trigger-id="drawing-family" :model-value="familyFilter" :options="familyOptions" @update:model-value="familyFilter = String($event)" />
            </div>
            <div class="field">
              <label for="drawing-level">Этаж</label>
              <TheSelect trigger-id="drawing-level" :model-value="levelFilter" :options="levelSelectOptions" @update:model-value="levelFilter = String($event)" />
            </div>
          </div>

          <p id="drawing-count" class="muted drawing-count" role="status">
            Показано {{ visibleDrawings.length }} из {{ project.drawings.length }} чертежей.
          </p>

          <div v-if="project.drawings.length > 1 && visibleDrawings.length" class="field drawing-sheet-select">
            <label for="drawing-sheet">Чертёж</label>
            <TheSelect
              trigger-id="drawing-sheet"
              :model-value="selectedDrawing?.id"
              :options="drawingOptions"
              described-by="drawing-count"
              @update:model-value="selectDrawing(String($event))"
            />
          </div>

          <ul v-if="project.drawings.length > 1 && visibleDrawings.length" class="drawing-list" tabindex="0" aria-label="Чертежи, прокрутка внутри списка" aria-describedby="drawing-count">
            <li v-for="drawing in visibleDrawings" :key="drawing.id">
              <button
                type="button"
                class="drawing-choice"
                :class="{ 'drawing-choice-current': selectedDrawing?.id === drawing.id }"
                :data-drawing-id="drawing.id"
                :aria-pressed="selectedDrawing?.id === drawing.id"
                aria-controls="drawing-sheet-preview"
                @click="selectDrawing(drawing.id)"
              >
                {{ atlasLabel(drawing.label) }}
              </button>
            </li>
          </ul>
        </div>

        <p v-if="!visibleDrawings.length" class="empty-state drawing-empty">
          Для этих фильтров чертежей нет. Выбери другой этаж или «Все виды».
        </p>

        <figure v-if="selectedDrawing" id="drawing-sheet-preview" class="drawing-frame drawing-preview" aria-labelledby="drawing-sheet-heading">
          <header class="drawing-sheet-header">
            <h3 id="drawing-sheet-heading">{{ atlasLabel(selectedDrawing.label) }}</h3>
            <div class="button-row drawing-actions">
              <Button type="button" class="min-h-11" :disabled="imageStatus === 'error'" @click="openZoom">Увеличить</Button>
              <a
                class="download-link"
                :href="selectedDrawing.svg"
                :download="downloadName(selectedDrawing.svg)"
              >
                Скачать {{ downloadFormat(selectedDrawing.svg) }}
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
          </header>
          <div class="drawing-image-wrap" :aria-busy="imageStatus === 'loading'">
            <p v-if="imageStatus === 'loading'" class="drawing-image-status muted" role="status">
              Загружаем выбранный чертёж.
            </p>
            <p v-if="imageStatus === 'error'" class="empty-state drawing-image-error" role="alert">
              Не удалось загрузить чертёж. Скачайте исходный файл или выберите другой лист.
            </p>
            <CampusDrawing v-if="isCampusDrawing" v-model="campusLine" :project="project" :drawing="selectedDrawing" />
            <MetricDrawing v-else-if="selectedDrawing.svg.endsWith('.svg') && imageStatus !== 'error'" :key="selectedDrawing.svg" :src="selectedDrawing.svg" :alt="atlasLabel(selectedDrawing.label)" @load="imageStatus = 'ready'" @error="imageStatus = 'error'" />
            <img
              v-else-if="imageStatus !== 'error'"
              :key="selectedDrawing.svg"
              ref="previewImage"
              :src="selectedDrawing.svg"
              :alt="atlasLabel(selectedDrawing.label)"
              decoding="async"
              @load="imageStatus = 'ready'"
              @error="imageStatus = 'error'"
            >
          </div>
          <figcaption>{{ disclosure }}</figcaption>
        </figure>
      </div>

      <template v-if="selectedDrawing">
        <details :key="selectedDrawing.id" class="reference-disclosure drawing-source-details"><summary>Данные и ограничения чертежа</summary><p>{{ constructionText(selectedDrawing.caption) }}</p><p v-if="conceptDisclosure">{{ constructionText(conceptDisclosure) }}</p><dl><div><dt>Лист</dt><dd><code>{{ selectedDrawing.id }}</code></dd></div><div v-if="selectedDrawing.operatingState"><dt>Режим</dt><dd>{{ atlasLabel(selectedDrawing.operatingState) }}</dd></div></dl></details>
        <section v-if="detailLevel" class="stack level-detail" aria-labelledby="drawing-level-heading">
          <h3 id="drawing-level-heading">
            {{ detailLevel.id }} · {{ atlasLabel(detailLevel.name) }}
          </h3>
          <p>Пол: {{ floorHeight(detailLevel.z) }}. {{ constructionText(detailLevel.purpose) }}</p>
          <DataTable
            :columns="placementColumns"
            :rows="placementRows"
            :caption="`Размещение машин: ${detailLevel.id} · ${detailLevel.name}`"
          />
        </section>
      </template>
    </template>

    <dialog
      ref="zoomDialog"
      class="zoom-dialog"
      aria-labelledby="drawing-zoom-heading"
      @close="onZoomClose"
    >
      <div v-if="selectedDrawing && zoomOpen" class="stack">
        <h2 id="drawing-zoom-heading">{{ atlasLabel(selectedDrawing.label) }}</h2>
        <p class="zoom-caption">{{ disclosure }}</p>
        <p class="fine">Чертёж в полном масштабе. Прокручивай внутри области; с клавиатуры используй стрелки.</p>
        <p v-if="zoomImageStatus === 'loading'" role="status">Загружаем выбранный чертёж.</p>
        <p v-if="zoomImageStatus === 'error'" class="empty-state" role="alert">
          Не удалось загрузить чертёж. Скачайте исходный файл или выберите другой лист.
        </p>
        <div v-else class="zoom-pan" tabindex="0" aria-label="Чертёж крупно, прокрутка по двум осям">
          <CampusDrawing v-if="isCampusDrawing" v-model="campusLine" class="zoom-campus" :project="project" :drawing="selectedDrawing" />
          <MetricDrawing v-else-if="selectedDrawing.svg.endsWith('.svg')" :key="selectedDrawing.svg" class="zoom-image" :src="selectedDrawing.svg" :alt="atlasLabel(selectedDrawing.label)" @load="zoomImageStatus = 'ready'" @error="zoomImageStatus = 'error'" />
          <img v-else
            :key="selectedDrawing.svg"
            class="zoom-image"
            :src="selectedDrawing.svg"
            :alt="atlasLabel(selectedDrawing.label)"
            decoding="async"
            @load="zoomImageStatus = 'ready'"
            @error="zoomImageStatus = 'error'"
          >
        </div>
        <div class="button-row">
          <a
            class="download-link"
            :href="selectedDrawing.svg"
            :download="downloadName(selectedDrawing.svg)"
          >
            Скачать {{ downloadFormat(selectedDrawing.svg) }}
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
.drawing-intro p {
  margin-bottom: 1rem;
  font-size: .875rem;
}

.drawing-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1rem;
  align-items: start;
}

.drawing-browser,
.drawing-preview,
.drawing-empty,
.level-detail {
  min-width: 0;
}

.drawing-browser {
  display: grid;
  gap: .75rem;
}

.drawing-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .75rem;
  align-items: end;
}

.drawing-count {
  margin: 0;
  font-size: .8125rem;
}

.drawing-list {
  display: none;
  gap: .25rem;
  max-height: min(30rem, 55dvh);
  overflow-y: auto;
  overscroll-behavior-y: contain;
  scrollbar-gutter: stable;
  padding: .25rem;
  margin: 0;
  list-style: none;
}

.drawing-list li {
  min-width: 0;
  margin: 0;
}

.drawing-choice {
  display: block;
  width: 100%;
  min-height: 44px;
  padding: .65rem .75rem;
  text-align: start;
  overflow-wrap: anywhere;
  font-size: .8125rem;
  line-height: 1.45;
  border: 1px solid transparent;
  border-radius: .35rem;
  background: transparent;
  color: var(--ink);
  cursor: pointer;
}

.drawing-choice:hover {
  border-color: var(--control-border);
  background: var(--surface);
}

.drawing-choice-current,
.drawing-choice-current:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
  font-weight: 600;
}

.drawing-list:focus-visible,
.drawing-choice:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}

.drawing-preview {
  margin: 0;
}

.drawing-sheet-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: .75rem 1rem;
  padding: .75rem;
}

.drawing-sheet-header h3 {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
  font-size: 1.125rem;
  font-weight: 600;
  line-height: 1.4;
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

.drawing-image-error {
  margin: 0;
}

.drawing-image-status {
  margin: 0;
  padding: .75rem;
  font-size: .875rem;
}

.drawing-preview figcaption {
  padding: .75rem;
  overflow-wrap: anywhere;
  font-size: .875rem;
  color: var(--ink);
}

.drawing-actions {
  gap: .5rem;
  margin: 0;
}

@media (min-width: 650px) {
  .drawing-browser {
    grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
    align-items: end;
  }

  .drawing-controls {
    grid-column: 1;
    grid-row: 1;
  }

  .drawing-sheet-select {
    grid-column: 2;
    grid-row: 1;
  }

  .drawing-count {
    grid-column: 1 / -1;
    grid-row: 2;
  }

  .drawing-workspace-single .drawing-browser {
    grid-template-columns: minmax(0, 1fr);
  }

  .drawing-sheet-header,
  .drawing-preview figcaption {
    padding: 1rem;
  }
}

@media (min-width: 1280px) {
  .drawing-workspace {
    grid-template-columns: 13rem minmax(0, 1fr);
  }

  .drawing-browser {
    display: block;
  }

  .drawing-controls {
    grid-template-columns: minmax(0, 1fr);
  }

  .drawing-count {
    margin-block: .75rem;
  }

  .drawing-sheet-select {
    display: none;
  }

  .drawing-list {
    display: grid;
  }

  .drawing-workspace-single {
    grid-template-columns: minmax(0, 1fr);
  }

  .drawing-workspace-single .drawing-controls {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    max-width: 40rem;
  }
}

@media print {
  .drawing-workspace {
    display: block;
  }

  .drawing-browser,
  .drawing-actions {
    display: none;
  }
}

.download-link {
  display: inline-flex;
  width: auto;
  min-height: 44px;
  min-width: 44px;
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
  margin-top: 1.5rem;
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

.zoom-pan {
  overflow: auto;
  max-height: 65dvh;
  border: 1px solid var(--control-border);
  background: var(--surface-raised);
}

.zoom-pan:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}

.zoom-image {
  display: block;
  width: max(100%, 80rem);
  max-width: none;
  height: auto;
}

.zoom-campus { width: max(100%, 80rem); max-width: none; }
.drawing-source-details { margin-top: 1.5rem; }
.drawing-source-details dd { overflow-wrap: anywhere; }
.zoom-caption {
  max-width: 70ch;
}
</style>
