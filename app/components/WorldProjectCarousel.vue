<script setup lang="ts">
import type { WorldManifest } from '~~/shared/types/world'

const props = defineProps<{ manifest?: WorldManifest | null; loading?: boolean; error?: boolean }>()
const emit = defineEmits<{ retry: [] }>()
const index = ref(0)
const imageState = ref<'loading' | 'ready' | 'error'>('loading')
const image = ref<HTMLImageElement | null>(null)
const projects = computed(() => props.manifest?.projects.filter(project => Boolean(project.preview?.src)) ?? [])
const selected = computed(() => projects.value[index.value])
const title = computed(() => atlasLabel(selected.value?.title.replace(/^Прежняя редакция\s*·\s*/, '') ?? ''))

watch(projects, () => { index.value = 0 })
watch(() => selected.value?.preview?.src, () => { imageState.value = 'loading' }, { flush: 'sync' })
watch(image, element => {
  if (element?.complete) imageState.value = element.naturalWidth ? 'ready' : 'error'
}, { flush: 'post' })

function move(offset: number) {
  if (projects.value.length < 2) return
  index.value = (index.value + offset + projects.value.length) % projects.value.length
}
function onKeydown(event: KeyboardEvent) {
  if (projects.value.length < 2 || event.altKey || event.ctrlKey || event.metaKey) return
  if ((event.target as HTMLElement).closest('details')) return
  if (event.key === 'ArrowLeft') move(-1)
  else if (event.key === 'ArrowRight') move(1)
  else if (event.key === 'Home') index.value = 0
  else if (event.key === 'End') index.value = projects.value.length - 1
  else return
  event.preventDefault()
}
</script>

<template>
  <section class="project-carousel" role="region" aria-roledescription="карусель" :aria-label="manifest ? `Проекты мира ${manifest.title}` : 'Превью проектов'" :aria-busy="loading || undefined" @keydown="onKeydown">
    <div v-if="loading" class="carousel-state" role="status">Загружаем проекты мира.</div>
    <div v-else-if="error" class="carousel-state" role="alert">
      <p>Не удалось загрузить превью проектов.</p>
      <button type="button" class="carousel-retry" @click="emit('retry')">Повторить загрузку</button>
    </div>
    <template v-else-if="selected && manifest">
      <NuxtLink class="carousel-project" :to="projectUrl(manifest, selected.id)" :aria-label="`Открыть проект: ${title}`">
        <div class="carousel-media" :aria-busy="imageState === 'loading' || undefined">
          <img v-if="imageState !== 'error'" :key="selected.preview!.src" ref="image" :src="selected.preview!.src" :alt="selected.preview!.alt" width="960" height="540" @load="imageState = 'ready'" @error="imageState = 'error'">
          <span v-if="imageState === 'loading'" class="carousel-image-status" role="status">Загружаем изображение.</span>
          <span v-else-if="imageState === 'error'" class="carousel-image-status" role="status">Изображение недоступно. Проект можно открыть.</span>
        </div>
        <div class="carousel-caption" aria-live="polite" aria-atomic="true">
          <span>Тир {{ selected.tier }} · {{ selected.category === 'factories' ? 'Завод' : 'Инфраструктура' }}</span>
          <strong>{{ title }}</strong>
          <span v-if="selected.integrationStatus === 'preserved-previous'">Архивный план</span>
          <span class="carousel-destination">Открыть проект</span>
        </div>
      </NuxtLink>
      <div class="carousel-controls" aria-label="Выбор проекта">
        <span class="carousel-position">{{ index + 1 }} из {{ projects.length }}</span>
        <div v-if="projects.length > 1" class="carousel-buttons">
          <button type="button" aria-label="Предыдущий проект" @click="move(-1)"><span aria-hidden="true">←</span></button>
          <button type="button" aria-label="Следующий проект" @click="move(1)"><span aria-hidden="true">→</span></button>
        </div>
      </div>
      <details v-if="selected.preview!.caption" :key="selected.id" class="carousel-data">
        <summary>Данные изображения</summary>
        <p>{{ selected.preview!.caption }}</p>
      </details>
    </template>
    <div v-else class="carousel-state"><p>У проектов пока нет превью.</p><p>Открой мир, чтобы выбрать проект по названию.</p></div>
  </section>
</template>

<style scoped>
.project-carousel { min-width: 0; background: var(--surface); border-radius: 8px; }
.carousel-project { display: block; color: var(--ink); text-decoration: none; border-radius: 8px; }
.carousel-media { position: relative; aspect-ratio: 16 / 9; max-height: 390px; background: var(--surface-raised); border-radius: 8px 8px 0 0; overflow: clip; }
.carousel-media img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.carousel-image-status { position: absolute; inset: auto .75rem .75rem; padding: .5rem .75rem; color: var(--ink); background: var(--surface); font-size: .875rem; }
.carousel-caption { display: grid; gap: .4rem; padding: 1rem 1.25rem .5rem; }
.carousel-caption>span { color: var(--muted); font-size: .875rem; line-height: 1.5; }
.carousel-caption strong { font-size: clamp(1.125rem, 2vw, 1.5rem); font-weight: 550; line-height: 1.35; overflow-wrap: anywhere; }
.carousel-caption .carousel-destination { color: var(--ink); text-decoration: underline; text-underline-offset: .2em; }
.carousel-project:hover .carousel-destination { color: var(--accent); }
.carousel-controls { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: .5rem 1.25rem 1rem; }
.carousel-position { color: var(--muted); font-size: .875rem; font-variant-numeric: tabular-nums; }
.carousel-buttons { display: flex; gap: .5rem; }
.carousel-buttons button,.carousel-retry { display: inline-grid; place-items: center; min-width: 44px; min-height: 44px; border: 1px solid var(--control-border); border-radius: 6px; background: var(--surface); color: var(--ink); }
.carousel-buttons button { font-size: 1.25rem; }
.carousel-buttons button:hover,.carousel-retry:hover { background: var(--surface-raised); }
.carousel-state { display: flex; flex-direction: column; justify-content: center; align-items: start; min-height: 16rem; padding: 1.25rem; color: var(--muted); }
.carousel-state p { margin-bottom: .5rem; }
.carousel-retry { padding: .5rem .75rem; }
.carousel-data { padding: 0 1.25rem .5rem; font-size: .8125rem; color: var(--muted); }
.carousel-data summary { min-height: 44px; }
.carousel-data p { margin: 0 0 .5rem; }
.project-carousel :is(a,button,summary):focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
@media (min-width: 700px) { .carousel-caption { padding-top: 1.25rem; } }
</style>
