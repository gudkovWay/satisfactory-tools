<script setup lang="ts">
import { Search, X, CornerDownLeft } from '@lucide/vue'
import { useEventListener } from '@vueuse/core'
import type { ProjectDocument } from '~~/shared/types/project'
const props = defineProps<{ project: ProjectDocument }>()
const world = useWorld()
const dialog = useTemplateRef<HTMLDialogElement>('dialog')
const input = useTemplateRef<HTMLInputElement>('input')
const query = ref('')
const selected = ref(0)
let trigger: HTMLElement | null = null
const entries = computed(() => {
  const base = projectUrl(world.value.manifest, props.project.id)
  return [
    ...projectSections.map(section => ({ id: section.id, title: section.label, group: 'Разделы', to: projectUrl(world.value.manifest, props.project.id, section.id) })),
    ...props.project.build.steps.map((step, i) => ({ id: step.id, title: `${i + 1}. ${guideStageLabel(step)}`, group: 'Этапы стройки', to: `${base}/build?stage=${encodeURIComponent(step.id)}` })),
    ...props.project.drawings.map(drawing => ({ id: drawing.id, title: drawing.label, group: 'Чертежи', to: `${base}/drawings?drawing=${encodeURIComponent(drawing.id)}` }))
  ]
})
const results = computed(() => {
  const words = query.value.toLocaleLowerCase('ru').trim().split(/\s+/).filter(Boolean)
  return entries.value.filter(entry => words.every(word => `${entry.title} ${entry.id} ${entry.group}`.toLocaleLowerCase('ru').includes(word)))
})
watch(query, () => { selected.value = 0 })
async function open() {
  if (dialog.value?.open) return
  trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null
  query.value = ''
  selected.value = 0
  dialog.value?.showModal()
  await nextTick()
  input.value?.focus()
}
function close() { dialog.value?.close() }
function restoreFocus() { trigger?.isConnected && trigger.focus(); trigger = null }
function move(event: KeyboardEvent) {
  if (!['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter'].includes(event.key)) return
  event.preventDefault()
  if (event.key === 'Enter') {
    const entry = results.value[selected.value]
    if (entry) { close(); void navigateTo(entry.to) }
    return
  }
  const count = results.value.length
  if (!count) return
  selected.value = event.key === 'Home' ? 0 : event.key === 'End' ? count - 1 : (selected.value + (event.key === 'ArrowDown' ? 1 : -1) + count) % count
  void nextTick(() => document.getElementById(`search-result-${selected.value}`)?.scrollIntoView({ block: 'nearest' }))
}
useEventListener(typeof window === 'undefined' ? undefined : window, 'keydown', (event: KeyboardEvent) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    if (document.querySelector('dialog[open]') && !dialog.value?.open) return
    event.preventDefault()
    if (dialog.value?.open) close(); else void open()
  }
})
</script>

<template>
  <button class="search-trigger" type="button" aria-label="Найти в проекте" @click="open"><Search :size="17" aria-hidden="true" /><span>Найти в проекте</span><kbd>Ctrl K</kbd></button>
  <dialog ref="dialog" class="atlas-dialog search-dialog" aria-labelledby="project-search-title" @close="restoreFocus" @keydown.esc.prevent="close" @click="($event.target === dialog) && close()">
    <div class="search-dialog-head"><Search :size="22" aria-hidden="true" /><h2 id="project-search-title" class="sr-only">Поиск по проекту</h2><input ref="input" v-model="query" type="search" placeholder="Этап, этаж или чертёж…" aria-label="Этап, этаж или чертёж" role="combobox" aria-autocomplete="list" aria-controls="project-search-results" :aria-expanded="true" :aria-activedescendant="results.length ? `search-result-${selected}` : undefined" @keydown="move"><button class="icon-button" type="button" aria-label="Закрыть поиск" @click="close"><X :size="20" /></button></div>
    <div id="project-search-results" class="search-results" role="listbox" aria-label="Результаты поиска">
      <template v-for="(entry, index) in results" :key="entry.group + entry.id">
        <p v-if="index === 0 || entry.group !== results[index - 1]?.group" class="search-group">{{ entry.group }}</p>
        <NuxtLink :id="`search-result-${index}`" :to="entry.to" role="option" :aria-selected="selected === index" class="search-result" @click="close" @focus="selected = index"><span>{{ entry.title }}</span><CornerDownLeft v-if="selected === index" :size="16" aria-hidden="true" /></NuxtLink>
      </template>
      <p v-if="!results.length" class="search-empty" role="status">Ничего не нашлось. Попробуй «этаж», «площадка» или номер этапа.</p>
    </div>
    <footer class="search-help"><span>Найдено: {{ results.length }}</span><span>↑ ↓ выбрать · Enter открыть · Esc закрыть</span></footer>
  </dialog>
</template>
