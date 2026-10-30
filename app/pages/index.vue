<script setup lang="ts">
import type { WorldManifest, WorldRegistry } from '~~/shared/types/world'
definePageMeta({ alias: ['/world'] })
const { data: registry, status, error, refresh } = await useFetch<WorldRegistry>('/worlds/index.json', { key: 'atlas-world-registry' })
const { data: manifests } = await useAsyncData('atlas-catalogue-manifests', async () => {
  const entries = await Promise.all((registry.value?.worlds ?? []).map(async world => {
    const manifest = await $fetch<WorldManifest>(`${worldUrl(world.id)}/manifest.json`).catch(() => null)
    return [world.id, manifest] as const
  }))
  return Object.fromEntries(entries)
}, { watch: [registry] })
useSeoMeta({ title: 'Миры / Строительный атлас Satisfactory' })
</script>
<template>
  <main id="main" class="page-width atlas-home">
    <header class="catalogue-title"><h1>Твой мир.<br>План строительства.</h1><p>Ресурсы, заводы и порядок сборки в одном атласе. Открой мир и выбери, что строить дальше.</p></header>
    <p v-if="status === 'pending'" class="empty-state" role="status">Загружаем миры и строительные планы.</p>
    <section v-else-if="error" class="empty-state" role="alert"><h2>Миры не загрузились</h2><p>Не удалось прочитать реестр. Попробуй загрузить его ещё раз.</p><Button @click="refresh()">Повторить загрузку</Button></section>
    <div v-else class="world-catalogue">
      <article v-for="world in registry?.worlds" :key="world.id" class="world-feature">
        <NuxtLink v-if="manifests?.[world.id]?.presentation.concept" class="world-feature-image" :to="worldUrl(world.id)" :aria-label="`Открыть мир ${world.title}`"><img :src="manifests[world.id]!.presentation.concept!.src" :alt="manifests[world.id]!.presentation.concept!.alt" width="1672" height="941" fetchpriority="high"><span>{{ manifests[world.id]!.presentation.concept!.kind === 'concept' ? 'AI-концепт, не игровой скриншот' : 'Архитектура мира' }}</span></NuxtLink>
        <div class="world-feature-body"><p class="snapshot-label">Сейв {{ world.saveId }} <span>Снимок {{ new Date(world.snapshotAt).toLocaleDateString('ru-RU') }}</span></p><h2><NuxtLink :to="worldUrl(world.id)">{{ world.title }}</NuxtLink></h2><p>{{ constructionText(world.summary) }}</p><dl v-if="manifests?.[world.id]" class="world-scope"><div><dt>Тиры</dt><dd>{{ manifests[world.id]!.tiers.map(tier => tier.id).join(' / ') }}</dd></div><div><dt>Проекты</dt><dd>{{ manifests[world.id]!.projects.length }}</dd></div><div><dt>Анализы</dt><dd>{{ manifests[world.id]!.analyses.length }}</dd></div></dl><div class="button-row"><Button as-child><NuxtLink :to="worldUrl(world.id)">Открыть мир</NuxtLink></Button><NuxtLink class="text-link" :to="`${worldUrl(world.id)}#projects`">Найти проект</NuxtLink></div></div>
      </article>
    </div>
    <section v-if="registry && !registry.worlds.length" class="empty-state"><h2>Миров пока нет</h2><p>В реестре ещё нет опубликованных строительных планов.</p></section>
    <div class="atlas-home-note"><h2>Планы отдельно. Игра отдельно.</h2><p>Атлас не меняет сохранения. Личные отметки остаются в этом браузере, а расчёты и ограничения всегда привязаны к конкретному миру.</p></div>
  </main>
</template>
