<script setup lang="ts">
import type { ProjectDocument } from '~~/shared/types/project'
const props = defineProps<{ project: ProjectDocument }>()
const search = ref('')
const rows = computed(() => props.project.infrastructure.streams.filter(stream => [stream.id, stream.label, stream.from.join(' '), stream.to].join(' ').toLocaleLowerCase('ru').includes(search.value.trim().toLocaleLowerCase('ru'))).map(stream => [stream.id, stream.label, stream.from.join(', '), stream.to, `${formatRate(stream.rate, 6)} ${stream.fluid ? 'м³' : 'шт'}/мин`, `${stream.lanes} × ${formatRate(stream.capacity)}/мин`]))
</script>
<template>
  <div class="stack">
    <section v-if="project.infrastructure.streams.length">
      <div class="section-heading"><h2>Что с чем соединить</h2><span class="fine" aria-live="polite">{{ rows.length }} из {{ project.infrastructure.streams.length }} линий</span></div><p class="muted">Потоки по плану: от источника к потребителю, с числом лент или труб и их пределом.</p>
      <label class="field stream-search" for="stream-search"><span>Найти соединение</span><Input id="stream-search" :model-value="search" variant="filled" type="search" placeholder="Резина, P05, RAW" @update:model-value="search = String($event)" /></label>
      <DataTable :columns="['Линия', 'Изделие', 'Откуда', 'Куда', 'Поток', 'Линии и предел']" :rows="rows" caption="Соединения между производственными группами" />
    </section>
    <section v-if="project.infrastructure.notes.length"><h2>Правила монтажа и запуска</h2><ContentNotes :notes="project.infrastructure.notes" /></section>
    <details v-for="table in project.infrastructure.tables" :key="table.caption" class="reference-disclosure"><summary>{{ constructionText(table.caption) }}</summary><DataTable :columns="table.columns" :rows="table.rows" :caption="table.caption" /></details>
    <details v-for="diagram in project.infrastructure.diagrams" :key="diagram.src" class="reference-disclosure"><summary>{{ diagram.alt }}</summary><figure class="drawing-frame"><img :src="diagram.src" :alt="diagram.alt" loading="lazy" width="1280" height="820"><figcaption>{{ diagram.caption }}</figcaption></figure></details>
    <p v-if="!project.infrastructure.streams.length && !project.infrastructure.notes.length && !project.infrastructure.tables.length" class="empty-state">В этом проекте пока нет схем коммуникаций.</p>
  </div>
</template>
