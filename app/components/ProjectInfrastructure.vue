<script setup lang="ts">
import type { ProjectDocument } from '~~/shared/types/project'
const props = defineProps<{ project: ProjectDocument }>()
const search = ref('')
const processes = computed(() => new Map((props.project.production?.processes ?? []).map(process => [process.id, process])))
function endpointLabel(id: string) {
  if (id === 'RAW') return 'Подача сырья'
  if (id === 'STOCK') return 'Склад'
  const process = processes.value.get(id)
  return process ? atlasLabel(process.recipeName) : atlasLabel(id)
}
const streams = computed(() => {
  const query = search.value.trim().toLocaleLowerCase('ru')
  return props.project.infrastructure.streams.filter(stream => [
    stream.id, stream.itemId, stream.label, atlasLabel(stream.label),
    ...stream.from, ...stream.from.map(endpointLabel), stream.to, endpointLabel(stream.to),
  ].join(' ').toLocaleLowerCase('ru').includes(query))
})
const rows = computed(() => streams.value.map(stream => [
  atlasLabel(stream.label), stream.from.map(endpointLabel).join(', '), endpointLabel(stream.to),
  `${formatRate(stream.rate, 6)} ${stream.fluid ? 'м³' : 'шт'}/мин`,
  `${stream.lanes} × ${formatRate(stream.capacity)} ${stream.fluid ? 'м³' : 'шт'}/мин`,
]))
const technicalRows = computed(() => streams.value.map(stream => [
  stream.id, stream.itemId, stream.from.join(', '), stream.to,
]))
</script>
<template>
  <div class="stack">
    <section v-if="project.infrastructure.streams.length">
      <div class="section-heading"><h2>Соединения</h2><span class="fine" aria-live="polite">{{ rows.length }} из {{ project.infrastructure.streams.length }} линий</span></div><p class="muted">Подключи источники к потребителям с указанной пропускной способностью.</p>
      <label class="field stream-search" for="stream-search"><span>Найти продукт или соединение</span><Input id="stream-search" :model-value="search" variant="filled" type="search" placeholder="Название продукта или группа" @update:model-value="search = String($event)" /></label>
      <DataTable :columns="['Продукт', 'Откуда', 'Куда', 'Поток', 'Число линий × предел каждой']" :rows="rows" caption="Подача между производственными группами" />
      <details class="reference-disclosure"><summary>Обозначения линий в исходном плане</summary><DataTable :columns="['Линия', 'Код продукта', 'Источники', 'Потребитель']" :rows="technicalRows" caption="Идентификаторы найденных соединений" /></details>
    </section>
    <section v-if="project.infrastructure.notes.length"><h2>Правила монтажа и запуска</h2><ContentNotes :notes="project.infrastructure.notes" /></section>
    <details v-for="table in project.infrastructure.tables" :key="table.caption" class="reference-disclosure"><summary>{{ constructionText(table.caption) }}</summary><DataTable :columns="table.columns" :rows="table.rows" :caption="table.caption" /></details>
    <details v-for="diagram in project.infrastructure.diagrams" :key="diagram.src" class="reference-disclosure"><summary>{{ atlasLabel(diagram.alt) }}</summary><figure class="drawing-frame"><img :src="diagram.src" :alt="diagram.alt" loading="lazy" width="1280" height="820"><figcaption>{{ constructionText(diagram.caption) }}</figcaption></figure></details>
    <p v-if="!project.infrastructure.streams.length && !project.infrastructure.notes.length && !project.infrastructure.tables.length && !project.infrastructure.diagrams.length" class="empty-state">Для этого проекта соединения ещё не описаны.</p>
  </div>
</template>

<style scoped>
.stream-search { max-width: 32rem; margin-block: 1rem; }
</style>
