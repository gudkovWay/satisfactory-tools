<script setup lang="ts">
const route = useRoute()
const world = useWorld()
const manifest = computed(() => world.value.manifest)
const tier = manifest.value.tiers.find(item => item.id === Number(route.params.tier))
if (!tier) throw createError({ statusCode: 404, statusMessage: 'Тир не найден в этом мире' })
const index = manifest.value.tiers.findIndex(item => item.id === tier.id)
const previous = manifest.value.tiers[index - 1]
const next = manifest.value.tiers[index + 1]
const base = computed(() => worldUrl(manifest.value.id))
useSeoMeta({ title: () => `Тир ${tier.id} · ${tier.title} / ${manifest.value.title}` })
</script>
<template>
  <main id="main" class="page-width world-page"><NuxtLink class="text-link" :to="base">← {{ manifest.title }}</NuxtLink><header class="world-heading"><div><p class="eyebrow">Тир {{ tier.id }} / {{ constructionText(tier.gate) }}</p><h1>{{ tier.title }}</h1><p class="world-intro">{{ tier.goal }}</p></div><nav class="tier-neighbours" aria-label="Соседние тиры"><NuxtLink v-if="previous" class="text-link" :to="`${base}/tiers/${previous.id}`">← Тир {{ previous.id }}</NuxtLink><NuxtLink v-if="next" class="text-link" :to="`${base}/tiers/${next.id}`">Тир {{ next.id }} →</NuxtLink></nav></header>
    <section class="world-section"><h2>Порядок действий</h2><ol class="tier-sequence"><li v-for="(step, number) in tier.sequence" :key="step.project"><span class="sequence-number">{{ String(number + 1).padStart(2, '0') }}</span><div><p>{{ constructionText(step.action) }}</p><NuxtLink class="text-link" :to="projectUrl(manifest, step.project)">{{ manifest.projects.find(project => project.id === step.project)?.title }} →</NuxtLink></div></li></ol></section>
    <section class="world-section"><h2>Технологии и затраты</h2><p class="muted">Открытое в снимке отмечено отдельно. Необязательные удобства не блокируют производственный маршрут.</p><DataTable caption="Технологии выбранного мира и его закреплённого профиля" :columns="['Технология', 'Статус / роль', 'Стоимость']" :rows="tier.milestones.map(milestone => [milestone.name, milestone.purchased ? 'Уже куплено' : milestone.optional ? 'Необязательно для основной цепочки' : 'Купить по порядку выше', milestone.cost.length ? milestone.cost.map(cost => `${cost.item} ${cost.amount}`).join(' · ') : 'Автогрант в текущем сейве'])" /></section>
    <section class="world-section"><div class="world-section-heading"><h2>Глобальные здания</h2><p>Уже начатые объекты сохраняются; новые очереди имеют собственный план.</p></div><WorldProjectCards :ids="tier.globals" /></section><section class="world-section"><h2>Необходимые заводы этого тира</h2><WorldProjectCards :ids="tier.factories" /></section><section class="world-section world-boundary"><h2>Условия перехода</h2><ul><li v-for="check in tier.exitChecks" :key="check">{{ constructionText(check) }}</li></ul><NuxtLink class="text-link" :to="base">К анализу и архитектуре мира →</NuxtLink></section>
  </main>
</template>
