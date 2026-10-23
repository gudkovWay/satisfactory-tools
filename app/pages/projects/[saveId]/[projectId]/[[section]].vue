<script setup lang="ts">
import type { SectionId } from '~~/shared/types/project'
import { Printer } from '@lucide/vue'
definePageMeta({ key: route => route.path })
const route = useRoute()
const saveId = String(route.params.saveId)
const projectId = String(route.params.projectId)
const selected = String(route.params.section || 'overview')
const sectionItem = projectSections.find(item => item.id === selected)
if (!sectionItem) throw createError({ statusCode: 404, statusMessage: 'Такого раздела проекта нет' })
const section: SectionId = sectionItem.id
const { data: project, status, error, refresh } = useProjectDocument(saveId, projectId)
watchEffect(() => {
  if (error.value?.statusCode === 404 || (project.value && (project.value.id !== projectId || project.value.saveId !== saveId))) {
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
        <WorldMap v-else-if="section === 'site'" :project="project" />
        <ProjectInfrastructure v-else-if="section === 'infrastructure'" :project="project" />
        <ProjectParts v-else-if="section === 'parts'" :project="project" />
        <ProjectEvidence v-else :project="project" />
      </div>
    </div>
  </main>
</template>
