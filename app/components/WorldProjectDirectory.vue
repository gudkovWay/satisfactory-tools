<script setup lang="ts">
const world = useWorld()
const query = ref('')
const tier = ref('all')
const kind = ref('all')
const tierOptions = computed(() => [{ value: 'all', label: 'Все тиры' }, ...world.value.manifest.tiers.map(item => ({ value: String(item.id), label: `Тир ${item.id}` }))])
const kindOptions = [{ value: 'all', label: 'Все объекты' }, { value: 'factories', label: 'Заводы' }, { value: 'global', label: 'Глобальные здания' }]
const filtered = computed(() => {
  const words = query.value.toLocaleLowerCase('ru').trim().split(/\s+/).filter(Boolean)
  return world.value.manifest.projects.filter(project => {
    const text = [project.title, project.site, ...project.outputs.map(flow => flow.label)].join(' ').toLocaleLowerCase('ru')
    return (tier.value === 'all' || String(project.tier) === tier.value)
      && (kind.value === 'all' || project.category === kind.value)
      && words.every(word => text.includes(word))
  })
})
function clear() { query.value = ''; tier.value = 'all'; kind.value = 'all' }
</script>
<template>
  <section id="projects" class="world-section project-directory" aria-labelledby="directory-heading">
    <div class="world-section-heading"><div><h2 id="directory-heading">Найти свой проект</h2><p>Выбери объект по названию, продукту или району. Если строишь с нуля, начни с маршрута тиров.</p></div><NuxtLink class="text-link" to="#route">К порядку строительства</NuxtLink></div>
    <div class="directory-filters">
      <label class="field" for="world-project-search"><span>Проект, продукт или район</span><Input id="world-project-search" v-model="query" type="search" placeholder="Например, бетон или склад" /></label>
      <div class="field"><label for="directory-tier">Тир</label><TheSelect v-model="tier" trigger-id="directory-tier" :options="tierOptions" /></div>
      <div class="field"><label for="directory-kind">Объекты</label><TheSelect v-model="kind" trigger-id="directory-kind" :options="kindOptions" /></div>
    </div>
    <div class="directory-result-line"><p role="status">{{ filtered.length }} из {{ world.manifest.projects.length }} проектов</p><button v-if="query || tier !== 'all' || kind !== 'all'" type="button" class="plain-button" @click="clear">Сбросить фильтры</button></div>
    <WorldProjectCards v-if="filtered.length" :ids="filtered.map(project => project.id)" />
    <div v-else class="empty-state"><h3>Таких проектов нет</h3><p>Попробуй другой продукт или убери ограничения по тиру и типу.</p><Button variant="outline" @click="clear">Показать все проекты</Button></div>
  </section>
</template>
