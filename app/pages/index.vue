<script setup lang="ts">
import type { WorldManifest, WorldRegistry } from '~~/shared/types/world'
definePageMeta({ alias: ['/world'] })
const { data: registry, status, error, refresh } = await useFetch<WorldRegistry>('/worlds/index.json', { key: 'atlas-world-registry' })
const { data: manifests, status: manifestStatus, refresh: refreshManifests } = await useAsyncData('atlas-catalogue-manifests', async () => {
  const entries = await Promise.all((registry.value?.worlds ?? []).map(async world => {
    const manifest = await $fetch<WorldManifest>(`${worldUrl(world.id)}/manifest.json`).catch(() => null)
    return [world.id, manifest] as const
  }))
  return Object.fromEntries(entries)
}, { watch: [registry] })
useSeoMeta({ title: 'Миры / Строительный атлас Satisfactory' })
</script>

<template>
  <main id="main" class="page-width atlas-home home-workspace">
    <header class="home-heading"><h1>Строительные проекты</h1><p>Выбери мир, найди нужный завод или начни строительство по тирам.</p></header>
    <p v-if="status === 'pending'" class="empty-state" role="status">Загружаем миры и строительные планы.</p>
    <section v-else-if="error" class="empty-state" role="alert"><h2>Миры не загрузились</h2><p>Попробуй загрузить список ещё раз.</p><Button @click="refresh()">Повторить загрузку</Button></section>
    <div v-else class="home-worlds">
      <article v-for="world in registry?.worlds" :key="world.id" class="home-world">
        <div class="home-world-context">
          <h2><NuxtLink :to="worldUrl(world.id)">{{ world.title }}</NuxtLink></h2>
          <p>Проекты заводов, порядок строительства и общая карта.</p>
          <nav class="home-world-actions" :aria-label="`Открыть мир ${world.title}`">
            <Button as-child><NuxtLink :to="worldUrl(world.id)">Открыть мир</NuxtLink></Button>
            <NuxtLink class="text-link" :to="`${worldUrl(world.id)}#projects`">Все проекты мира</NuxtLink>
          </nav>
        </div>
        <WorldProjectCarousel :manifest="manifests?.[world.id]" :loading="manifestStatus === 'pending' || manifestStatus === 'idle'" :error="manifestStatus !== 'pending' && manifestStatus !== 'idle' && !manifests?.[world.id]" @retry="refreshManifests()" />
      </article>
    </div>
    <section v-if="registry && !registry.worlds.length" class="empty-state"><h2>Миров пока нет</h2><p>В атласе ещё нет опубликованных строительных планов.</p></section>
    <p class="home-save-note">Атлас не меняет сохранения игры. Отметки о строительстве хранятся в этом браузере.</p>
  </main>
</template>

<style scoped>
.home-workspace { padding-top: clamp(1.5rem, 4vw, 3rem); }
.home-heading { margin-bottom: 1.5rem; }
.home-heading h1 { margin-bottom: .5rem; font-size: clamp(1.75rem, 3vw, 2.5rem); font-weight: 550; line-height: 1.2; letter-spacing: -.04em; }
.home-heading p { color: var(--muted); max-width: 55ch; margin-bottom: 0; }
.home-worlds { display: grid; gap: 2rem; }
.home-world { display: grid; grid-template-columns: minmax(0, 1fr); gap: 1.25rem; padding: 1rem; background: var(--surface-raised); border-radius: 12px; }
.home-world-context { min-width: 0; }
.home-world-context h2 { font-size: clamp(1.5rem, 3vw, 2.25rem); line-height: 1.2; letter-spacing: -.04em; font-weight: 550; margin-bottom: .5rem; }
.home-world-context h2 a { display: inline-flex; align-items: center; min-height: 44px; color: var(--ink); text-decoration: none; }
.home-world-context h2 a:hover { color: var(--accent); }
.home-world-context>p { color: var(--muted); max-width: 36ch; font-size: .9375rem; }
.home-world-actions { display: flex; align-items: center; flex-wrap: wrap; gap: .5rem 1rem; }
.home-save-note { max-width: 75ch; margin: 1.5rem 0 0; font-size: .875rem; color: var(--muted); }
.home-world a:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
@media (min-width: 700px) {
  .home-world { padding: 1.5rem; gap: 1.5rem; }
  .home-world-context { display: grid; grid-template-columns: minmax(0, 1fr) auto; column-gap: 1.5rem; align-items: center; }
  .home-world-context h2 { grid-column: 1; }
  .home-world-context>p { grid-column: 1; margin-bottom: 0; }
  .home-world-actions { grid-column: 2; grid-row: 1 / 3; flex-direction: column; align-items: start; }
}
@media (min-width: 1050px) {
  .home-world { grid-template-columns: minmax(0, .7fr) minmax(0, 1.3fr); gap: 2rem; }
  .home-world-context { display: flex; flex-direction: column; align-items: start; justify-content: center; }
  .home-world-context h2 { font-size: clamp(2rem, 3vw, 3rem); }
  .home-world-context>p { margin-bottom: 1.5rem; }
  .home-world-actions { align-items: start; }
}
</style>
