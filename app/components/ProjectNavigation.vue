<script setup lang="ts">
import { LayoutDashboard, ListChecks, Layers, Workflow, MapPinned, Cable, Package, ShieldCheck, ArrowLeft } from '@lucide/vue'
import type { ProjectDocument, SectionId } from '~~/shared/types/project'
const props = defineProps<{ project: ProjectDocument; section: SectionId }>()
const world = useWorld()
const summary = computed(() => world.value.manifest.projects.find(item => item.id === props.project.id))
const icons = { overview: LayoutDashboard, build: ListChecks, drawings: Layers, balance: Workflow, site: MapPinned, infrastructure: Cable, parts: Package, evidence: ShieldCheck }
const sectionOptions = projectSections.map(item => ({ value: item.id, label: item.label }))
function selectSection(value: string | number) {
  const section = projectSections.find(item => item.id === value)
  if (section) void navigateTo(projectUrl(world.value.manifest, props.project.id, section.id))
}
</script>

<template>
  <aside class="project-navigation" aria-label="Разделы проекта">
    <div class="project-nav-context"><NuxtLink class="back-link" :to="`${worldUrl(world.manifest.id)}/tiers/${summary?.tier}`"><ArrowLeft :size="15" aria-hidden="true" />К тиру {{ summary?.tier }}</NuxtLink><img v-if="project.preview" :src="project.preview.src" alt="" width="216" height="104"><p>{{ world.manifest.title }}</p><strong>{{ project.title }}</strong><span v-if="project.target" class="fine">{{ formatRate(project.target.rate) }} {{ project.target.unit }} · план</span></div>
    <nav class="project-section-links" aria-label="Рабочие разделы"><template v-for="(item, index) in projectSections" :key="item.id"><p v-if="index === 0 || index === 3 || index === 7" class="nav-group">{{ index === 0 ? 'Проект' : index === 3 ? 'Справочник' : 'Основания' }}</p><NuxtLink :to="projectUrl(world.manifest, project.id, item.id)" :aria-current="section === item.id ? 'page' : undefined" class="section-link"><component :is="icons[item.id]" :size="17" :stroke-width="1.7" aria-hidden="true" /><span>{{ item.label }}</span></NuxtLink></template></nav>
    <div class="field mobile-section-select"><label for="section-select">Раздел проекта</label><TheSelect trigger-id="section-select" :model-value="section" :options="sectionOptions" @update:model-value="selectSection" /></div>
  </aside>
</template>
