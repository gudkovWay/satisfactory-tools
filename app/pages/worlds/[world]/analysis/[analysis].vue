<script setup lang="ts">
import type { WorldAnalysis } from '~~/shared/types/world'
definePageMeta({ key: route => route.path })

type AnalysisTopic = {
  id: string
  title: string
  sections: number[]
  tables: number[]
  media: number[]
  states?: boolean
  data?: boolean
}

const route = useRoute()
const world = useWorld()
const analysis = world.value.analyses.find(item => item.id === route.params.analysis)
if (!analysis) throw createError({ statusCode: 404, statusMessage: 'Анализ не найден в этом мире' })
const base = computed(() => worldUrl(world.value.manifest.id))
const descriptor = world.value.manifest.analyses.find(item => item.id === analysis.id)!
useSeoMeta({ title: () => `${analysis.title} / ${world.value.manifest.title}` })
const extractorOptions = (analysis.extractors ?? []).map(item => ({ value: String(item.id), label: `${atlasLabel(item.label)} · тир ${item.tier}` }))
const miner = ref(extractorOptions[0]?.value || '')
const states = computed(() => analysis.states?.filter(state => state.miner === Number(miner.value)) ?? [])
const analysisIndex = world.value.manifest.analyses.findIndex(item => item.id === analysis.id)
const nextAnalysis = world.value.manifest.analyses[analysisIndex + 1]
const panelScroll = useTemplateRef<HTMLElement>('panelScroll')
const architecture = analysis.id === 'architecture'

const sectionTitles: Record<string, string> = {
  'Bootstrap и Logistics прежде масштаба': 'Подготовка и логистика',
  'Горизонт запаса вместо бесконтрольного максимума': 'Пополнение запаса',
  'Расширять, а не обязательно сносить': 'Расширение',
  'Предел доказательств площадки': 'Проверка площадок',
  'Публичная проверка стартовой сметы, не игровой отчёт': 'Энергия, топливо и порядок пуска',
  'Снимок и граница публикации': 'Сохранение и объём плана',
  'Установка, исходник и работа игры различаются': 'Моды и проверка в игре',
  'Почему жидкостный расчёт пока не является эффективным профилем игры': 'Ограничения жидкостного расчёта',
  'EasyAlt: актуальный плагин и старый каталог различаются': 'Рецепты EasyAlt',
  '250% и экономия от осколков требуют отдельных условий': 'Разгон и силовые осколки',
  'Материковые кандидаты из известных записей сейва': 'Кандидаты на материке',
  'Граница по сырью, а не независимые максимумы': 'Общий баланс сырья',
  'Какие альтернативы искать, а не считать уже открытыми': 'Поиск альтернативных рецептов'
}
const architectureTableTitles = [
  'Пополнение запаса · сценарии не суммируются',
  'Редакции проектов',
  'Стартовые постройки · без полного фасада',
  'Материалы · Logistics учтён один раз',
  'Остатки после операций · приход по фактическому приёму',
  'Выпуск за 8 установившихся минут · не срок холодного запуска'
]
const tableTitles: Record<string, string[]> = {
  seed: ['Факты о сохранении', 'Ноды острова · прямая дистанция, не трасса', 'Сохранённые параметры модов', 'Известные ноды · номинальная оценка', 'Железо · кандидаты на материке', 'Уголь · кандидаты на материке', 'Медь · кандидаты на материке'],
  states: ['Электросеть · прочая нагрузка учтена один раз', 'Добыча, потребление и резерв'],
  progression: ['Альтернативные рецепты · условия и сырьё', 'Один порт · ограничения при профиле WB']
}

function sectionTitle(index: number) {
  const title = analysis!.sections[index]?.title ?? ''
  return sectionTitles[title] ?? atlasLabel(title)
}

function tableTitle(index: number) {
  return (architecture ? architectureTableTitles : tableTitles[analysis!.id])?.[index]
    ?? atlasLabel(analysis!.tables?.[index]?.caption ?? 'Таблица')
}

function mediaTitle(index: number) {
  const asset = analysis!.media?.[index]
  if (architecture && index === 0) return 'Склад и ячейки хранения'
  if (architecture && index === 1) return 'Объёмный план кампуса'
  return atlasLabel(asset?.alt ?? 'Иллюстрация')
}

const topics = computed<AnalysisTopic[]>(() => {
  const items: AnalysisTopic[] = architecture
    ? [
        { id: 'overview', title: 'Обзор', sections: [0, 3, 4], tables: [], media: [0, 1] },
        { id: 'supply', title: 'Снабжение', sections: [2], tables: [0], media: [] },
        { id: 'budget', title: 'Стартовая смета', sections: [1, 5], tables: [2, 3, 4, 5], media: [] }
      ]
    : analysis.sections.map((_, index) => ({
        id: `section-${index + 1}`, title: sectionTitle(index), sections: [index], tables: [], media: []
      }))

  for (const topic of items) {
    topic.sections = topic.sections.filter(index => Boolean(analysis.sections[index]))
    topic.tables = topic.tables.filter(index => Boolean(analysis.tables?.[index]))
    topic.media = topic.media.filter(index => Boolean(analysis.media?.[index]))
  }
  for (let index = 0; index < analysis.sections.length; index++) {
    if (!items.some(topic => topic.sections.includes(index))) {
      items.push({ id: `section-${index + 1}`, title: sectionTitle(index), sections: [index], tables: [], media: [] })
    }
  }
  if (analysis.states?.length) items.push({ id: 'extraction', title: 'Режимы добычи', sections: [], tables: [], media: [], states: true })
  for (let index = 0; index < (analysis.tables?.length ?? 0); index++) {
    if (architecture && index === 1) continue
    if (!items.some(topic => topic.tables.includes(index))) {
      items.push({ id: `table-${index + 1}`, title: tableTitle(index), sections: [], tables: [index], media: [] })
    }
  }
  for (let index = 0; index < (analysis.media?.length ?? 0); index++) {
    if (!items.some(topic => topic.media.includes(index))) {
      items.push({ id: `media-${index + 1}`, title: mediaTitle(index), sections: [], tables: [], media: [index] })
    }
  }
  items.push({ id: 'data', title: 'Данные и источники', sections: [], tables: architecture && analysis.tables?.[1] ? [1] : [], media: [], data: true })
  return items.filter(topic => topic.data || topic.states || topic.sections.length || topic.tables.length || topic.media.length)
})
const selectedTopic = computed(() => {
  const requested = Array.isArray(route.query.topic) ? route.query.topic[0] : route.query.topic
  const matching = topics.value.find(topic => topic.id === requested)
  if (matching) return matching
  if (!requested && route.hash.startsWith('#analysis-section-')) {
    const index = Number(route.hash.slice('#analysis-section-'.length))
    return topics.value.find(topic => topic.sections.includes(index)) ?? topics.value[0]!
  }
  if (!requested && route.hash === '#analysis-sources') return topics.value.find(topic => topic.data)!
  return topics.value[0]!
})
const visibleSections = computed(() => selectedTopic.value.sections.map(index => ({ index, section: analysis.sections[index]! })))
const visibleTables = computed(() => selectedTopic.value.tables.map(index => ({ index, table: analysis.tables![index]! })))
const visibleMedia = computed(() => selectedTopic.value.media.map(index => ({ index, asset: analysis.media![index]! })))
const sourceParagraphs = computed(() => analysis.sections.flatMap(section => section.paragraphs.filter(isSourceParagraph)))

function isSourceParagraph(paragraph: string) {
  return /SHA-?256/i.test(paragraph)
}

function chooseTopic(id: string) {
  if (id === selectedTopic.value.id || !topics.value.some(topic => topic.id === id)) return
  void navigateTo({ path: route.path, query: { ...route.query, topic: id }, hash: route.hash })
}

function chooseMobileTopic(event: Event) {
  chooseTopic((event.target as HTMLSelectElement).value)
}


watch(() => selectedTopic.value.id, () => {
  if (panelScroll.value) panelScroll.value.scrollTop = 0
})

function displayRows(table: NonNullable<WorldAnalysis['tables']>[number]) {
  return table.rows.map(row => row.map(cell => atlasLabel(cell)))
}
</script>

<template>
  <main id="main" class="page-width world-page analysis-page">
    <header class="world-heading analysis-heading">
      <div>
        <h1>{{ analysis.title.replace(/^\d+\s*·\s*/, '') }}</h1>
        <p class="world-intro">{{ architecture ? 'Как связать домашние заводы, пополнять склад и расширять производство.' : constructionText(analysis.summary) }}</p>
      </div>
      <a class="text-link analysis-download" :href="`${base}/${descriptor.path}`" download>Скачать JSON</a>
    </header>
    <nav class="analysis-step-nav" aria-label="Документы анализа">
      <NuxtLink v-for="item in world.manifest.analyses" :key="item.id" :to="`${base}/analysis/${item.id}`" :aria-current="item.id === analysis.id ? 'page' : undefined">{{ item.title.replace(/^\d+\s*·\s*/, '') }}</NuxtLink>
    </nav>

    <div class="analysis-workspace">
      <nav class="analysis-topic-rail" aria-label="Темы анализа">
        <h2>Содержание</h2>
        <button
          v-for="topic in topics"
          :key="topic.id"
          type="button"
          :aria-current="topic.id === selectedTopic.id ? 'true' : undefined"
          aria-controls="analysis-panel"
          @click="chooseTopic(topic.id)"
        >{{ topic.title }}</button>
      </nav>
      <div class="analysis-topic-mobile">
        <label for="analysis-topic">Тема анализа</label>
        <select id="analysis-topic" :value="selectedTopic.id" aria-controls="analysis-panel" @change="chooseMobileTopic">
          <option v-for="topic in topics" :key="topic.id" :value="topic.id">{{ topic.title }}</option>
        </select>
      </div>

      <section id="analysis-panel" class="analysis-panel" aria-labelledby="analysis-topic-heading">
        <header class="analysis-panel-heading">
          <h2 id="analysis-topic-heading" aria-live="polite">{{ selectedTopic.title }}</h2>
          <span v-if="architecture && selectedTopic.id === 'budget'" class="fine">Постройки, материалы и запуск</span>
        </header>
        <div ref="panelScroll" class="analysis-panel-scroll" tabindex="0" role="region" :aria-label="selectedTopic.title">
          <div v-if="visibleTables.length" class="analysis-tables">
            <template v-for="{ index, table } in visibleTables" :key="index">
              <details v-if="visibleTables.length > 1 || selectedTopic.data" class="analysis-table-detail">
                <summary>{{ tableTitle(index) }} <span>{{ table.rows.length }} строк</span></summary>
                <p v-if="!selectedTopic.data" class="fine analysis-table-qualification">{{ constructionText(table.caption) }}</p>
                <DataTable :columns="table.columns.map(column => atlasLabel(column))" :rows="displayRows(table)" :caption="tableTitle(index)" />
              </details>
              <section v-else class="analysis-table-single">
                <p class="fine analysis-table-qualification">{{ constructionText(table.caption) }}</p>
                <DataTable :columns="table.columns.map(column => atlasLabel(column))" :rows="displayRows(table)" :caption="tableTitle(index)" />
              </section>
            </template>
          </div>
          <article v-for="{ index, section } in visibleSections" :id="`analysis-section-${index}`" :key="index" class="analysis-prose">
            <h3>{{ sectionTitle(index) }}</h3>
            <p v-for="(paragraph, paragraphIndex) in analysisParagraphs(analysis.id, index, section.paragraphs, descriptor.sha256).filter(text => !isSourceParagraph(text))" :key="paragraphIndex">{{ constructionText(atlasLabel(paragraph)) }}</p>
          </article>

          <section v-if="selectedTopic.states" class="analysis-extraction">
            <p class="analysis-notice">Номинальный расчёт, не измерение в игре. Порты делят общий выпуск, а не умножают его.</p>
            <div class="field state-selector">
              <label for="miner-state">Класс экстрактора</label>
              <TheSelect trigger-id="miner-state" :model-value="miner" :options="extractorOptions" @update:model-value="miner = String($event)" />
            </div>
            <DataTable caption="Непрерывная работа · общий выпуск на все порты" :columns="['Чистота', 'Частота', 'Осколки', 'Руда / мин', 'Порты', 'Вывоз / мин', 'МВт']" :rows="states.map(state => [atlasLabel(state.purity), `${state.clock * 100}%`, String(state.shards), formatRate(state.raw), String(state.ports), `${state.lanes} × ${formatRate(state.perLane)} ≤ ${state.belt}`, formatRate(state.powerMW)])" />
            <p v-if="!states.length" class="empty-state">Для этого экстрактора нет режимов в текущем анализе.</p>
          </section>

          <div v-if="visibleMedia.length" class="analysis-media">
            <figure v-for="{ index, asset } in visibleMedia" :key="asset.src">
              <img :src="asset.src" :alt="asset.alt" width="1600" height="1000" loading="lazy">
              <figcaption>
                <strong>{{ mediaTitle(index) }}</strong>
                <a class="text-link" :href="asset.src" download>Скачать изображение</a>
              </figcaption>
            </figure>
          </div>


          <template v-if="selectedTopic.data">
            <section class="analysis-data-section">
              <h3>Исходный анализ</h3>
              <a class="text-link" :href="`${base}/${descriptor.path}`" download>Скачать анализ JSON</a>
              <p class="fine">Сохранение: {{ world.record.saveId }}. После изменения сейва или профиля мира зависимые расчёты нужно пересмотреть. Расчёт не подтверждает работу в игре.</p>
              <ul v-if="analysis.sources.length" class="analysis-source-list">
                <li v-for="source in analysis.sources" :key="source.url"><a class="text-link" :href="source.url" target="_blank" rel="noopener">{{ constructionText(source.label) }}</a></li>
              </ul>
            </section>
            <details class="analysis-data-detail">
              <summary>Сохранение и контрольные суммы</summary>
              <dl class="analysis-identities">
                <dt>Сейв</dt><dd>{{ world.record.saveId }}</dd>
                <dt>SHA-256 сейва</dt><dd><code>{{ world.manifest.saveSha256 }}</code></dd>
                <dt>SHA-256 анализа</dt><dd><code>{{ descriptor.sha256 }}</code></dd>
                <template v-if="analysis.sourceSha256"><dt>SHA-256 исходных данных</dt><dd><code>{{ analysis.sourceSha256 }}</code></dd></template>
              </dl>
              <p v-for="paragraph in sourceParagraphs" :key="paragraph" class="fine">{{ paragraph }}</p>
            </details>
            <details v-if="analysis.sections.length" class="analysis-data-detail">
              <summary>Исходный текст анализа</summary>
              <article v-for="section in analysis.sections" :key="section.title"><h4>{{ section.title }}</h4><p v-for="paragraph in section.paragraphs" :key="paragraph">{{ paragraph }}</p></article>
            </details>
            <details v-if="analysis.tables?.length" class="analysis-data-detail">
              <summary>Полные подписи таблиц</summary>
              <dl class="analysis-caption-list"><template v-for="(table, index) in analysis.tables" :key="index"><dt>{{ tableTitle(index) }}</dt><dd>{{ table.caption }}</dd></template></dl>
            </details>
            <details v-if="analysis.media?.length" class="analysis-data-detail">
              <summary>Иллюстрации и происхождение</summary>
              <div v-for="(asset, index) in analysis.media" :key="asset.src" class="analysis-asset-source">
                <h4>{{ mediaTitle(index) }}</h4>
                <p>{{ asset.caption }}</p>
                <a class="text-link" :href="asset.src" download>Скачать изображение</a>
              </div>
            </details>
          </template>
        </div>
      </section>
    </div>

    <nav class="analysis-next" aria-label="Продолжить после анализа">
      <NuxtLink v-if="nextAnalysis" :to="`${base}/analysis/${nextAnalysis.id}`"><span>Следующий анализ</span><strong>{{ nextAnalysis.title.replace(/^\d+\s*·\s*/, '') }}</strong></NuxtLink>
      <NuxtLink :to="`${base}#route`"><span>Перейти к практике</span><strong>Порядок строительства</strong></NuxtLink>
    </nav>
  </main>
</template>

<style scoped>
.analysis-page { min-width: 0; }
.analysis-heading { display: flex; flex-wrap: wrap; align-items: start; justify-content: space-between; gap: .75rem 1.5rem; margin-bottom: 1.25rem; }
.analysis-heading > div { min-width: 0; flex: 1 1 28rem; }
.analysis-heading h1 { margin-bottom: .65rem; font-size: clamp(1.5rem, 2.5vw, 2rem); line-height: 1.2; max-width: none; }
.analysis-heading .world-intro { margin-bottom: 0; font-size: 1rem; }
.analysis-download { flex: none; font-size: .8125rem; }
.analysis-step-nav { max-width: 100%; margin-bottom: 1.25rem; }
.analysis-workspace { display: grid; gap: 1rem; min-width: 0; margin-bottom: 1.5rem; }
.analysis-topic-rail { display: none; }
.analysis-topic-mobile { display: grid; gap: .4rem; min-width: 0; }
.analysis-topic-mobile label { font-size: .8125rem; font-weight: 550; }
.analysis-topic-mobile select { width: 100%; min-width: 0; min-height: 44px; padding: .65rem .75rem; border: 1px solid var(--control-border); border-radius: 6px; color: var(--ink); background: var(--surface); font: inherit; font-size: .875rem; }
.analysis-panel { display: flex; flex-direction: column; min-width: 0; height: clamp(26rem, 68dvh, 52rem); border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }
.analysis-panel-heading { display: flex; flex-wrap: wrap; align-items: baseline; gap: .35rem 1rem; flex: none; padding: 1rem; border-bottom: 1px solid var(--line); }
.analysis-panel-heading h2 { margin: 0; font-size: 1.125rem; }
.analysis-panel-scroll { flex: 1; min-height: 0; min-width: 0; padding: 1rem; overflow: auto; overscroll-behavior: contain; scrollbar-gutter: stable; }
.analysis-prose + .analysis-prose { margin-top: 1.75rem; }
.analysis-prose h3 { max-width: 72ch; margin-bottom: .65rem; font-size: 1rem; }
.analysis-prose p { max-width: 80ch; font-size: .9375rem; line-height: 1.75; }
.analysis-prose p:last-child { margin-bottom: 0; }
.analysis-notice { padding: .8rem 1rem; border-radius: 6px; background: var(--warning-soft); color: var(--warning-ink); font-size: .875rem; }
.state-selector { margin-block: 1rem; }
.analysis-media { display: grid; gap: 1rem; margin-top: 1.5rem; min-width: 0; }
.analysis-media figure { min-width: 0; margin: 0; }
.analysis-media img { width: 100%; aspect-ratio: 1.6; object-fit: contain; border-radius: 6px; background: var(--paper); }
.analysis-media figcaption { display: grid; gap: .35rem; padding: .7rem 0 0; }
.analysis-media figcaption strong { color: var(--ink); font-weight: 550; }
.analysis-media .text-link { justify-self: start; font-size: .8125rem; }
.analysis-tables { min-width: 0; margin-top: 1.5rem; }
.analysis-panel-scroll > .analysis-tables:first-child { margin-top: 0; }
.analysis-tables + .analysis-prose { margin-top: 1.5rem; }
.analysis-table-detail, .analysis-data-detail { border-bottom: 1px solid var(--line); }
.analysis-table-detail summary, .analysis-data-detail summary { min-height: 44px; padding-block: .85rem; color: var(--ink); font-size: .875rem; font-weight: 550; }
.analysis-table-detail summary span { color: var(--muted); font-size: .75rem; font-weight: 400; white-space: nowrap; }
.analysis-table-detail summary span::before { content: ' · '; }
.analysis-table-detail[open] { padding-bottom: 1rem; }
.analysis-table-qualification { margin-block: .25rem .75rem; }
.analysis-tables :deep(.table-wrap), .analysis-extraction :deep(.table-wrap) { width: 100%; max-width: 100%; min-width: 0; margin-block: 0; overflow-x: auto; overscroll-behavior-x: contain; }
.analysis-tables :deep(.data-table), .analysis-extraction :deep(.data-table) { display: table; min-width: 36rem; width: 100%; font-variant-numeric: tabular-nums; }
.analysis-tables :deep(caption), .analysis-extraction :deep(caption) { display: table-caption; text-align: left; }
.analysis-panel :deep(.data-table thead) { display: table-header-group; position: static; width: auto; height: auto; overflow: visible; clip-path: none; }
.analysis-panel :deep(.data-table tbody) { display: table-row-group; }
.analysis-panel :deep(.data-table tr) { display: table-row; padding: 0; border: 0; }
.analysis-panel :deep(.data-table th), .analysis-panel :deep(.data-table td) { display: table-cell; min-width: 5rem; padding: .75rem 1rem; border-bottom: 1px solid var(--line); overflow-wrap: normal; font-size: .8125rem; text-align: left; }
.analysis-panel :deep(.data-table td:first-child) { min-width: 9rem; font-size: .8125rem; }
.analysis-panel :deep(.data-table .numeric) { text-align: right !important; }
.analysis-panel :deep(.data-table td::before) { display: none; }
.analysis-data-section { margin-top: 1.5rem; }
.analysis-data-section:first-child { margin-top: 0; }
.analysis-data-section > .text-link { margin-bottom: .5rem; }
.analysis-source-list { margin-block: .5rem 1rem; }
.analysis-source-list li + li { margin-top: .15rem; }
.analysis-source-list .text-link { font-size: .875rem; }
.analysis-identities { display: grid; gap: .3rem; margin-block: .5rem 1rem; font-size: .8125rem; }
.analysis-identities dt { color: var(--muted); }
.analysis-identities dd { margin: 0 0 .6rem; overflow-wrap: anywhere; }
.analysis-identities code { font-size: .75rem; }
.analysis-caption-list { margin-block: .5rem 1rem; font-size: .8125rem; }
.analysis-caption-list dt { margin-bottom: .3rem; font-weight: 550; }
.analysis-caption-list dd { margin: 0 0 1.25rem; color: var(--muted); }
.analysis-data-detail > ol { font-size: .8125rem; }
.analysis-asset-source { margin-bottom: 1.25rem; }
.analysis-asset-source p { font-size: .8125rem; }
.analysis-next { margin-top: 0; }
.analysis-next a { padding: 1rem; }
.analysis-page :is(button, select, summary, a, [tabindex]):focus-visible { outline: 2px solid var(--focus); outline-offset: 3px; }

@media (min-width: 650px) {
  .analysis-panel-heading { padding: 1rem 1.5rem; }
  .analysis-panel-scroll { padding: 1.5rem; }
  .analysis-media { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .analysis-identities { grid-template-columns: 11rem minmax(0, 1fr); gap: .65rem 1rem; }
  .analysis-identities dd { margin: 0; }
}
@media (min-width: 1000px) {
  .analysis-workspace { grid-template-columns: 220px minmax(0, 1fr); gap: 1.5rem; }
  .analysis-topic-mobile { display: none; }
  .analysis-topic-rail { display: block; align-self: start; max-height: clamp(26rem, 68dvh, 52rem); padding: .5rem; overflow-y: auto; overscroll-behavior: contain; scrollbar-width: thin; }
  .analysis-topic-rail h2 { margin: .5rem .65rem .75rem; font-size: .8125rem; color: var(--muted); letter-spacing: 0; }
  .analysis-topic-rail button { display: block; width: 100%; min-height: 44px; margin-bottom: .2rem; padding: .65rem; border: 1px solid transparent; border-radius: 6px; color: var(--muted); background: transparent; font: inherit; font-size: .875rem; line-height: 1.4; text-align: left; overflow-wrap: anywhere; }
  .analysis-topic-rail button:hover { color: var(--ink); background: var(--surface); }
  .analysis-topic-rail button[aria-current] { color: var(--ink); background: var(--surface); border-color: var(--control-border); font-weight: 550; }
  .analysis-topic-rail button[aria-current]::before { content: ''; display: inline-block; width: .4rem; height: .4rem; margin-right: .5rem; border-radius: 50%; background: var(--accent); vertical-align: .1em; }
}
@media print {
  .analysis-topic-rail, .analysis-topic-mobile { display: none; }
  .analysis-workspace { display: block; }
  .analysis-panel { height: auto; border: 0; }
  .analysis-panel-scroll { overflow: visible; padding: 0; }
  .analysis-panel :deep(.table-wrap) { overflow: visible; }
  .analysis-panel :deep(.data-table) { min-width: 0; }
}
</style>
