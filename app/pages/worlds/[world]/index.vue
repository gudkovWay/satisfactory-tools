<script setup lang="ts">
const world = useWorld()
const manifest = computed(() => world.value.manifest)
const base = computed(() => worldUrl(manifest.value.id))
useSeoMeta({ title: () => `${manifest.value.title} · мир и строительство` })
</script>
<template>
  <main id="main" class="page-width world-page">
    <NuxtLink class="text-link" to="/world">← Все миры</NuxtLink>
    <header class="world-heading"><div><p class="eyebrow">{{ constructionText(manifest.presentation.eyebrow) }}</p><h1>{{ manifest.title }}</h1><p class="world-intro">{{ manifest.presentation.intro }}</p></div><div class="world-snapshot"><div v-for="fact in manifest.presentation.facts" :key="fact.label"><span class="fine">{{ fact.label }}</span><strong class="block">{{ constructionText(fact.value) }}</strong></div><NuxtLink class="text-link" :to="`${base}/analysis/${manifest.sourceAnalysisId}`">Что подтверждено в сейве →</NuxtLink></div></header>
    <nav class="world-tier-nav" aria-label="Тиры прохождения"><NuxtLink v-for="tier in manifest.tiers" :key="tier.id" :to="`${base}/tiers/${tier.id}`"><span>Тир {{ tier.id }}</span><strong>{{ tier.title }}</strong><span aria-hidden="true">→</span></NuxtLink></nav>
    <WorldDistrictMap v-if="manifest.map" />
    <section class="world-section"><div class="world-section-heading"><h2>Основания плана</h2><p>Анализ мира, его архитектура и расчёты отделены от строительных инструкций.</p></div><div class="analysis-links"><NuxtLink v-for="analysis in manifest.analyses" :key="analysis.id" :to="`${base}/analysis/${analysis.id}`"><h3>{{ analysis.title }}</h3><p>{{ analysis.summary }}</p><span class="text-link">Открыть анализ →</span></NuxtLink></div></section>
    <section v-if="manifest.presentation.concept || manifest.presentation.links.length" class="world-section"><div class="world-section-heading"><h2>{{ manifest.presentation.architectureTitle }}</h2><p>{{ manifest.presentation.architectureBody }}</p></div><figure v-if="manifest.presentation.concept" class="world-concept"><img :src="manifest.presentation.concept.src" :alt="manifest.presentation.concept.alt" width="1672" height="941" loading="lazy"><figcaption>{{ manifest.presentation.concept.caption }}</figcaption></figure><div class="world-drawing-links"><a v-for="link in manifest.presentation.links" :key="link.url" class="text-link" :href="link.url" target="_blank" rel="noopener">{{ link.label }} ↗</a></div></section>
    <section v-if="manifest.presentation.boundary" class="world-section world-boundary"><h2>{{ manifest.presentation.boundary.title }}</h2><p>{{ constructionText(manifest.presentation.boundary.body) }}</p><NuxtLink class="text-link" :to="`${base}/analysis/${manifest.presentation.boundary.analysisId}`">Расчёты и условия перехода →</NuxtLink></section>
    <p class="fine">{{ constructionText(manifest.presentation.limitations) }}</p>
  </main>
</template>
