<script setup lang="ts">
const world = useWorld()
const manifest = computed(() => world.value.manifest)
const base = computed(() => worldUrl(manifest.value.id))
const firstTier = computed(() => manifest.value.tiers[0])
const warehouse = computed(() => manifest.value.projects.find(project => project.id === 'warehouse'))
const warehouseDrawings = computed(() => warehouse.value ? projectUrl(manifest.value, warehouse.value.id, 'drawings') : null)
const warehousePreviewFailed = ref(false)
const campusDrawingIds = ['campus-freight-concrete-only-01', 'campus-freight-first-plate-01', 'campus-freight-01', 'campus-power-concrete-only-01', 'campus-power-first-plate-01', 'campus-power-optional-fuel-01', 'campus-power-01', 'campus-power-02', 'campus-power-03', 'campus-power-04', 'campus-power-05']
const sourceDrawingLinks = computed(() => manifest.value.presentation.links.map(link => {
  const filename = link.url.split('/').pop()
  const drawing = filename === 'render.png' ? 'blender-assembly' : campusDrawingIds.find(id => filename === `${id}.svg`)
  return { ...link, drawing }
}))
const actionForms = new Intl.PluralRules('ru')
function actionCount(count: number) {
  const form = actionForms.select(count)
  return `${count} ${form === 'one' ? 'действие' : form === 'few' ? 'действия' : 'действий'}`
}
useSeoMeta({ title: () => `${manifest.value.title} · мир и строительство` })
</script>

<template>
  <main id="main" class="page-width world-page world-workspace">
    <header class="world-heading workspace-heading">
      <div><h1>{{ manifest.title }}</h1><p class="world-intro">{{ constructionText(manifest.presentation.intro) }}</p></div>
      <div class="button-row"><Button v-if="firstTier" as-child><NuxtLink :to="`${base}/tiers/${firstTier.id}`">Начать с тира {{ firstTier.id }}</NuxtLink></Button><NuxtLink class="text-link" to="#projects">Выбрать проект</NuxtLink></div>
    </header>

    <section id="route" class="world-section workspace-section" aria-labelledby="route-heading">
      <div class="workspace-section-heading"><div><h2 id="route-heading">Порядок строительства</h2><p>Выбери тир, чтобы пройти его проекты и проверить условия перехода.</p></div><NuxtLink class="text-link" :to="`${base}/analysis/${manifest.sourceAnalysisId}`">Исходные условия</NuxtLink></div>
      <nav class="world-tier-nav workspace-tiers" aria-label="Тиры строительства">
        <NuxtLink v-for="tier in manifest.tiers" :key="tier.id" :to="`${base}/tiers/${tier.id}`"><span class="tier-marker">{{ tier.id }}</span><span class="tier-nav-copy"><span>Тир {{ tier.id }}</span><strong>{{ atlasLabel(tier.title) }}</strong><small>{{ actionCount(tier.sequence.length) }}</small></span></NuxtLink>
      </nav>
    </section>

    <WorldProjectDirectory />

    <section v-if="warehouse && warehouseDrawings" id="infrastructure" class="world-section workspace-section" aria-labelledby="infrastructure-heading">
      <div class="workspace-section-heading"><div><h2 id="infrastructure-heading">Склад и общие сети</h2><p>План склада и соединения между проектами открываются отдельно.</p></div></div>
      <div class="infrastructure-entries">
        <article class="warehouse-entry">
          <NuxtLink v-if="warehouse.preview?.src && !warehousePreviewFailed" class="warehouse-preview" :to="{ path: warehouseDrawings, query: { view: 'drawings', drawing: 'blender-assembly' } }" aria-label="Открыть объёмную схему склада"><img :src="warehouse.preview.src" :alt="warehouse.preview.alt" width="640" height="400" loading="lazy" @error="warehousePreviewFailed = true"></NuxtLink>
          <div class="infrastructure-entry-copy"><h3>Адресный склад</h3><p>Размещение контейнеров, сборка рядов и подвод конвейеров внутри склада.</p>
            <nav aria-label="Проект склада"><NuxtLink :to="projectUrl(manifest, warehouse.id)">Открыть проект склада</NuxtLink><NuxtLink :to="{ path: warehouseDrawings, query: { view: 'drawings', drawing: 'layout' } }">Размерный план</NuxtLink><NuxtLink :to="{ path: warehouseDrawings, query: { view: 'drawings', drawing: 'assembly-G0-row-01' } }">Сборка рядов</NuxtLink></nav>
          </div>
        </article>
        <article class="campus-entry"><h3>Инфраструктура кампуса</h3><p>Доставка материалов между заводами и общее питание. Эти сети относятся ко всему домашнему району, а не только к складу.</p>
          <nav aria-label="Общие сети кампуса"><NuxtLink :to="{ path: warehouseDrawings, query: { view: 'drawings', drawing: 'campus-freight-01' } }">Доставка между проектами</NuxtLink><NuxtLink :to="{ path: warehouseDrawings, query: { view: 'drawings', drawing: 'campus-power-01' } }">Электросеть кампуса</NuxtLink></nav>
          <details class="campus-startup"><summary>Сети при первом запуске</summary><nav aria-label="Пусковые состояния сетей"><NuxtLink :to="{ path: warehouseDrawings, query: { view: 'drawings', drawing: 'campus-freight-concrete-only-01' } }">Доставка при пуске бетона</NuxtLink><NuxtLink :to="{ path: warehouseDrawings, query: { view: 'drawings', drawing: 'campus-power-concrete-only-01' } }">Питание при пуске бетона</NuxtLink><NuxtLink :to="{ path: warehouseDrawings, query: { view: 'drawings', drawing: 'campus-freight-first-plate-01' } }">Доставка при пуске пластин</NuxtLink><NuxtLink :to="{ path: warehouseDrawings, query: { view: 'drawings', drawing: 'campus-power-first-plate-01' } }">Питание при пуске пластин</NuxtLink></nav></details>
        </article>
      </div>
    </section>

    <section v-if="manifest.map" id="map" class="world-section workspace-section"><WorldDistrictMap /></section>

    <section id="analyses" class="world-section workspace-section" aria-labelledby="analyses-heading">
      <div class="workspace-section-heading"><div><h2 id="analyses-heading">Расчёты и условия</h2><p>Площадки, доступные технологии и ограничения строительного плана.</p></div></div>
      <div class="analysis-links workspace-analyses"><NuxtLink v-for="analysis in manifest.analyses" :key="analysis.id" :to="`${base}/analysis/${analysis.id}`"><h3>{{ atlasLabel(analysis.title.replace(/^\d+\s*·\s*/, '')) }}</h3><p>{{ constructionText(analysis.summary) }}</p><span>Открыть расчёты</span></NuxtLink></div>
    </section>

    <section v-if="manifest.presentation.boundary" class="world-section workspace-section world-boundary"><h2>{{ manifest.presentation.boundary.title }}</h2><p>{{ constructionText(manifest.presentation.boundary.body) }}</p><NuxtLink class="text-link" :to="`${base}/analysis/${manifest.presentation.boundary.analysisId}`">Условия перехода на материк</NuxtLink></section>

    <section id="data" class="world-section workspace-section world-data" aria-labelledby="world-data-heading">
      <h2 id="world-data-heading">Данные мира</h2>
      <p class="world-data-warning">Перед строительством проверь рельеф, коллизии и доступность деталей в игре. Атлас не меняет сохранение.</p>
      <details><summary>Источник и ограничения расчёта</summary><dl class="world-source-facts"><div><dt>Сохранение</dt><dd>{{ manifest.saveId }}</dd></div><div><dt>Снимок</dt><dd>{{ new Date(manifest.snapshotAt).toLocaleDateString('ru-RU') }}</dd></div><div v-for="fact in manifest.presentation.facts" :key="fact.label"><dt>{{ fact.label }}</dt><dd>{{ constructionText(fact.value) }}</dd></div></dl><p>{{ constructionText(manifest.presentation.limitations) }}</p><NuxtLink class="text-link" :to="`${base}/analysis/${manifest.sourceAnalysisId}`">Анализ сохранения и источники</NuxtLink></details>
      <details><summary>Материалы архитектурного плана</summary><h3>{{ manifest.presentation.architectureTitle }}</h3><p>{{ constructionText(manifest.presentation.architectureBody) }}</p><figure v-if="manifest.presentation.concept" class="world-data-concept"><img :src="manifest.presentation.concept.src" :alt="manifest.presentation.concept.alt" loading="lazy" width="960" height="540"><figcaption>{{ manifest.presentation.concept.caption }}</figcaption></figure><ul v-if="sourceDrawingLinks.length" class="world-source-links"><li v-for="link in sourceDrawingLinks" :key="link.url"><NuxtLink v-if="warehouseDrawings && link.drawing" :to="{ path: warehouseDrawings, query: { view: 'drawings', drawing: link.drawing } }">{{ atlasLabel(link.label) }}</NuxtLink><a v-else :href="link.url">{{ atlasLabel(link.label) }}</a></li></ul></details>
    </section>
  </main>
</template>

<style scoped>
.workspace-heading h1 { font-size: clamp(2rem, 4vw, 3rem); line-height: 1.15; font-weight: 550; margin-bottom: .75rem; }
.workspace-heading { margin-bottom: 1.5rem; }
.workspace-heading .world-intro { max-width: 75ch; font-size: 1rem; }
.workspace-section,.world-workspace :deep(.project-directory) { margin-block: 2.5rem; }
.workspace-section-heading { display: flex; flex-wrap: wrap; align-items: end; justify-content: space-between; gap: .5rem 1.5rem; margin-bottom: 1rem; }
.workspace-section-heading h2,.world-data>h2 { font-size: clamp(1.5rem, 2.5vw, 2rem); line-height: 1.25; font-weight: 550; letter-spacing: -.035em; margin: 0 0 .5rem; }
.workspace-section-heading p { color: var(--muted); max-width: 65ch; margin: 0; font-size: .9375rem; }
.workspace-tiers { gap: .75rem; }
.workspace-tiers a { padding: 1rem; border-radius: 8px; transition: none; }
.workspace-tiers a:hover { transform: none; background: var(--surface-raised); border-color: var(--line); }
.workspace-tiers .tier-marker { font-size: 2rem; }
.infrastructure-entries { display: grid; gap: 1rem; }
.infrastructure-entries article { min-width: 0; background: var(--surface); border-radius: 8px; padding: 1.25rem; }
.infrastructure-entries h3 { font-size: 1.25rem; font-weight: 550; margin-bottom: .5rem; }
.infrastructure-entries p { color: var(--muted); font-size: .9375rem; }
.infrastructure-entries nav { display: flex; flex-direction: column; align-items: start; gap: .25rem; }
.infrastructure-entries nav a { display: inline-flex; align-items: center; min-height: 44px; padding-block: .375rem; font-size: .9375rem; text-underline-offset: .2em; }
.warehouse-preview { display: block; margin-bottom: 1rem; background: var(--surface-raised); border-radius: 4px; }
.warehouse-preview img { width: 100%; max-height: 220px; object-fit: contain; border-radius: inherit; }
.campus-startup { margin-top: .75rem; font-size: .875rem; }
.workspace-analyses { grid-template-columns: minmax(0, 1fr); gap: .75rem; }
.workspace-analyses a { padding: 1rem 1.25rem; border-radius: 8px; transition: none; }
.workspace-analyses a:hover { transform: none; background: var(--surface-raised); border-color: var(--line); }
.workspace-analyses h3 { font-size: 1.125rem; line-height: 1.4; letter-spacing: -.02em; margin: 0; }
.workspace-analyses p { margin: .5rem 0 .75rem; }
.world-data-warning { color: var(--muted); max-width: 75ch; font-size: .9375rem; }
.world-data details { padding-block: .25rem; border-bottom: 1px solid var(--line); }
.world-data summary { min-height: 44px; }
.world-data details>p { max-width: 85ch; }
.world-source-facts { display: grid; gap: 1rem; margin-block: 1rem; }
.world-source-facts dt { color: var(--muted); font-size: .875rem; }
.world-source-facts dd { margin: .25rem 0 0; overflow-wrap: anywhere; }
.world-data-concept { margin: 1rem 0; max-width: 48rem; }
.world-data-concept img { width: 100%; border-radius: 6px; }
.world-source-links { margin-block: 1rem; padding: 0; list-style: none; }
.world-source-links li+li { margin: 0; }
.world-source-links a { display: inline-flex; min-height: 44px; align-items: center; padding-block: .375rem; }
.world-workspace :is(a,summary):focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
@media (min-width: 700px) {
  .infrastructure-entries { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .workspace-analyses { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .world-source-facts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (min-width: 1150px) {
  .warehouse-entry { display: grid; grid-template-columns: minmax(0, .8fr) minmax(0, 1fr); gap: 1.25rem; }
  .warehouse-preview { align-self: start; margin: 0; }
}
</style>
