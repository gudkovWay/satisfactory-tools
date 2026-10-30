<script setup lang="ts">
import type { ProjectDocument } from '~~/shared/types/project'
const props = defineProps<{ project: ProjectDocument }>()
const query = ref('')
const parts = computed(() => props.project.parts.items.filter(part => [part.code, part.name, part.mod, part.role].join(' ').toLocaleLowerCase('ru').includes(query.value.trim().toLocaleLowerCase('ru'))))
</script>
<template>
  <div class="stack">
    <section>
      <div class="section-heading"><h2>Детали для завода</h2><span class="fine" aria-live="polite">{{ parts.length }} из {{ project.parts.items.length }}</span></div>
      <p class="muted">Названия для поиска в меню строительства. Количества проектные: метраж трасс и запас уточни после примерки.</p>
      <label class="field parts-search" for="parts-search"><span>Найти деталь или мод</span><Input id="parts-search" :model-value="query" variant="filled" type="search" placeholder="Фундамент, лестница, стекло" @update:model-value="query = String($event)" /></label>
      <p v-if="!parts.length" class="empty-state">Таких деталей нет. Попробуй другое название или мод.</p>
      <div class="part-list"><article v-for="part in parts" :key="part.code"><div class="part-identity"><h3>{{ constructionText(part.name) }}</h3><p>{{ constructionText(part.role) }}</p><details><summary>Где найти · {{ part.code }}</summary><p class="fine">{{ constructionText(part.availability) }}</p><p class="recipe-path fine">{{ part.recipeKey }}<br>{{ part.recipePath }}</p></details></div><div class="part-quantity"><span class="fine">По плану</span><strong>{{ constructionText(String(part.quantity)) }}</strong><span class="fine">{{ part.mod }}</span></div></article></div>
    </section>
    <details v-if="project.parts.facade" class="reference-disclosure"><summary>Схема фасада</summary><figure class="drawing-frame"><img :src="project.parts.facade.src" :alt="project.parts.facade.alt" width="1280" height="820" loading="lazy"><figcaption>{{ project.parts.facade.caption }}</figcaption></figure></details>
    <section v-if="project.parts.notes.length"><h2>Сборка, внешний вид и допуски</h2><ContentNotes :notes="project.parts.notes" /></section>
  </div>
</template>
