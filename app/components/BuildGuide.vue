<script setup lang="ts">
import type { Drawing, GuideStep, Level, ProjectDocument } from '~~/shared/types/project'
import { useMediaQuery } from '@vueuse/core'

const props = defineProps<{ project: ProjectDocument }>()
const world = useWorld()
const { blockGrid, horizontal, vertical, floorHeight } = useConstructionUnits(() => props.project)
const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
const stageDirection = ref(1)
const stageList = useTemplateRef<HTMLElement>('stage-list')
const stageScroll = useTemplateRef<HTMLElement>('stage-scroll')
const route = useRoute()
const { completed, isComplete, toggle, reset, storageError } = useProjectProgress(props.project)
const stages = computed(() => props.project.build.steps)
const stageOptions = computed(() => stages.value.map((stage, index) => ({ value: stage.id, label: `${index + 1}. ${guideStageLabel(stage)}` })))
const projectPath = computed(() => projectUrl(world.value.manifest, props.project.id))
const selectedIndex = computed(() => {
  const requested = Array.isArray(route.query.stage) ? route.query.stage[0] : route.query.stage
  const index = stages.value.findIndex(stage => stage.id === requested)
  return index < 0 ? 0 : index
})
const activeStage = computed<GuideStep | null>(() => stages.value[selectedIndex.value] ?? null)
const previousStage = computed(() => stages.value[selectedIndex.value - 1])
const nextStage = computed(() => stages.value[selectedIndex.value + 1])
const stageArticle = useTemplateRef<HTMLElement>('stage-article')
async function goToStage(id: string) {
  if (!stages.value.some(stage => stage.id === id) || id === activeStage.value?.id) return
  await navigateTo({ path: route.path, query: { ...route.query, stage: id } })
  stageScroll.value?.focus({ preventScroll: true })
}
watch(selectedIndex, (index, previous) => {
  stageDirection.value = index >= previous ? 1 : -1
  void nextTick(() => stageList.value?.querySelector<HTMLElement>('[aria-current="step"]')?.scrollIntoView({ block: 'nearest', behavior: reducedMotion.value ? 'instant' : 'smooth' }))
})
function finishStageTransition() {
  stageArticle.value?.scrollIntoView({ block: 'start', behavior: 'instant' })
}
const levelMap = computed(() => new Map(props.project.levels.map(level => [level.id, level])))
const processNames = computed(() => new Map((props.project.production?.processes ?? []).map(process => [process.id, `${process.recipeName} (${process.machineName})`])))
const drawingMap = computed(() => new Map(props.project.drawings.map(drawing => [drawing.id, drawing])))
const stageLevels = computed(() => (activeStage.value?.levelIds ?? []).map(id => levelMap.value.get(id)).filter((level): level is Level => Boolean(level)))
const stageLevelIds = computed(() => new Set(activeStage.value?.levelIds ?? []))
const stagePlacements = computed(() => {
  const zones = props.project.zoneAtlas?.views.filter(zone => activeStage.value?.zoneIds?.includes(zone.id)) ?? []
  if (zones.length) {
    const ids = new Set(zones.flatMap(zone => zone.placementIds))
    return props.project.placements.filter(placement => ids.has(placement.id))
  }
  return props.project.placements.filter(placement => stageLevelIds.value.has(placement.levelId))
})
const stageDrawings = computed(() => (activeStage.value?.drawingIds ?? []).map(id => drawingMap.value.get(id)).filter((drawing): drawing is Drawing => Boolean(drawing)))
const stageZones = computed(() => (props.project.zoneAtlas?.views ?? []).filter(zone => activeStage.value?.zoneIds?.includes(zone.id)))
const commissioningChecks = computed(() => props.project.build.commissioning.map((text, index) => ({ id: `check-${String(index + 1).padStart(2, '0')}`, text })))
const doneStages = computed(() => stages.value.filter(stage => isComplete(stage.id)).length)
const doneChecks = computed(() => commissioningChecks.value.filter(check => isComplete(check.id)).length)
const placementColumns = computed(() => ['Машина', 'Группа', 'Этаж', blockGrid.value ? 'X, ф.' : 'X, м', blockGrid.value ? 'Y, ф.' : 'Y, м', blockGrid.value ? 'H, сл.' : 'Z, м', 'Частота'])
const placementRows = computed(() => stagePlacements.value.map(placement => [
  placement.id, processNames.value.get(placement.processId) ?? placement.processId,
  levelMap.value.get(placement.levelId)?.name ?? placement.levelId,
  horizontal(placement.x), horizontal(placement.y), vertical(placement.z), `${formatRate(placement.clock * 100, 6)}%`
]))
const resetDialog = useTemplateRef<HTMLDialogElement>('reset-dialog')
let resetTrigger: HTMLElement | null = null
function openResetConfirm(event: Event) {
  resetTrigger = event.currentTarget as HTMLElement
  resetDialog.value?.showModal()
}
function confirmReset() {
  reset()
  resetDialog.value?.close()
}
function onResetClose() {
  if (resetTrigger?.isConnected) resetTrigger.focus()
  else stageArticle.value?.focus({ preventScroll: true })
  resetTrigger = null
}
</script>

<template>
  <section class="build-guide" aria-label="План строительства">
    <div v-if="!stages.length" class="empty-state">В этом проекте пока нет этапов строительства.</div>
    <template v-else>
      <header class="guide-progress">
        <div><strong>План строительства</strong><span>{{ doneStages }} из {{ stages.length }} этапов отмечено</span></div>
        <progress :value="doneStages" :max="stages.length" aria-label="Отмеченные этапы" />
        <Button v-if="completed.length" variant="ghost" @click="openResetConfirm">Сбросить отметки</Button>
      </header>
      <p v-if="storageError" class="notice notice-warning" role="alert">{{ storageError }}</p>
      <div class="field guide-stage-select"><label for="build-stage-select">Этап строительства</label><TheSelect trigger-id="build-stage-select" :model-value="activeStage?.id || ''" :options="stageOptions" @update:model-value="goToStage(String($event))" /></div>
      <div class="guide-layout" :style="{ '--stage-direction': stageDirection }">
        <nav ref="stage-list" class="guide-index" aria-label="Этапы строительства" tabindex="0"><ol>
          <li v-for="(stage, index) in stages" :key="stage.id"><button type="button" class="step-link" :aria-current="stage.id === activeStage?.id ? 'step' : undefined" @click="goToStage(stage.id)"><span class="step-number" :class="{ 'step-complete': isComplete(stage.id) }">{{ isComplete(stage.id) ? '✓' : index + 1 }}</span><span>{{ guideStageLabel(stage) }}</span><span v-if="isComplete(stage.id)" class="sr-only">Выполнен</span></button></li>
        </ol></nav>
        <article v-if="activeStage" ref="stage-article" class="guide-step" :aria-labelledby="`stage-${activeStage.id}-title`">
          <div ref="stage-scroll" class="stage-scroll" tabindex="0" :aria-labelledby="`stage-${activeStage.id}-title`">
          <Transition name="stage" mode="out-in" @after-enter="finishStageTransition">
          <div :key="activeStage.id" class="stage-content">
          <header class="stage-heading"><div><p class="fine">Этап {{ selectedIndex + 1 }} / {{ stages.length }}</p><h2 :id="`stage-${activeStage.id}-title`">{{ guideStageLabel(activeStage) }}</h2></div><label class="stage-completion check-row"><input :checked="isComplete(activeStage.id)" type="checkbox" @change="toggle(activeStage.id)"><span>{{ isComplete(activeStage.id) ? 'Этап отмечен' : 'Отметить этап' }}</span></label></header>
          <div class="stage-work">
            <section v-if="activeStage.actions.length" aria-labelledby="stage-actions-heading"><h3 id="stage-actions-heading">Что сделать</h3><ol class="construction-actions"><li v-for="(action, index) in activeStage.actions" :key="index">{{ constructionText(action) }}</li></ol></section>
            <p v-else-if="activeStage.body">{{ constructionText(activeStage.body) }}</p>
            <aside v-if="stageDrawings.length" class="stage-reference" aria-label="Чертежи этапа">
              <NuxtLink :to="{ path: `${projectPath}/drawings`, query: { drawing: stageDrawings[0]!.id } }" class="stage-drawing-preview"><img :src="stageDrawings[0]!.png || stageDrawings[0]!.svg" :alt="stageDrawings[0]!.label" width="1280" height="820"></NuxtLink>
              <h3>Под рукой</h3><ul class="stage-drawing-links"><li v-for="drawing in stageDrawings" :key="drawing.id"><NuxtLink class="text-link" :to="{ path: `${projectPath}/drawings`, query: { drawing: drawing.id } }">{{ drawing.label }}</NuxtLink></li></ul>
              <NuxtLink class="text-link" :to="`${projectPath}/parts`">Материалы проекта</NuxtLink>
            </aside>
          </div>
          <div class="stage-support">
            <details v-if="activeStage.prerequisites.length" :key="`${activeStage.id}-prerequisites`" class="reference-disclosure"><summary>До этого этапа</summary><ul><li v-for="id in activeStage.prerequisites" :key="id">{{ constructionText(stages.find(stage => stage.id === id)?.title ?? id) }}</li></ul></details>
            <details v-if="activeStage.materials.length" :key="`${activeStage.id}-materials`" class="reference-disclosure"><summary>Детали и количества для этапа</summary><ul><li v-for="text in activeStage.materials" :key="text">{{ constructionText(text) }}</li></ul><NuxtLink class="text-link" :to="`${projectPath}/parts`">Вся спецификация</NuxtLink></details>
            <details v-if="activeStage.checks.length" :key="`${activeStage.id}-checks`" class="reference-disclosure"><summary>Как проверить результат</summary><ul><li v-for="text in activeStage.checks" :key="text">{{ constructionText(text) }}</li></ul><p class="fine">Ожидаемые результаты плана. Их ещё нужно проверить в игре.</p></details>
            <details v-if="stageLevels.length || stagePlacements.length" :key="`${activeStage.id}-placements`" class="reference-disclosure"><summary>Этажи и координаты машин · {{ stagePlacements.length }}</summary><div v-for="level in stageLevels" :key="level.id" class="stage-level"><h3>{{ level.id }} · {{ level.name }}</h3><p>Пол: {{ floorHeight(level.z) }}. {{ constructionText(level.purpose) }}</p></div><DataTable :columns="placementColumns" :rows="placementRows" :caption="`Размещение: ${guideStageLabel(activeStage)}`" /></details>
            <details v-if="stageZones.length" :key="`${activeStage.id}-zones`" class="reference-disclosure"><summary>Иллюстрации зон · {{ stageZones.length }}</summary><p class="fine">Приближённые AI-виды, не игровые скриншоты. Размеры бери из чертежей.</p><ul><li v-for="zone in stageZones" :key="zone.id"><NuxtLink class="text-link" :to="{ path: `${projectPath}/drawings`, query: { zone: zone.id } }">{{ zone.id }} · {{ zone.title }}</NuxtLink></li></ul></details>
            <details v-if="activeStage.body && activeStage.body !== activeStage.actions.join(' ')" :key="`${activeStage.id}-body`" class="reference-disclosure"><summary>Описание из плана</summary><p>{{ constructionText(activeStage.body) }}</p></details>
          </div>
          </div>
          </Transition>
          </div>
          <footer class="guide-actions"><Button variant="outline" :disabled="!previousStage" @click="previousStage && goToStage(previousStage.id)">Предыдущий этап</Button><Button :disabled="!nextStage" @click="nextStage && goToStage(nextStage.id)">Следующий этап</Button></footer>
        </article>
      </div>
      <details v-if="commissioningChecks.length" class="reference-disclosure commissioning-checklist"><summary>Проверка готового завода <span class="fine">{{ doneChecks }} / {{ commissioningChecks.length }}</span></summary><p class="fine">Личный чек-лист для проверки в игре. Отметки не снимают ограничения площадки.</p><ul class="check-list"><li v-for="check in commissioningChecks" :key="check.id"><label class="check-row"><input :checked="isComplete(check.id)" type="checkbox" @change="toggle(check.id)"><span>{{ constructionText(check.text) }}</span></label></li></ul></details>
      <details v-if="project.build.notes.length" class="reference-disclosure"><summary>Примечания к сборке</summary><ul><li v-for="note in project.build.notes" :key="note">{{ constructionText(note) }}</li></ul></details>
    </template>
    <dialog ref="reset-dialog" class="atlas-dialog confirm-dialog" aria-labelledby="reset-dialog-heading" @close="onResetClose"><h2 id="reset-dialog-heading">Сбросить отметки стройки?</h2><p>Отметки всех этапов и проверок этой версии проекта будут удалены из браузера. План и сохранение игры не изменятся.</p><div class="button-row"><Button @click="confirmReset">Сбросить отметки</Button><Button variant="outline" @click="resetDialog?.close()">Отмена</Button></div></dialog>
  </section>
</template>
