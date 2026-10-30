<script setup lang="ts">
const props = defineProps<{ ids: string[] }>()
const world = useWorld()
const projects = computed(() => props.ids.map(id => world.value.manifest.projects.find(project => project.id === id)).filter(item => item !== undefined))

function removeFilteredRow(_element: Element, done: () => void) {
  done()
}
</script>
<template>
  <TransitionGroup name="project-list" tag="div" class="world-project-list" @leave="removeFilteredRow">
    <article v-for="project in projects" :key="project.id" class="project-register-row">
      <div class="register-identity"><span class="project-kind"><span class="register-number">{{ String(world.manifest.projects.findIndex(item => item.id === project.id) + 1).padStart(2, '0') }}</span>{{ project.category === 'factories' ? 'Завод' : 'Глобальный объект' }}<span v-if="project.optional"> · необязательный вариант</span></span><h3><NuxtLink :to="projectUrl(world.manifest, project.id)">{{ project.title }}</NuxtLink></h3><p>{{ project.site }}</p></div>
      <dl class="register-outputs"><div v-for="flow in project.outputs" :key="flow.itemId"><dt>{{ flow.label }}</dt><dd>{{ formatRate(flow.rate) }} <span>/ мин</span></dd></div><div v-if="!project.outputs.length"><dt>Назначение</dt><dd class="register-purpose">Инфраструктура мира</dd></div></dl>
      <div class="register-meta"><span>Тир {{ project.tier }}</span><span>{{ project.stages }} этапов</span></div>
      <NuxtLink class="register-build" :to="projectUrl(world.manifest, project.id, 'build')">К стройке<span class="sr-only">: {{ project.title }}</span></NuxtLink>
    </article>
  </TransitionGroup>
</template>
