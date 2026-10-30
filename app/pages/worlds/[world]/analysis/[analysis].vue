<script setup lang="ts">
const route = useRoute()
const world = useWorld()
const analysis = world.value.analyses.find(item => item.id === route.params.analysis)
if (!analysis) throw createError({ statusCode: 404, statusMessage: 'Анализ не найден в этом мире' })
const base = computed(() => worldUrl(world.value.manifest.id))
const descriptor = world.value.manifest.analyses.find(item => item.id === analysis.id)!
useSeoMeta({ title: () => `${analysis.title} / ${world.value.manifest.title}` })
const extractorOptions = (analysis.extractors ?? []).map(item => ({ value: String(item.id), label: `${item.label} · тир ${item.tier}` }))
const miner = ref(extractorOptions[0]?.value || '')
const states = computed(() => analysis.states?.filter(state => state.miner === Number(miner.value)) ?? [])
</script>
<template>
  <main id="main" class="page-width world-page analysis-page">
    <NuxtLink class="text-link" :to="base">← {{ world.manifest.title }}</NuxtLink>
    <header class="world-heading"><div><p class="eyebrow">Последовательный анализ / исходные данные отдельно от проекта</p><h1>{{ analysis.title }}</h1><p class="world-intro">{{ analysis.summary }}</p></div></header>
    <nav class="analysis-step-nav" aria-label="Документы анализа"><NuxtLink v-for="item in world.manifest.analyses" :key="item.id" :to="`${base}/analysis/${item.id}`" :aria-current="item.id === analysis.id ? 'page' : undefined">{{ item.title }}</NuxtLink></nav>
    <div class="analysis-content"><article v-for="section in analysis.sections" :key="section.title"><h2>{{ section.title }}</h2><p v-for="paragraph in section.paragraphs" :key="paragraph">{{ constructionText(paragraph) }}</p></article></div>
    <section v-if="analysis.states?.length" class="world-section"><h2>Добыча, линии и мощность</h2><div class="field state-selector"><label for="miner-state">Класс экстрактора</label><TheSelect trigger-id="miner-state" :model-value="miner" :options="extractorOptions" @update:model-value="miner = String($event)" /></div><DataTable caption="Номинальная непрерывная работа; порты не удваивают общий выпуск" :columns="['Чистота', 'Частота', 'Осколки', 'Руда / мин', 'Порты', 'Вывоз / мин', 'MW']" :rows="states.map(state => [state.purity, `${state.clock * 100}%`, String(state.shards), formatRate(state.raw), String(state.ports), `${state.lanes} × ${formatRate(state.perLane)} ≤ ${state.belt}`, formatRate(state.powerMW)])" /></section>
    <figure v-for="asset in analysis.media" :key="asset.src" class="world-concept"><img :src="asset.src" :alt="asset.alt" width="1600" height="1000" loading="lazy"><figcaption>{{ asset.caption }}</figcaption></figure>
    <section v-for="table in analysis.tables" :key="table.caption" class="world-section"><DataTable :columns="table.columns" :rows="table.rows" :caption="table.caption" /></section>
    <section class="world-section"><h2>Источники и переносимость</h2><ul><li v-for="source in analysis.sources" :key="source.url"><a class="text-link" :href="source.url" target="_blank" rel="noopener">{{ source.label }}</a></li></ul><a class="text-link" :href="`${base}/${descriptor.path}`" download>Скачать закреплённый анализ JSON</a><p class="fine recipe-path">Сейв {{ world.record.saveId }} · SHA-256: {{ world.manifest.saveSha256 }}</p><p class="fine">Изменение сейва или профиля мира требует пересмотра зависимых расчётов. Арифметика не доказывает работу в игре.</p></section>
  </main>
</template>
