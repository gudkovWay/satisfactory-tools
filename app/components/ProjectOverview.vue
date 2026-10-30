<script setup lang="ts">
import { ArrowUpRight, ListChecks, Layers } from '@lucide/vue'
import type { ProjectDocument } from '~~/shared/types/project'
const props = defineProps<{ project: ProjectDocument }>()
const world = useWorld()
const { isComplete } = useProjectProgress(props.project)
const done = computed(() => props.project.build.steps.filter(step => isComplete(step.id)).length)
const next = computed(() => props.project.build.steps.find(step => !isComplete(step.id)) ?? props.project.build.steps[0])
</script>

<template>
  <div class="stack overview">
    <div class="overview-workbench">
      <figure v-if="project.preview" class="overview-preview"><img :src="project.preview.src" :alt="project.preview.alt" width="1280" height="900"><figcaption>{{ project.preview.kind === 'concept' ? 'AI-концепт завода, не игровой скриншот.' : 'Схема проекта. Размеры смотри в чертежах.' }}</figcaption></figure>
      <section class="overview-next">
        <div class="next-heading"><ListChecks :size="20" aria-hidden="true" /><h2>{{ done === project.build.steps.length && done ? 'Этапы отмечены' : 'Продолжить проект' }}</h2></div>
        <p v-if="next" class="next-stage-name">{{ guideStageLabel(next) }}</p>
        <p class="muted next-description">{{ done === project.build.steps.length && done ? 'Вернись к любому этапу или проверь готовый завод.' : 'Чертежи, детали и порядок действий для следующего этапа.' }}</p>
        <div class="next-progress"><span>Личные отметки</span><strong>{{ done }} <span>/ {{ project.build.steps.length }}</span></strong></div><progress :value="done" :max="project.build.steps.length || 1" aria-label="Личный прогресс строительства" />
        <Button v-if="next" as-child><NuxtLink :to="{ path: projectUrl(world.manifest, project.id, 'build'), query: { stage: next.id } }">{{ done ? 'Вернуться к этапам' : 'Открыть первый этап' }}<ArrowUpRight :size="18" aria-hidden="true" /></NuxtLink></Button>
        <NuxtLink class="next-secondary" :to="projectUrl(world.manifest, project.id, 'drawings')"><Layers :size="17" aria-hidden="true" />Этажи и чертежи</NuxtLink>
        <p class="fine">Отметки хранятся в этом браузере и не подтверждают готовность в игре.</p>
      </section>
    </div>
    <dl class="project-facts"><div v-if="project.target"><dt>Расчётный выпуск</dt><dd>{{ formatRate(project.target.rate) }} <span>{{ project.target.unit }}</span></dd></div><div><dt>Машины по плану</dt><dd>{{ project.placements.length }}</dd></div><div><dt>Уровни</dt><dd>{{ project.levels.length }}</dd></div><div><dt>Размерные чертежи</dt><dd>{{ project.drawings.length }}</dd></div></dl>
    <FloorPreview :project="project" />
    <section><div class="section-heading"><h2>Подготовка к стройке</h2></div><div class="work-links">
      <NuxtLink :to="projectUrl(world.manifest, project.id, 'site')"><strong>Где строить<ArrowUpRight :size="18" aria-hidden="true" /></strong><span>Площадка, сырьё и действующая инфраструктура</span></NuxtLink>
      <NuxtLink :to="projectUrl(world.manifest, project.id, 'balance')"><strong>Что производить<ArrowUpRight :size="18" aria-hidden="true" /></strong><span>Рецепты, частоты и потоки по группам</span></NuxtLink>
      <NuxtLink :to="projectUrl(world.manifest, project.id, 'parts')"><strong>Что взять с собой<ArrowUpRight :size="18" aria-hidden="true" /></strong><span>Детали, количества и названия в меню</span></NuxtLink>
      <NuxtLink :to="projectUrl(world.manifest, project.id, 'infrastructure')"><strong>Как соединить<ArrowUpRight :size="18" aria-hidden="true" /></strong><span>Ленты, трубы, питание и вывоз</span></NuxtLink>
    </div></section>
    <details class="reference-disclosure"><summary>Почему завод устроен так</summary><div class="decision-list"><article v-for="decision in project.overview.decisions" :key="decision.choice"><h3>{{ constructionText(decision.choice) }}</h3><p>{{ constructionText(decision.reason) }}</p><p class="fine">Альтернатива: {{ constructionText(decision.instead) }}</p><p class="muted">Компромисс: {{ constructionText(decision.tradeoff) }}</p></article></div></details>
    <details class="reference-disclosure"><summary>Полное описание и исходные допущения</summary><p v-for="paragraph in project.overview.paragraphs" :key="paragraph">{{ constructionText(paragraph) }}</p></details>
    <details v-if="project.overview.concept" class="reference-disclosure"><summary>Визуальный концепт интерьера</summary><figure class="concept-figure"><img :src="project.overview.concept.src" :alt="project.overview.concept.alt" loading="lazy" width="1672" height="940"><figcaption>Приближённая AI-иллюстрация. {{ project.overview.concept.caption }}</figcaption></figure></details>
    <section v-if="project.dependencies.length"><h2>Связанные проекты</h2><ul><li v-for="dependency in project.dependencies" :key="dependency.projectId"><NuxtLink class="text-link" :to="projectUrl(world.manifest, dependency.projectId)">{{ dependency.role }}</NuxtLink></li></ul></section>
  </div>
</template>
