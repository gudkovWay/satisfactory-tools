<script setup lang="ts">
const world = useWorld()
const query = ref('')
const tier = ref('all')
const kind = ref('all')
const tierOptions = computed(() => [{ value: 'all', label: 'Все тиры' }, ...world.value.manifest.tiers.map(item => ({ value: String(item.id), label: `Тир ${item.id}` }))])
const kindOptions = [{ value: 'all', label: 'Все объекты' }, { value: 'factories', label: 'Заводы' }, { value: 'global', label: 'Инфраструктура' }]
const filtered = computed(() => {
  const words = query.value.toLocaleLowerCase('ru').trim().split(/\s+/).filter(Boolean)
  return world.value.manifest.projects.filter(project => {
    const labels = [project.title, project.site, ...project.outputs.map(flow => flow.label)]
    const text = [...labels, ...labels.map(atlasLabel)].join(' ').toLocaleLowerCase('ru')
    return (tier.value === 'all' || String(project.tier) === tier.value)
      && (kind.value === 'all' || project.category === kind.value)
      && words.every(word => text.includes(word))
  })
})
const hasFilters = computed(() => Boolean(query.value || tier.value !== 'all' || kind.value !== 'all'))
function clear() { query.value = ''; tier.value = 'all'; kind.value = 'all' }
</script>

<template>
  <section id="projects" class="world-section project-directory" aria-labelledby="directory-heading">
    <div class="directory-heading"><div><h2 id="directory-heading">Проекты мира</h2><p>Найди завод по продукту или выбери общий объект.</p></div><NuxtLink class="text-link" to="#route">Порядок строительства</NuxtLink></div>
    <div class="project-filters" role="search" aria-label="Найти строительный проект">
      <label class="field" for="world-project-search"><span>Проект или продукт</span><Input id="world-project-search" v-model="query" type="search" placeholder="Бетон, кабель, склад" /></label>
      <div class="field"><label for="directory-tier">Тир</label><TheSelect v-model="tier" trigger-id="directory-tier" :options="tierOptions" /></div>
      <div class="field"><label for="directory-kind">Тип объекта</label><TheSelect v-model="kind" trigger-id="directory-kind" :options="kindOptions" /></div>
    </div>
    <div class="project-result-line"><p role="status" aria-live="polite">Показано {{ filtered.length }} из {{ world.manifest.projects.length }}</p><button v-if="hasFilters" type="button" @click="clear">Сбросить фильтры</button></div>
    <WorldProjectCards v-if="filtered.length" :ids="filtered.map(project => project.id)" />
    <div v-else class="empty-state"><h3>{{ world.manifest.projects.length ? 'Ничего не найдено' : 'Проектов пока нет' }}</h3><p>{{ world.manifest.projects.length ? 'Измени запрос или убери ограничения по тиру и типу.' : 'Строительные проекты этого мира ещё не опубликованы.' }}</p><Button v-if="hasFilters" variant="outline" @click="clear">Показать все проекты</Button></div>
  </section>
</template>

<style scoped>
.project-directory { min-width: 0; }
.directory-heading { display: flex; align-items: end; flex-wrap: wrap; justify-content: space-between; gap: .5rem 1.5rem; margin-bottom: 1rem; }
.directory-heading h2 { font-size: clamp(1.5rem, 2.5vw, 2rem); font-weight: 550; letter-spacing: -.035em; margin: 0 0 .4rem; }
.directory-heading p { color: var(--muted); margin: 0; font-size: .9375rem; }
.project-filters { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: end; gap: .75rem; }
.project-filters>.field:first-child { grid-column: 1 / -1; }
.project-filters :deep(input),.project-filters :deep([role=combobox]) { min-height: 44px; }
.project-result-line { display: flex; align-items: center; justify-content: space-between; gap: .75rem; min-height: 56px; color: var(--muted); font-size: .875rem; }
.project-result-line p { margin: 0; }
.project-result-line button { min-height: 44px; padding: .5rem 0 .5rem .5rem; color: var(--ink); text-decoration: underline; text-underline-offset: .2em; }
.project-result-line button:hover { color: var(--accent); }
.project-directory :is(a,button):focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
@media (min-width: 850px) { .project-filters { grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) minmax(0, 1fr); gap: 1rem; } .project-filters>.field:first-child { grid-column: auto; } }
</style>
