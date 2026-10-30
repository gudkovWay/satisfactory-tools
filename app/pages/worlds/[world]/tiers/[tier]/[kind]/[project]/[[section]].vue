<script setup lang="ts">
import type { SectionId } from '~~/shared/types/project'
import { Printer } from '@lucide/vue'
definePageMeta({ key: route => route.path })
const route = useRoute()
const world = useWorld()
const saveId = world.value.record.saveId
const projectId = String(route.params.project)
const summary = world.value.manifest.projects.find(item => item.id === projectId)
if (!summary || summary.tier !== Number(route.params.tier) || summary.category !== route.params.kind) {
  throw createError({ statusCode: 404, statusMessage: 'Проект не найден в этом тире' })
}
const selected = String(route.params.section || 'overview')
const sectionItem = projectSections.find(item => item.id === selected)
if (!sectionItem) throw createError({ statusCode: 404, statusMessage: 'Такого раздела проекта нет' })
const section: SectionId = sectionItem.id
const { data: project, status, error, refresh } = useProjectDocument(saveId, projectId)
watchEffect(() => {
  if (error.value?.statusCode === 404 || (project.value && (project.value.id !== projectId || project.value.saveId !== saveId || project.value.source.saveSha256 !== world.value.manifest.saveSha256))) {
    showError(createError({ statusCode: 404, statusMessage: 'Проект не найден' }))
  }
})
useSeoMeta({ title: () => `${sectionItem.label} / ${project.value?.title || 'Проект'} / Заводской атлас` })
function printProject() { window.print() }
const showingZones = computed(() => Boolean(project.value?.zoneAtlas) && route.query.view !== 'drawings' && !route.query.drawing)
</script>

<template>
  <main id="main" class="project-page page-width">
    <p v-if="status === 'pending' && !project" class="empty-state" role="status">Загружаем строительный проект.</p>
    <div v-else-if="error || !project" class="empty-state" role="alert"><h1>Проект не загрузился</h1><p>Не удалось прочитать документ проекта. Повтори загрузку или вернись в каталог.</p><div class="button-row"><Button @click="refresh()">Загрузить проект ещё раз</Button><Button as-child variant="outline"><NuxtLink to="/">Все проекты</NuxtLink></Button></div></div>
    <div v-else class="project-layout">
      <ProjectNavigation :project="project" :section="section" />
      <div class="project-content">
      <nav class="world-project-breadcrumb" aria-label="Положение в мире"><NuxtLink :to="worldUrl(world.manifest.id)">{{ world.manifest.title }}</NuxtLink><span>/</span><NuxtLink :to="`${worldUrl(world.manifest.id)}/tiers/${summary.tier}`">Тир {{ summary.tier }}</NuxtLink><span>/</span><NuxtLink :to="projectUrl(world.manifest, summary.id)">{{ summary.category === 'factories' ? 'Завод' : 'Глобальный объект' }} · {{ summary.title }}</NuxtLink></nav>
        <header class="project-content-header">
          <div><p class="project-breadcrumb">{{ project.subtitle }}</p><h1 class="project-section-title">{{ section === 'overview' ? project.title : sectionItem.label }}</h1></div>
          <div class="project-header-tools"><ProjectSearch :project="project" /><Button variant="ghost" class="print-button" aria-label="Печать" @click="printProject"><Printer :size="17" aria-hidden="true" /><span>Печать</span></Button></div>
        </header>
        <ProjectReadiness :project="project" />
        <ProjectOverview v-if="section === 'overview'" :project="project" />
        <BuildGuide v-else-if="section === 'build'" :project="project" />
        <div v-else-if="section === 'drawings'" class="stack">
          <RouteSegments v-if="project.zoneAtlas" :selected="showingZones ? 0 : 1" :options="[
            { label: `Виды зон · ${project.zoneCount}`, to: { path: route.path, query: { zone: route.query.zone } } },
            { label: `Чертежи · ${project.drawingCount}`, to: { path: route.path, query: { view: 'drawings' } } }
          ]" />
          <ZoneAtlas v-if="showingZones" :project="project" />
          <DrawingViewer v-else :project="project" />
        </div>
        <ProjectBalance v-else-if="section === 'balance'" :project="project" />
        <section v-else-if="section === 'site'" class="stack"><h2>Площадка в архитектуре мира</h2><WorldDistrictMap v-if="world.manifest.map" /><p>Район привязан к общему плану; точные позиции машин и уровни — в чертежах этого проекта.</p><DataTable v-for="table in project.infrastructure.tables" :key="table.caption" :columns="table.columns" :rows="table.rows" :caption="table.caption" /></section>
        <ProjectInfrastructure v-else-if="section === 'infrastructure'" :project="project" />
        <ProjectParts v-else-if="section === 'parts'" :project="project" />
        <ProjectEvidence v-else :project="project" />
      </div>
    </div>
  </main>
</template>
