<script setup lang="ts">
import type { ProjectKind } from '~~/shared/types/project'
import { useDebounceFn } from '@vueuse/core'
import { Plus, ArrowUpRight, FolderOpen } from '@lucide/vue'

const router = useRouter()
const { projects, saves } = useProjectCatalogue()
const catalogue = computed(() => projects.data.value?.projects || [])
const saveList = computed(() => saves.data.value?.saves || [])
const pending = computed(() => projects.status.value === 'pending' || saves.status.value === 'pending')
const failed = computed(() => projects.error.value || saves.error.value)
const queryValue = (key: string) => typeof router.currentRoute.value.query[key] === 'string' ? router.currentRoute.value.query[key] as string : ''
const search = ref(queryValue('q'))
let searchWrite: string | undefined
function setFilter(key: string, value: string, replace = false) {
  return navigateTo({ path: '/', query: { ...router.currentRoute.value.query, q: search.value || undefined, [key]: value && value !== 'all' ? value : undefined } }, { replace })
}
const commitSearchQuery = useDebounceFn(async () => {
  const value = search.value
  searchWrite = value
  try {
    await setFilter('q', value, true)
  } finally {
    if (searchWrite === value) searchWrite = undefined
  }
}, 200)
function updateSearch(value: string | number) {
  search.value = String(value)
  void commitSearchQuery()
}
watch(() => router.currentRoute.value.fullPath, () => {
  const value = queryValue('q')
  if (value !== searchWrite) search.value = value
})
const saveFilter = computed({ get: () => queryValue('save') || 'all', set: value => { void setFilter('save', value) } })
const kindFilter = computed({ get: () => queryValue('kind') || 'all', set: value => { void setFilter('kind', value) } })
const saveOptions = computed(() => [{ value: 'all', label: 'Все сейвы' }, ...saveList.value.map(save => ({ value: save.id, label: `${save.name} / ${save.sessionName}` }))])
const kindOptions = [{ value: 'all', label: 'Все проекты' }, ...Object.entries(projectKindLabels).map(([value, label]) => ({ value, label }))]
const visible = computed(() => {
  const needle = search.value.trim().toLocaleLowerCase('ru')
  return catalogue.value.filter(project =>
    (saveFilter.value === 'all' || project.saveId === saveFilter.value) &&
    (kindFilter.value === 'all' || project.kind === kindFilter.value) &&
    (!needle || [project.title, project.subtitle, project.target?.label, project.id].join(' ').toLocaleLowerCase('ru').includes(needle))
  )
})
const addDialog = useTemplateRef<HTMLDialogElement>('add-dialog')
const copied = ref(false)
const copyError = ref('')
const example = '/new-factory modular engine 100 per min --save cachys'
async function copyCommand() {
  try { await navigator.clipboard.writeText(example); copied.value = true; copyError.value = '' }
  catch { copyError.value = 'Копирование недоступно. Выдели и скопируй команду ниже.' }
}
async function refreshCatalogue() { await Promise.all([projects.refresh(), saves.refresh()]) }
useSeoMeta({ title: 'Проекты / Заводской атлас' })
</script>

<template>
  <main id="main" class="catalogue page-width">
    <div class="catalogue-heading">
      <div><h1>Мои проекты</h1><p class="lead catalogue-intro">Твои заводы, от первого фундамента до выпуска.</p></div>
      <Button variant="outline" class="add-project" @click="addDialog?.showModal()"><Plus :size="17" aria-hidden="true" />Новый проект</Button>
    </div>
    <form class="catalogue-filters" role="search" @submit.prevent>
      <label class="field" for="project-search"><span>Найти проект</span><Input id="project-search" :model-value="search" variant="filled" type="search" placeholder="Название или изделие" @update:model-value="updateSearch" /></label>
      <div class="field"><label for="save-filter">Сейв</label><TheSelect trigger-id="save-filter" :model-value="saveFilter" :options="saveOptions" @update:model-value="saveFilter = String($event)" /></div>
      <div class="field"><label for="kind-filter">Тип проекта</label><TheSelect trigger-id="kind-filter" :model-value="kindFilter" :options="kindOptions" @update:model-value="kindFilter = String($event)" /></div>
    </form>
    <p v-if="pending" class="empty-state" role="status">Загружаем каталог проектов и сейвов.</p>
    <div v-else-if="failed" class="notice notice-warning" role="alert"><h2>Каталог не загрузился</h2><p>Не удалось прочитать опубликованные данные. Проверь подключение к локальному сайту или повтори загрузку.</p><Button variant="outline" @click="refreshCatalogue">Загрузить каталог ещё раз</Button></div>
    <template v-else>
      <div class="catalogue-list-heading"><h2><FolderOpen :size="17" aria-hidden="true" />Планы строительства</h2><span class="muted" aria-live="polite">{{ visible.length }} из {{ catalogue.length }}</span></div>
      <div v-if="!visible.length" class="empty-state"><h3>{{ catalogue.length ? 'Проектов не нашлось' : 'Пока нет проектов' }}</h3><p>{{ catalogue.length ? 'Попробуй другое название или сбрось фильтры.' : 'Создай план через OMP. После публикации он появится здесь.' }}</p><Button v-if="catalogue.length" as-child variant="outline"><NuxtLink to="/" @click="search = ''">Сбросить фильтры</NuxtLink></Button><Button v-else @click="addDialog?.showModal()">Как добавить проект</Button></div>
      <div v-else class="project-list">
        <article v-for="project in visible" :key="`${project.saveId}/${project.id}`" class="project-card">
          <div class="project-card-image"><NuxtLink :to="projectUrl(project.saveId, project.id)" tabindex="-1" aria-hidden="true"><img v-if="project.preview" :src="project.preview.src" :alt="project.preview.alt" width="1280" height="900"><span v-else class="project-no-preview">{{ projectKindLabels[project.kind as ProjectKind] }}</span></NuxtLink><span v-if="project.preview?.kind === 'concept'" :id="`concept-${project.saveId}-${project.id}`" class="cover-caption">AI-концепт · не игровой скриншот</span></div>
          <div class="project-card-body">
            <div class="project-card-meta"><span>Мир {{ project.saveId }}</span><span class="tag">{{ projectStatusLabels[project.status] }}</span></div>
            <h3><NuxtLink :to="projectUrl(project.saveId, project.id)" :aria-describedby="project.preview?.kind === 'concept' ? `concept-${project.saveId}-${project.id}` : undefined">{{ project.title }}</NuxtLink></h3><p class="muted">{{ project.subtitle }}</p>
            <div v-if="project.target" class="project-output"><strong>{{ formatRate(project.target.rate) }}</strong><span>шт/мин<br>расчётный выпуск</span></div>
            <p class="fine">{{ project.drawingCount }} чертежей<span v-if="project.zoneCount"> · {{ project.zoneCount }} вида зон</span></p>
            <div class="button-row project-open"><Button as-child><NuxtLink :to="projectUrl(project.saveId, project.id, 'build')">К этапам стройки<ArrowUpRight :size="18" aria-hidden="true" /></NuxtLink></Button><NuxtLink class="text-link" :to="projectUrl(project.saveId, project.id)">Обзор проекта</NuxtLink></div>
          </div>
        </article>
      </div>
      <p class="catalogue-footnote fine">Каждый проект относится к своему миру. Отметки этапов сохраняются в этом браузере.</p>
    </template>
    <dialog ref="add-dialog" class="atlas-dialog" aria-labelledby="add-title" @close="copied = false">
      <div class="dialog-heading"><h2 id="add-title">Добавить проект</h2><Button variant="outline" aria-label="Закрыть инструкцию создания" @click="addDialog?.close()">Закрыть</Button></div>
      <p>План создаётся в OMP: открой этот репозиторий и введи команду с изделием, выпуском и миром. Перед публикацией нужно проверить сейв, моды и снабжение.</p>
      <code class="command-example">{{ example }}</code>
      <div class="button-row"><Button class="copy-command" :class="{ copied }" @click="copyCommand"><Transition name="feedback" mode="out-in"><span :key="copied ? 'copied' : 'copy'">{{ copied ? 'Команда скопирована' : 'Скопировать команду' }}</span></Transition></Button><span class="sr-only" role="status">{{ copied ? 'Команда скопирована' : '' }}</span></div>
      <p v-if="copyError" role="status">{{ copyError }}</p>
      <p class="fine">Сайт показывает опубликованные планы. Эта кнопка не запускает генерацию и не меняет сохранение.</p>
    </dialog>
  </main>
</template>
