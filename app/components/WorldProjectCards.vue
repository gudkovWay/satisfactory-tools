<script setup lang="ts">
const props = defineProps<{ ids: string[] }>()
const world = useWorld()
const projects = computed(() => props.ids.map(id => world.value.manifest.projects.find(project => project.id === id)).filter(item => item !== undefined))
const failedPreviews = ref<Record<string, boolean>>({})
const stages = new Intl.PluralRules('ru')
function stageCount(count: number) {
  const form = stages.select(count)
  return `${count} ${form === 'one' ? 'этап' : form === 'few' ? 'этапа' : 'этапов'}`
}
</script>

<template>
  <div class="project-cards">
    <article v-for="project in projects" :key="project.id" class="project-card">
      <NuxtLink class="project-card-preview" :to="projectUrl(world.manifest, project.id)" :aria-label="`Открыть проект: ${project.title}`">
        <img v-if="project.preview?.src && !failedPreviews[project.preview.src]" :src="project.preview.src" :alt="project.preview.alt" loading="lazy" width="240" height="160" @error="failedPreviews[project.preview!.src] = true">
        <span v-else>{{ project.preview?.src ? 'Превью недоступно' : 'Без превью' }}</span>
      </NuxtLink>
      <div class="project-card-identity">
        <h3><NuxtLink :to="projectUrl(world.manifest, project.id)">{{ atlasLabel(project.title.replace(/^Прежняя редакция\s*·\s*/, '')) }}</NuxtLink></h3>
        <p class="project-card-meta"><span>Тир {{ project.tier }}</span><span>{{ stageCount(project.stages) }}</span><span>{{ project.category === 'factories' ? 'Завод' : 'Инфраструктура' }}</span><span v-if="project.integrationStatus === 'preserved-previous'">Архивный план</span><span v-if="project.optional">Необязательный вариант</span></p>
      </div>
      <dl v-if="project.outputs.length" class="project-card-outputs" aria-label="Расчётный выпуск">
        <div v-for="flow in project.outputs" :key="flow.itemId"><dt>{{ atlasLabel(flow.label) }}</dt><dd>{{ formatRate(flow.rate) }} <span>{{ flow.unit || '/мин' }}</span></dd></div>
      </dl>
      <p v-else class="project-card-purpose">Общий объект мира</p>
      <NuxtLink class="project-card-build" :to="projectUrl(world.manifest, project.id, 'build')">К этапам<span class="sr-only"> проекта {{ project.title }}</span></NuxtLink>
    </article>
  </div>
</template>

<style scoped>
.project-cards { display: grid; gap: .5rem; min-width: 0; }
.project-card { display: grid; grid-template-columns: 5.5rem minmax(0, 1fr); gap: .5rem .875rem; align-items: start; padding: .875rem; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; }
.project-card-preview { display: grid; place-items: center; grid-row: 1 / 3; min-width: 0; aspect-ratio: 3 / 2; background: var(--surface-raised); color: var(--muted); border-radius: 4px; text-decoration: none; }
.project-card-preview img { width: 100%; height: 100%; aspect-ratio: 3 / 2; object-fit: contain; border-radius: inherit; }
.project-card-preview>span { padding: .375rem; font-size: .75rem; text-align: center; }
.project-card-identity { min-width: 0; }
.project-card-identity h3 { margin: 0; font-size: 1rem; font-weight: 550; line-height: 1.4; letter-spacing: -.015em; }
.project-card-identity h3 a { display: inline-flex; align-items: center; min-height: 44px; color: var(--ink); text-decoration: none; }
.project-card-identity h3 a:hover { color: var(--accent); }
.project-card-meta { display: flex; flex-wrap: wrap; gap: .2rem .75rem; margin: .2rem 0 0; color: var(--muted); font-size: .8125rem; line-height: 1.6; }
.project-card-outputs { grid-column: 1 / -1; display: grid; gap: .25rem; margin: .25rem 0 0; font-size: .875rem; }
.project-card-outputs>div { display: flex; justify-content: space-between; gap: .5rem; align-items: baseline; }
.project-card-outputs dt { min-width: 0; }
.project-card-outputs dd { flex: none; margin: 0; font-weight: 550; font-variant-numeric: tabular-nums; text-align: right; }
.project-card-outputs dd span { font-weight: 400; color: var(--muted); }
.project-card-purpose { grid-column: 1 / -1; margin: .25rem 0 0; color: var(--muted); font-size: .875rem; }
.project-card-build { grid-column: 1 / -1; display: inline-flex; align-items: center; justify-self: end; min-height: 44px; padding: .375rem .5rem; color: var(--ink); font-size: .875rem; text-decoration: underline; text-underline-offset: .2em; }
.project-card-build:hover { color: var(--accent); }
.project-cards a:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
@media (min-width: 700px) {
  .project-card { grid-template-columns: 7rem minmax(0, 1.2fr) minmax(0, 1fr); align-items: center; gap: .75rem 1rem; padding: .75rem 1rem; }
  .project-card-preview { grid-column: 1; grid-row: 1 / 3; }
  .project-card-identity { grid-column: 2; grid-row: 1 / 3; }
  .project-card-outputs,.project-card-purpose { grid-column: 3; grid-row: 1; margin: 0; }
  .project-card-build { grid-column: 3; grid-row: 2; }
}
@media (min-width: 1180px) {
  .project-card { grid-template-columns: 8rem minmax(0, 1.35fr) minmax(0, 1fr) auto; gap: 1.25rem; }
  .project-card-preview,.project-card-identity { grid-row: 1; }
  .project-card-build { grid-column: 4; grid-row: 1; }
}
</style>
