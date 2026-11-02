<script setup lang="ts">
import type { ProjectDocument } from '~~/shared/types/project'
defineProps<{ project: ProjectDocument }>()
const world = useWorld()
</script>

<template>
  <details v-if="!project.readiness.constructionReady" class="readiness-strip">
    <summary><span><strong>Стройку пока не начинай</strong><span class="readiness-hint">Сначала проверь ограничения проекта.</span></span><span class="readiness-count">Что проверить<span v-if="project.readiness.blockers.length"> · {{ project.readiness.blockers.length }}</span></span></summary>
    <div class="readiness-details"><ul><li v-for="blocker in project.readiness.blockers" :key="blocker">{{ constructionText(blocker) }}</li></ul><p v-if="!project.readiness.blockers.length">Готовность к строительству пока не подтверждена.</p><NuxtLink class="text-link" :to="projectUrl(world.manifest, project.id, 'site')">Открыть площадку</NuxtLink><NuxtLink class="text-link" :to="projectUrl(world.manifest, project.id, 'evidence')">Проверки и ограничения</NuxtLink></div>
  </details>
</template>

<style scoped>
.readiness-details > .text-link { margin-inline-end: 1.25rem; min-height: 44px; }
</style>
