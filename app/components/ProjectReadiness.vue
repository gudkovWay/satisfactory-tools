<script setup lang="ts">
import type { ProjectDocument } from '~~/shared/types/project'
defineProps<{ project: ProjectDocument }>()
const world = useWorld()
</script>

<template>
  <details v-if="!project.readiness.constructionReady" class="readiness-strip">
    <summary><span><strong>Площадка не утверждена</strong><span class="readiness-hint">Стройку пока не начинай.</span></span><span class="readiness-count">Подробнее<span v-if="project.readiness.blockers.length"> · {{ project.readiness.blockers.length }}</span></span></summary>
    <div class="readiness-details"><ul><li v-for="blocker in project.readiness.blockers" :key="blocker">{{ constructionText(blocker) }}</li></ul><p v-if="!project.readiness.blockers.length">Готовность к строительству пока не подтверждена.</p><NuxtLink class="text-link" :to="projectUrl(world.manifest, project.id, 'evidence')">Подробности проверки</NuxtLink></div>
  </details>
</template>
