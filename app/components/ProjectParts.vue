<script setup lang="ts">
import type { ProjectDocument } from '~~/shared/types/project'
const props = defineProps<{ project: ProjectDocument }>()
const query = ref('')
const parts = computed(() => props.project.parts.items.filter(part => [part.code, part.name, atlasLabel(part.name), part.mod, part.role].join(' ').toLocaleLowerCase('ru').includes(query.value.trim().toLocaleLowerCase('ru'))))
function tableTitle(caption: string) {
  if (caption.startsWith('Опциональный прирост')) return 'Дополнительные материалы'
  if (caption.startsWith('Распределение сметы')) return 'Материалы по этапам'
  if (caption.startsWith('Единый резерв закупки трасс')) return 'Общий резерв лент и проводки'
  return constructionText(caption)
}
</script>
<template>
  <div class="stack">
    <section v-if="project.parts.tables?.length" class="stack">
      <h2>Закупка материалов</h2>
      <p class="muted">Основной заказ показан ниже. Распределение по этапам не нужно покупать повторно; материалы для трасс учитываются отдельно.</p>
      <template v-for="(table, index) in project.parts.tables" :key="table.caption">
        <DataTable v-if="index === 0" :columns="table.columns" :rows="table.rows" :caption="table.caption.startsWith('Полная фиксированная базовая смета') ? 'Основные материалы: без резерва трасс' : table.caption" />
        <details v-else class="reference-disclosure"><summary>{{ tableTitle(table.caption) }}</summary><DataTable :columns="table.columns" :rows="table.rows" :caption="table.caption" /></details>
      </template>
    </section>
    <section>
      <div class="section-heading"><h2>Детали для завода</h2><span class="fine" aria-live="polite">{{ parts.length }} из {{ project.parts.items.length }}</span></div>
      <p class="muted">Найди деталь в меню строительства. Для лент и труб сверь длину на площадке.</p>
      <label class="field parts-search" for="parts-search"><span>Найти деталь или мод</span><Input id="parts-search" :model-value="query" variant="filled" type="search" placeholder="Фундамент, лестница, стекло" @update:model-value="query = String($event)" /></label>
      <p v-if="!parts.length" class="empty-state">Таких деталей нет. Попробуй другое название или мод.</p>
      <div class="part-list"><article v-for="part in parts" :key="part.code"><div class="part-identity"><h3>{{ atlasLabel(constructionText(part.name)) }}</h3><p>{{ constructionText(part.role) }}</p><details><summary>Где найти</summary><p class="fine">{{ constructionText(part.availability) }}</p><p class="recipe-path fine">{{ part.code }}<br>{{ part.recipeKey }}<br>{{ part.recipePath }}</p></details></div><div class="part-quantity"><span class="fine">По плану</span><strong>{{ constructionText(String(part.quantity)) }}</strong><span class="fine">{{ part.mod }}</span></div></article></div>
    </section>
    <details v-if="project.parts.facade" class="reference-disclosure"><summary>Схема фасада</summary><figure class="drawing-frame"><img :src="project.parts.facade.src" :alt="project.parts.facade.alt" width="1280" height="820" loading="lazy"><figcaption>{{ project.parts.facade.caption }}</figcaption></figure></details>
    <section v-if="project.parts.notes.length"><h2>Сборка, внешний вид и допуски</h2><ContentNotes :notes="project.parts.notes" /></section>
  </div>
</template>
