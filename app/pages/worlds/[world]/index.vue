<script setup lang="ts">
const world = useWorld()
const manifest = computed(() => world.value.manifest)
const base = computed(() => worldUrl(manifest.value.id))
const firstTier = computed(() => manifest.value.tiers[0])
useSeoMeta({ title: () => `${manifest.value.title} · мир и строительство` })
</script>
<template>
  <main id="main" class="page-width world-page">
    <header class="world-heading world-dashboard-heading"><div><h1>{{ manifest.title }}</h1><p class="world-intro">{{ manifest.presentation.intro }}</p></div><div class="button-row"><Button v-if="firstTier" as-child><NuxtLink :to="`${base}/tiers/${firstTier.id}`">Начать с тира {{ firstTier.id }}</NuxtLink></Button><NuxtLink class="text-link" to="#projects">Найти проект</NuxtLink></div></header>
    <dl class="world-fact-strip"><div v-for="fact in manifest.presentation.facts" :key="fact.label"><dt>{{ fact.label }}</dt><dd>{{ constructionText(fact.value) }}</dd></div></dl>
    <section id="route" class="world-section progression-section" aria-labelledby="route-heading"><div class="world-section-heading"><div><h2 id="route-heading">Строить по порядку</h2><p>От домашнего снабжения к первому выходу на материк. У каждого тира свой порядок действий и условия перехода.</p></div><NuxtLink class="text-link" :to="`${base}/analysis/${manifest.sourceAnalysisId}`">Основания плана</NuxtLink></div><nav class="world-tier-nav" aria-label="Тиры прохождения"><NuxtLink v-for="tier in manifest.tiers" :key="tier.id" :to="`${base}/tiers/${tier.id}`"><span class="tier-marker">{{ tier.id }}</span><span class="tier-nav-copy"><span>Тир {{ tier.id }}</span><strong>{{ tier.title }}</strong><small>{{ tier.sequence.length }} действий по плану</small></span></NuxtLink></nav></section>
    <section v-if="manifest.presentation.concept" class="world-visual-intro"><figure><img :src="manifest.presentation.concept.src" :alt="manifest.presentation.concept.alt" width="1672" height="941"><figcaption>{{ manifest.presentation.concept.caption }}</figcaption></figure><div><h2>{{ manifest.presentation.architectureTitle }}</h2><p>{{ manifest.presentation.architectureBody }}</p><div class="world-drawing-links"><a v-for="link in manifest.presentation.links" :key="link.url" class="text-link" :href="link.url" target="_blank" rel="noopener">{{ link.label }}<span class="sr-only"> (новая вкладка)</span></a></div></div></section>
    <WorldProjectDirectory />
    <section v-if="manifest.map" id="map" class="world-section"><div class="world-section-heading"><div><h2>Найти место на острове</h2><p>Выбери район на карте или в списке. Площадка и связанные проекты откроются рядом.</p></div></div><WorldDistrictMap /></section>
    <section id="analyses" class="world-section"><div class="world-section-heading"><div><h2>Разобраться в плане</h2><p>Сейв, возможности модов и принятые решения. Здесь расчёты, на которых основана стройка.</p></div></div><div class="analysis-links"><NuxtLink v-for="analysis in manifest.analyses" :key="analysis.id" :to="`${base}/analysis/${analysis.id}`"><h3>{{ analysis.title.replace(/^\d+\s*·\s*/, '') }}</h3><p>{{ constructionText(analysis.summary) }}</p><span>Читать анализ</span></NuxtLink></div></section>
    <section v-if="!manifest.presentation.concept && manifest.presentation.links.length" class="world-section"><h2>{{ manifest.presentation.architectureTitle }}</h2><p>{{ manifest.presentation.architectureBody }}</p><div class="world-drawing-links"><a v-for="link in manifest.presentation.links" :key="link.url" class="text-link" :href="link.url" target="_blank" rel="noopener">{{ link.label }}</a></div></section>
    <section v-if="manifest.presentation.boundary" class="world-section world-boundary"><h2>{{ manifest.presentation.boundary.title }}</h2><p>{{ constructionText(manifest.presentation.boundary.body) }}</p><NuxtLink class="text-link" :to="`${base}/analysis/${manifest.presentation.boundary.analysisId}`">Расчёты и условия перехода</NuxtLink></section>
    <p class="fine world-limitations">{{ constructionText(manifest.presentation.limitations) }}</p>
  </main>
</template>
