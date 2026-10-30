<script setup lang="ts">
import type { WorldRegistry } from '~~/shared/types/world'
definePageMeta({ alias: ['/world'] })
const { data: registry, status, error, refresh } = await useFetch<WorldRegistry>('/worlds/index.json', { key: 'atlas-world-registry' })
useSeoMeta({ title: 'Миры / Строительный атлас Satisfactory' })
</script>
<template>
  <main id="main" class="page-width world-page">
    <header class="world-heading"><div><p class="eyebrow">Satisfactory / строительный атлас</p><h1>Миры</h1><p class="world-intro">У каждого мира — свои сейвы, настройки, ресурсы и архитектура. Внутри сохраняется путь: анализ → тир → глобальный объект или завод → этап строительства.</p></div></header>
    <p v-if="status === 'pending'" role="status">Загружаем каталог миров.</p>
    <section v-else-if="error" class="empty-state" role="alert"><h2>Каталог не загрузился</h2><Button @click="refresh()">Повторить загрузку</Button></section>
    <div v-else class="world-project-list"><NuxtLink v-for="world in registry?.worlds" :key="world.id" class="world-project-link" :to="worldUrl(world.id)"><div><p class="fine">Сейв {{ world.saveId }} · снимок {{ new Date(world.snapshotAt).toLocaleDateString('ru-RU') }}</p><h2>{{ world.title }}</h2><p>{{ constructionText(world.summary) }}</p><span class="text-link">Открыть мир →</span></div></NuxtLink></div>
    <p v-if="registry && !registry.worlds.length" class="empty-state">В реестре пока нет миров.</p>
    <p class="fine">Расчёты, проекты и личные отметки изолированы по контексту мира и сейва. Сохранения игры не изменяются.</p>
  </main>
</template>
