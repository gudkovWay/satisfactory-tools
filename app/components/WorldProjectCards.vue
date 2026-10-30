<script setup lang="ts">
const props = defineProps<{ ids: string[] }>()
const world = useWorld()
const projects = computed(() => props.ids.map(id => world.value.manifest.projects.find(project => project.id === id)).filter(item => item !== undefined))
</script>
<template><div class="world-project-list"><NuxtLink v-for="project in projects" :key="project.id" :to="projectUrl(world.manifest, project.id)" class="world-project-link"><div><p class="fine">Тир {{ project.tier }} · {{ project.stages }} этапов<span v-if="project.optional"> · необязательный вариант</span></p><h3>{{ project.title }}</h3><p v-if="project.outputs.length">{{ project.outputs.map(flow => `${flow.label} ${formatRate(flow.rate)} / мин`).join(' · ') }}</p><p v-else class="muted">{{ project.site }}</p></div><span aria-hidden="true">↗</span></NuxtLink></div></template>
