<script setup lang="ts">
const world = useWorld()
const route = useRoute()
const manifest = computed(() => world.value.manifest)
const base = computed(() => worldUrl(manifest.value.id))
const links = computed(() => [
  { label: 'Обзор мира', to: base.value, active: route.path.replace(/\/$/, '') === base.value && !route.hash },
  { label: 'Проекты', to: `${base.value}#projects`, active: route.hash === '#projects' },
  { label: 'По порядку', to: `${base.value}#route`, active: route.hash === '#route' || Boolean(route.params.tier) },
  ...(manifest.value.map ? [{ label: 'Карта', to: `${base.value}#map`, active: route.hash === '#map' }] : []),
  { label: 'Анализы', to: `${base.value}/analysis/${manifest.value.sourceAnalysisId}`, active: Boolean(route.params.analysis) }
])
</script>
<template>
  <div class="world-context-bar page-width" :class="{ 'context-working': Boolean(route.params.project) }">
    <NuxtLink class="context-world" :to="base">{{ manifest.title }}<span>Сейв {{ world.record.saveId }}</span></NuxtLink>
    <nav class="context-links" aria-label="Навигация по миру"><NuxtLink v-for="link in links" :key="link.label" :to="link.to" :aria-current="link.active ? 'page' : undefined">{{ link.label }}</NuxtLink></nav>
    <details v-if="route.params.project" class="mobile-world-nav"><summary>Навигация мира</summary><nav aria-label="Мир на мобильном"><NuxtLink v-for="link in links" :key="link.label" :to="link.to">{{ link.label }}</NuxtLink></nav></details>
  </div>
</template>
