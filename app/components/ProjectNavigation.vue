<script setup lang="ts">
import { LayoutDashboard, ListChecks, Layers, Workflow, MapPinned, Cable, Package, ShieldCheck, ArrowLeft } from '@lucide/vue'
import type { ProjectDocument, SectionId } from '~~/shared/types/project'
const props = defineProps<{ project: ProjectDocument; section: SectionId }>()
const world = useWorld()
const summary = computed(() => world.value.manifest.projects.find(item => item.id === props.project.id))
const icons = { overview: LayoutDashboard, build: ListChecks, drawings: Layers, balance: Workflow, site: MapPinned, infrastructure: Cable, parts: Package, evidence: ShieldCheck }
</script>

<template>
  <aside class="project-navigation" aria-label="Разделы проекта">
    <div class="project-nav-context"><NuxtLink class="back-link" :to="`${worldUrl(world.manifest.id)}/tiers/${summary?.tier}`"><ArrowLeft :size="15" aria-hidden="true" />Тир {{ summary?.tier }}</NuxtLink><strong>{{ project.title }}</strong><span v-if="project.target" class="fine">{{ formatRate(project.target.rate) }} {{ project.target.unit }} · расчётный выпуск</span></div>
    <nav class="project-section-links" aria-label="Рабочие разделы"><template v-for="(item, index) in projectSections" :key="item.id"><p v-if="index === 0 || index === 3 || index === 7" class="nav-group">{{ index === 0 ? 'Строительство' : index === 3 ? 'Справочник' : 'Основания' }}</p><NuxtLink :to="projectUrl(world.manifest, project.id, item.id)" :aria-current="section === item.id ? 'page' : undefined" class="section-link"><component :is="icons[item.id]" :size="17" :stroke-width="1.7" aria-hidden="true" /><span>{{ item.label }}</span></NuxtLink></template></nav>
    <div class="mobile-project-tools"><details class="mobile-project-menu"><summary aria-label="Разделы проекта">Разделы</summary><nav aria-label="Разделы проекта на мобильном"><NuxtLink v-for="item in projectSections" :key="item.id" :to="projectUrl(world.manifest, project.id, item.id)" :aria-current="section === item.id ? 'page' : undefined">{{ item.label }}</NuxtLink></nav></details><NuxtLink :to="projectUrl(world.manifest, project.id, 'build')" :aria-current="section === 'build' ? 'page' : undefined" class="mobile-work-link">Стройка</NuxtLink><NuxtLink :to="projectUrl(world.manifest, project.id, 'drawings')" :aria-current="section === 'drawings' ? 'page' : undefined" class="mobile-work-link">Чертежи</NuxtLink></div>
  </aside>
</template>
