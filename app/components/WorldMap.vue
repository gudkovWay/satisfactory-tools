<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ProjectDocument } from '~~/shared/types/project'

const props = defineProps<{ project: ProjectDocument }>()

const VIEW_WIDTH = 1280
const VIEW_HEIGHT = 900
const PAD = { left: 64, right: 64, top: 72, bottom: 88 }

const map = computed(() => props.project.map ?? null)
const mapScales = computed(() => map.value?.scales ?? [])
const mapNotes = computed(() => map.value?.notes ?? [])
const mapTables = computed(() => map.value?.tables ?? [])
const terrain = computed(() => map.value?.terrain ?? null)
const site = computed(() => map.value?.site ?? null)

const scaleId = ref<string>(
  map.value?.scales.find(scale => scale.id === 'region')?.id
  ?? map.value?.scales[0]?.id
  ?? ''
)

const activeScale = computed(() => {
  const scales = mapScales.value
  return scales.find(scale => scale.id === scaleId.value) ?? scales[0] ?? null
})

const plot = computed(() => {
  const bounds = activeScale.value?.bounds ?? map.value?.worldBounds ?? [-1, 1, -1, 1]
  const [minX, maxX, minY, maxY] = bounds
  const spanX = Math.max(1, maxX - minX)
  const spanY = Math.max(1, maxY - minY)
  const availableWidth = VIEW_WIDTH - PAD.left - PAD.right
  const availableHeight = VIEW_HEIGHT - PAD.top - PAD.bottom
  const scale = Math.min(availableWidth / spanX, availableHeight / spanY)
  const width = spanX * scale
  const height = spanY * scale
  return {
    minX,
    maxX,
    minY,
    maxY,
    scale,
    left: PAD.left + (availableWidth - width) / 2,
    top: PAD.top + (availableHeight - height) / 2,
    width,
    height,
  }
})

function projectX(value: number) {
  return plot.value.left + (value - plot.value.minX) * plot.value.scale
}

function projectY(value: number) {
  return plot.value.top + (value - plot.value.minY) * plot.value.scale
}

function inside(x: number, y: number) {
  return x >= plot.value.minX && x <= plot.value.maxX && y >= plot.value.minY && y <= plot.value.maxY
}

const terrainImage = computed(() => {
  const bounds = map.value?.worldBounds
  if (!bounds) return null
  return {
    x: projectX(bounds[0]),
    y: projectY(bounds[2]),
    width: (bounds[1] - bounds[0]) * plot.value.scale,
    height: (bounds[3] - bounds[2]) * plot.value.scale,
  }
})

function boxRect(box: [number, number, number, number] | undefined) {
  if (!box) return null
  const [minX, minY, maxX, maxY] = box
  return {
    x: projectX(minX),
    y: projectY(minY),
    width: (maxX - minX) * plot.value.scale,
    height: (maxY - minY) * plot.value.scale,
  }
}

const protectedBoxRect = computed(() => boxRect(map.value?.protectedBox))
const protectedFactoryRect = computed(() => boxRect(map.value?.protectedFactoryBounds))

const candidateRect = computed(() => {
  const current = site.value
  if (!current) return null
  const originX = current.origin[0]
  const originY = current.origin[1]
  return {
    x: projectX(originX),
    y: projectY(originY),
    width: current.width * plot.value.scale,
    height: current.depth * plot.value.scale,
  }
})

const candidateCenter = computed(() => {
  const current = site.value
  if (!current) return null
  return { x: projectX(current.x), y: projectY(current.y), inside: inside(current.x, current.y) }
})

const candidateLabel = computed(() => {
  const center = candidateCenter.value
  if (!center) return null
  const anchor = center.x > plot.value.left + plot.value.width * 0.68 ? 'end' : 'start'
  return {
    x: anchor === 'end' ? center.x - 22 : center.x + 22,
    y: center.y - 28,
    anchor,
  }
})

const hubPoint = computed(() => {
  const hub = map.value?.hub
  if (!hub || hub.length < 2) return null
  const x = hub[0] ?? 0
  const y = hub[1] ?? 0
  return { x, y, px: projectX(x), py: projectY(y), inside: inside(x, y) }
})

const withdrawnPoint = computed(() => {
  const marker = map.value?.withdrawnMarker
  if (!marker) return null
  const anchor = projectX(marker.x) > plot.value.left + plot.value.width * 0.68 ? 'end' : 'start'
  return {
    ...marker,
    px: projectX(marker.x),
    py: projectY(marker.y),
    inside: inside(marker.x, marker.y),
    labelX: anchor === 'end' ? projectX(marker.x) - 18 : projectX(marker.x) + 18,
    labelY: projectY(marker.y) + 42,
    anchor,
  }
})

const siteInside = computed(() => {
  const current = site.value
  return Boolean(current && inside(current.x, current.y))
})

const siteCenter = computed(() => {
  const current = site.value
  if (!current) return null
  return { x: projectX(current.x), y: projectY(current.y) }
})

const feedPoints = computed(() => (map.value?.feeds ?? []).map((feed, index) => ({
  ...feed,
  number: index + 1,
  px: projectX(feed.x),
  py: projectY(feed.y),
  inside: inside(feed.x, feed.y),
})))

const extractorPoints = computed(() => (map.value?.protectedExtractors ?? []).map(extractor => ({
  ...extractor,
  px: projectX(extractor.x),
  py: projectY(extractor.y),
  inside: inside(extractor.x, extractor.y),
})))

const extractorLabelPoint = computed(() =>
  extractorPoints.value.find(extractor => extractor.inside) ?? null
)

const railPoints = computed(() => (map.value?.railPoints ?? []).map(point => ({
  x: projectX(point[0] ?? 0),
  y: projectY(point[1] ?? 0),
  inside: inside(point[0] ?? 0, point[1] ?? 0),
})))

const railPolyline = computed(() => railPoints.value.map(point => `${point.x},${point.y}`).join(' '))

function niceStep(span: number) {
  if (!Number.isFinite(span) || span <= 0) return 1
  const raw = span / 8
  const power = 10 ** Math.floor(Math.log10(raw))
  const fraction = raw / power
  const multiplier = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10
  return multiplier * power
}

function tickLabel(value: number) {
  const rounded = Math.round(value)
  return String(rounded).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

const xTicks = computed(() => {
  const current = plot.value
  const step = niceStep(current.maxX - current.minX)
  const first = Math.ceil(current.minX / step)
  const last = Math.floor(current.maxX / step)
  if (last - first > 40) return []
  const ticks: Array<{ x: number; label: string }> = []
  for (let index = first; index <= last; index += 1) {
    const value = index * step
    ticks.push({ x: projectX(value), label: tickLabel(value) })
  }
  return ticks
})

const yTicks = computed(() => {
  const current = plot.value
  const step = niceStep(current.maxY - current.minY)
  const first = Math.ceil(current.minY / step)
  const last = Math.floor(current.maxY / step)
  if (last - first > 40) return []
  const ticks: Array<{ y: number; label: string }> = []
  for (let index = first; index <= last; index += 1) {
    const value = index * step
    ticks.push({ y: projectY(value), label: tickLabel(value) })
  }
  return ticks
})

function number(value: number | undefined, digits = 2) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits).replace('.', ',') : 'нет данных'
}

function percent(value: number | undefined) {
  return typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(2).replace('.', ',')}%` : 'нет данных'
}

function feedUnitNote() {
  return 'Единица потока следует из предмета ввода: для жидкостей это объём в минуту, для предметов это штуки в минуту.'
}

const mapTitle = computed(() => {
  const label = site.value?.label ?? 'участок без названия'
  return `Карта: ${label}, масштаб ${activeScale.value?.label ?? 'нет данных'}`
})

const mapDescription = computed(() => {
  const current = activeScale.value
  const bounds = map.value?.worldBounds
  const scaleBounds = current
    ? `Видимые границы X ${number(current.bounds[0])} до ${number(current.bounds[1])}, Y ${number(current.bounds[2])} до ${number(current.bounds[3])}, метры.`
    : ''
  const worldBounds = bounds
    ? `Границы мира X ${number(bounds[0])} до ${number(bounds[1])}, Y ${number(bounds[2])} до ${number(bounds[3])}, метры.`
    : ''
  return [
    'Схематическая карта по исходным координатам в метрах, X направлен на восток, Y на юг.',
    scaleBounds,
    worldBounds,
    'Кандидат участка не утверждён. Защищённая зона, действующий завод и занятая добыча показаны отдельными штриховками.',
    'Номера питающих точек соответствуют таблице. Водная координата указывает водоём, а не проверенную позицию насоса.',
    'Страница не изменяет сохранение или карту игры.',
  ].filter(Boolean).join(' ')
})

const scaleBoundsText = computed(() => {
  const current = activeScale.value
  if (!current) return ''
  return `X ${number(current.bounds[0])} до ${number(current.bounds[1])}, Y ${number(current.bounds[2])} до ${number(current.bounds[3])} м`
})

const worldBoundsText = computed(() => {
  const bounds = map.value?.worldBounds
  if (!bounds) return ''
  return `X ${number(bounds[0])} до ${number(bounds[1])}, Y ${number(bounds[2])} до ${number(bounds[3])} м`
})

const candidateFootprint = computed(() => {
  const current = site.value
  if (!current) return ''
  return `${number(current.width, 1)} × ${number(current.depth, 1)} м, начало ${number(current.origin[0], 1)} / ${number(current.origin[1], 1)} м`
})

const coordinateColumns = ['Объект', 'X, м', 'Y, м', 'Z, м', 'Примечание']
const coordinateRows = computed(() => {
  const current = site.value
  if (!current || !map.value) return []
  const rows: string[][] = [
    [
      `Кандидат: ${current.label}`,
      number(current.x),
      number(current.y),
      number(current.baseZ),
      `Не утверждён. Контур ${candidateFootprint.value}`,
    ],
  ]
  const marker = withdrawnPoint.value
  if (marker) {
    rows.push(['Отозванная метка', number(marker.x), number(marker.y), number(marker.z), marker.label])
  }
  const hub = hubPoint.value
  if (hub) {
    rows.push(['HUB', number(hub.x), number(hub.y), 'нет данных', 'Существующая точка игрока'])
  }
  return rows
})

const feedColumns = [
  '№',
  'ID',
  'Ввод',
  'X, м',
  'Y, м',
  'Z, м',
  'Требуется',
  'Номинал',
  'Частота',
  'Чистота',
  'Примечание',
]
const waterFeed = (feed: { itemId: string; purity: string; note: string; capacity: number; clock: number }) =>
  feed.itemId === 'Desc_Water_C' || feed.purity.includes('водоём') || feed.note.includes('водоём')

const feedRows = computed(() => (map.value?.feeds ?? []).map((feed, index) => [
  String(index + 1),
  feed.id,
  feed.label,
  number(feed.x),
  number(feed.y),
  number(feed.z),
  number(feed.required, 3),
  waterFeed(feed) && feed.capacity === 0 ? 'не заявлена' : number(feed.capacity, 3),
  waterFeed(feed) && feed.clock === 0 ? 'не задана' : percent(feed.clock),
  feed.purity || 'не указана',
  constructionText(feed.note || 'нет примечания'),
]))

const extractorColumns = ['ID', 'Занятый ввод', 'Нода', 'X, м', 'Y, м', 'Z, м', 'Номинал настройки', 'Частота']
const extractorRows = computed(() => (map.value?.protectedExtractors ?? []).map(extractor => [
  extractor.id,
  extractor.label,
  extractor.node,
  number(extractor.x),
  number(extractor.y),
  number(extractor.z),
  number(extractor.nominal, 3),
  percent(extractor.clock),
]))
</script>

<template>
  <section class="panel world-map" aria-labelledby="world-map-heading">
    <header class="stack">
      <h2 id="world-map-heading" class="section-heading">Карта и координаты</h2>
      <p class="muted">Координаты в метрах. Площадка-кандидат и действующий завод отмечены отдельно: существующее снабжение не трогай.</p>
    </header>

    <div v-if="!map" class="empty-state">
      Для этого проекта нет опубликованных данных карты. Координаты и участок не подставляются.
    </div>

    <template v-else>
      <div class="button-row map-scales" role="group" aria-label="Масштаб карты">
        <Button
          v-for="scale in mapScales"
          :key="scale.id"
          type="button"
          class="map-scale"
          variant="outline"
          :aria-pressed="activeScale?.id === scale.id"
          @click="scaleId = scale.id"
        >
          {{ scale.label }}
        </Button>
      </div>

      <figure v-if="activeScale" class="map-figure">
        <svg
          class="map-canvas"
          :viewBox="`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`"
          role="img"
          aria-labelledby="world-map-title world-map-description"
        >
          <title id="world-map-title">{{ mapTitle }}</title>
          <desc id="world-map-description">{{ mapDescription }}</desc>

          <defs>
            <clipPath id="world-map-plot-clip">
              <rect
                :x="plot.left"
                :y="plot.top"
                :width="plot.width"
                :height="plot.height"
              />
            </clipPath>
            <pattern
              id="world-map-protected-pattern"
              width="10"
              height="10"
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)"
            >
              <line x1="0" y1="0" x2="0" y2="10" class="pattern-warning" />
            </pattern>
            <pattern id="world-map-factory-pattern" width="10" height="10" patternUnits="userSpaceOnUse">
              <path d="M0 0H10M0 0V10" class="pattern-warning-strong" />
            </pattern>
            <pattern
              id="world-map-candidate-pattern"
              width="12"
              height="12"
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)"
            >
              <line x1="0" y1="0" x2="0" y2="12" class="pattern-accent" />
            </pattern>
          </defs>

          <rect class="map-frame-rect" x="0" y="0" :width="VIEW_WIDTH" :height="VIEW_HEIGHT" />
          <rect
            class="map-plot-rect"
            :x="plot.left"
            :y="plot.top"
            :width="plot.width"
            :height="plot.height"
          />

          <g clip-path="url(#world-map-plot-clip)">
            <image
              v-if="terrain && terrainImage"
              :href="terrain.src"
              :x="terrainImage.x"
              :y="terrainImage.y"
              :width="terrainImage.width"
              :height="terrainImage.height"
              preserveAspectRatio="none"
            >
              <title>{{ terrain.alt }}</title>
            </image>

            <g class="map-grid" aria-hidden="true">
              <line
                v-for="(tick, index) in xTicks"
                :key="`x-${index}`"
                :x1="tick.x"
                :x2="tick.x"
                :y1="plot.top"
                :y2="plot.top + plot.height"
              />
              <line
                v-for="(tick, index) in yTicks"
                :key="`y-${index}`"
                :x1="plot.left"
                :x2="plot.left + plot.width"
                :y1="tick.y"
                :y2="tick.y"
              />
            </g>

            <g v-if="railPolyline" class="map-rail" aria-hidden="true">
              <polyline :points="railPolyline" />
              <circle
                v-for="(point, index) in railPoints"
                v-show="point.inside"
                :key="`rail-${index}`"
                :cx="point.x"
                :cy="point.y"
                r="1.8"
              />
            </g>

            <g v-if="protectedBoxRect" class="protected-box">
              <rect
                :x="protectedBoxRect.x"
                :y="protectedBoxRect.y"
                :width="protectedBoxRect.width"
                :height="protectedBoxRect.height"
                fill="url(#world-map-protected-pattern)"
              />
              <text
                class="map-label map-small"
                :x="protectedBoxRect.x + 8"
                :y="protectedBoxRect.y + 22"
              >
                Защищённая зона
              </text>
            </g>

            <g v-if="protectedFactoryRect" class="protected-factory">
              <rect
                :x="protectedFactoryRect.x"
                :y="protectedFactoryRect.y"
                :width="protectedFactoryRect.width"
                :height="protectedFactoryRect.height"
                fill="url(#world-map-factory-pattern)"
              />
              <text
                class="map-label"
                :x="protectedFactoryRect.x + 8"
                :y="protectedFactoryRect.y - 8"
              >
                Действующий завод
              </text>
            </g>

            <g class="protected-extractors">
              <circle
                v-for="extractor in extractorPoints"
                v-show="extractor.inside"
                :key="extractor.id"
                class="extractor-dot"
                :cx="extractor.px"
                :cy="extractor.py"
                r="5"
              >
                <title>
                  Занято: {{ extractor.label }}; нода {{ extractor.node }}; настройка
                  {{ number(extractor.nominal, 3) }}, частота {{ percent(extractor.clock) }}
                </title>
              </circle>
              <text
                v-if="extractorLabelPoint"
                class="map-label map-small"
                :x="extractorLabelPoint.px + 10"
                :y="extractorLabelPoint.py - 8"
              >
                Занятая добыча
              </text>
            </g>

            <g class="map-feeds">
              <template v-for="feed in feedPoints" :key="feed.id">
                <template v-if="feed.inside">
                  <line
                    v-if="siteInside && siteCenter"
                    class="feed-line"
                    :x1="feed.px"
                    :y1="feed.py"
                    :x2="siteCenter.x"
                    :y2="siteCenter.y"
                  />
                  <circle class="feed-dot" :cx="feed.px" :cy="feed.py" r="3.5" />
                  <g class="feed-marker">
                    <title>
                      {{ feed.number }}. {{ feed.label }}: X {{ number(feed.x) }}, Y {{ number(feed.y) }},
                      Z {{ number(feed.z) }} м. Требуется {{ number(feed.required, 3) }}, номинал
                      {{ number(feed.capacity, 3) }}, частота {{ percent(feed.clock) }}.
                    </title>
                    <circle :cx="feed.px" :cy="feed.py" r="13" />
                    <text :x="feed.px" :y="feed.py + 4.5" text-anchor="middle">
                      {{ feed.number }}
                    </text>
                  </g>
                </template>
              </template>
            </g>

            <g v-if="candidateRect && candidateCenter" class="candidate-plot">
              <rect
                :x="candidateRect.x"
                :y="candidateRect.y"
                :width="candidateRect.width"
                :height="candidateRect.height"
                fill="url(#world-map-candidate-pattern)"
              />
              <circle :cx="candidateCenter.x" :cy="candidateCenter.y" r="9" />
              <path
                class="candidate-crosshair"
                :d="`M${candidateCenter.x - 26},${candidateCenter.y}h15m22,0h15M${candidateCenter.x},${candidateCenter.y - 26}v15m0,22v15`"
              />
            </g>

            <g v-if="candidateLabel" class="map-label">
              <text :x="candidateLabel.x" :y="candidateLabel.y" :text-anchor="candidateLabel.anchor">
                Кандидат, не утверждён
              </text>
              <text
                class="map-small"
                :x="candidateLabel.x"
                :y="candidateLabel.y + 18"
                :text-anchor="candidateLabel.anchor"
              >
                X {{ number(site?.x ?? 0) }} / Y {{ number(site?.y ?? 0) }} м
              </text>
            </g>

            <g v-if="withdrawnPoint && withdrawnPoint.inside" class="withdrawn-marker">
              <path
                :d="`M${withdrawnPoint.px - 9},${withdrawnPoint.py - 9}l18,18m-18,0l18,-18`"
              />
              <text
                class="map-label map-small"
                :x="withdrawnPoint.labelX"
                :y="withdrawnPoint.labelY"
                :text-anchor="withdrawnPoint.anchor"
              >
                Старая метка отозвана
              </text>
            </g>

            <g v-if="hubPoint && hubPoint.inside" class="hub-marker">
              <circle :cx="hubPoint.px" :cy="hubPoint.py" r="8" />
              <text class="map-label" :x="hubPoint.px + 16" :y="hubPoint.py - 12">HUB</text>
            </g>
          </g>

          <rect
            class="map-plot-border"
            :x="plot.left"
            :y="plot.top"
            :width="plot.width"
            :height="plot.height"
          />

          <g class="map-axis" aria-hidden="true">
            <text
              v-for="(tick, index) in xTicks"
              :key="`x-label-${index}`"
              :x="tick.x"
              :y="plot.top + plot.height - 6"
              text-anchor="middle"
            >
              {{ tick.label }}
            </text>
            <text
              v-for="(tick, index) in yTicks"
              :key="`y-label-${index}`"
              :x="plot.left + 6"
              :y="tick.y - 4"
            >
              {{ tick.label }}
            </text>
            <text class="map-axis-note" x="64" y="894">
              X на восток, Y на юг. Значения в метрах. {{ activeScale.label }}: {{ scaleBoundsText }}.
            </text>
          </g>
        </svg>

        <figcaption>
          <strong>{{ terrain?.caption || 'Карта участка по исходным данным' }}</strong>
          <span v-if="terrain" class="fine">{{ terrain.alt }}</span>
          <span class="fine">
            Масштаб {{ activeScale.label }}. Границы мира: {{ worldBoundsText }}. Координаты в метрах.
          </span>
        </figcaption>
      </figure>
      <div v-else class="empty-state">В данных карты нет доступных масштабов.</div>

      <ul class="map-legend" aria-label="Обозначения карты">
        <li><span class="legend-swatch legend-candidate" aria-hidden="true"></span>Кандидат участка: штриховая рамка, перекрестие и подпись «не утверждён».</li>
        <li><span class="legend-swatch legend-protected" aria-hidden="true"></span>Защищённая зона: диагональная штриховка.</li>
        <li><span class="legend-swatch legend-factory" aria-hidden="true"></span>Действующий завод: перекрёстная штриховка.</li>
        <li><span class="legend-swatch legend-extractor" aria-hidden="true"></span>Занятая добыча: точка с подсказкой.</li>
        <li><span class="legend-swatch legend-withdrawn" aria-hidden="true"></span>Отозванная старая метка: крест.</li>
        <li><span class="legend-swatch legend-feed" aria-hidden="true"></span>Новая питающая точка: номер в круге.</li>
        <li><span class="legend-swatch legend-rail" aria-hidden="true"></span>Существующий рельс: линия с точками.</li>
        <li><span class="legend-swatch legend-hub" aria-hidden="true"></span>HUB: отдельный маркер.</li>
      </ul>

      <div class="notice notice-warning" role="note">
        <p>
          Кандидат участка не утверждён. Защищённые вводы и существующий завод не являются
          свободной мощностью проекта. Водная координата указывает водоём, а не проверенную
          позицию насоса. Карта не подтверждает коллизии, подходы или пригодность участка.
        </p>
        <p class="fine">
          Водная точка: координата водоёма, не готовая позиция насоса. Все расстояния и
          координаты приведены в метрах.
        </p>
      </div>

      <section class="stack map-section" aria-labelledby="map-coordinates-heading">
        <h3 id="map-coordinates-heading" class="eyebrow">Координаты участка</h3>
        <DataTable
          :columns="coordinateColumns"
          :rows="coordinateRows"
          caption="Кандидат, отозванная метка и HUB в метрах"
        />
      </section>

      <section class="stack map-section" aria-labelledby="map-feeds-heading">
        <h3 id="map-feeds-heading" class="eyebrow">Питающие точки</h3>
        <p class="fine">{{ feedUnitNote() }}</p>
        <DataTable
          :columns="feedColumns"
          :rows="feedRows"
          caption="Новые питающие точки: координаты и расход"
        />
      </section>

      <section class="stack map-section" aria-labelledby="map-extractors-heading">
        <h3 id="map-extractors-heading" class="eyebrow">Занятая добыча</h3>
        <p class="fine">
          Номинал отражает настройку существующей добычи, а не свободный остаток мощности.
        </p>
        <DataTable
          :columns="extractorColumns"
          :rows="extractorRows"
          caption="Защищённые добывающие установки"
        />
      </section>

      <section
        v-if="mapTables.length"
        class="stack map-section"
        aria-labelledby="map-tables-heading"
      >
        <h3 id="map-tables-heading" class="eyebrow">Исходные таблицы карты</h3>
        <details v-for="(table, index) in mapTables" :key="index">
          <summary>{{ table.caption }}</summary>
          <DataTable :columns="table.columns" :rows="table.rows" :caption="table.caption" />
        </details>
      </section>

      <section v-if="mapNotes.length" class="stack map-section" aria-labelledby="map-notes-heading">
        <h3 id="map-notes-heading" class="eyebrow">Примечания к карте</h3>
        <details v-for="(note, index) in mapNotes" :key="index">
          <summary>{{ constructionText(note.title) }}</summary>
          <p>{{ constructionText(note.body) }}</p>
        </details>
      </section>
    </template>
  </section>
</template>

<style scoped>
.map-scales {
  margin-block: 1rem;
}

.map-scale {
  width: auto;
  min-height: 44px;
}

.map-scale[aria-pressed="true"] {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--ink);
  font-weight: 600;
}

.map-figure {
  margin: 0;
}

.map-canvas {
  display: block;
  width: 100%;
  height: auto;
  max-height: 78vh;
  border: 1px solid var(--line);
}

.map-frame-rect {
  fill: var(--surface-raised);
}

.map-plot-rect {
  fill: var(--surface-raised);
}

.map-plot-border {
  fill: none;
  stroke: var(--control-border);
  stroke-width: 1.5;
}

.map-grid line {
  stroke: var(--line);
  stroke-opacity: 0.45;
  stroke-width: 1;
}

.map-axis text {
  fill: #f7f8f5;
  font-size: 13px;
  paint-order: stroke;
  stroke: #101b20;
  stroke-width: 3px;
  stroke-linejoin: round;
}

.map-axis-note {
  font-size: 14px;
}

.map-label {
  fill: #f7f8f5;
  font-size: 18px;
  font-weight: 600;
  paint-order: stroke;
  stroke: #101b20;
  stroke-width: 4px;
  stroke-linejoin: round;
}

.map-small {
  font-size: 13px;
  font-weight: 400;
}

.map-rail polyline {
  fill: none;
  stroke: var(--muted);
  stroke-width: 2;
  stroke-dasharray: 6 6;
}

.map-rail circle {
  fill: var(--muted);
}

.protected-box rect {
  stroke: var(--warning);
  stroke-width: 2;
  stroke-dasharray: 9 6;
}

.protected-factory rect {
  stroke: var(--warning);
  stroke-width: 2.5;
}

.pattern-warning {
  stroke: var(--warning);
  stroke-width: 2;
}

.pattern-warning-strong {
  stroke: var(--warning);
  stroke-width: 1.6;
  opacity: 0.85;
}

.pattern-accent {
  stroke: var(--accent);
  stroke-width: 1.6;
}

.extractor-dot {
  fill: var(--warning);
  stroke: #101b20;
  stroke-width: 1.5;
}

.feed-line {
  stroke: var(--accent);
  stroke-width: 1.8;
  stroke-dasharray: 5 6;
  opacity: 0.9;
}

.feed-dot {
  fill: var(--accent);
  stroke: #101b20;
  stroke-width: 1;
}

.feed-marker circle {
  fill: #101b20;
  stroke: var(--accent);
  stroke-width: 3;
}

.feed-marker text {
  fill: #f7f8f5;
  font-size: 12px;
  font-weight: 700;
}

.candidate-plot rect {
  stroke: var(--accent);
  stroke-width: 3;
  stroke-dasharray: 10 6;
}

.candidate-plot circle {
  fill: #101b20;
  stroke: var(--accent);
  stroke-width: 3;
}

.candidate-crosshair {
  fill: none;
  stroke: var(--accent);
  stroke-width: 2.5;
}

.withdrawn-marker path {
  fill: none;
  stroke: var(--warning);
  stroke-width: 4;
}

.hub-marker circle {
  fill: var(--accent);
  stroke: #101b20;
  stroke-width: 2;
}

.map-figure figcaption {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding-top: 0.75rem;
}

.map-legend {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 16rem), 1fr));
  gap: 0.5rem 1rem;
  margin-block: 1rem;
  padding: 0;
  list-style: none;
}

.map-legend li {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.legend-swatch {
  flex: none;
  width: 1.25rem;
  height: 1.25rem;
  margin-top: 0.15rem;
  border: 2px solid var(--accent);
  border-radius: 2px;
}

.legend-candidate {
  border-style: dashed;
}

.legend-protected {
  border-color: var(--warning);
  background: repeating-linear-gradient(45deg, transparent 0 3px, var(--warning) 3px 5px);
}

.legend-factory {
  border-color: var(--warning);
  background:
    repeating-linear-gradient(0deg, transparent 0 4px, var(--warning) 4px 5px),
    repeating-linear-gradient(90deg, transparent 0 4px, var(--warning) 4px 5px);
}

.legend-extractor {
  border-color: var(--warning);
  border-radius: 50%;
  background: var(--warning);
}

.legend-withdrawn {
  border: none;
  background:
    linear-gradient(45deg, transparent 45%, var(--warning) 45% 55%, transparent 55%),
    linear-gradient(-45deg, transparent 45%, var(--warning) 45% 55%, transparent 55%);
}

.legend-feed {
  border-color: var(--accent);
  border-radius: 50%;
  background: #101b20;
}

.legend-rail {
  border: none;
  background: repeating-linear-gradient(90deg, var(--muted) 0 5px, transparent 5px 9px);
  height: 0.35rem;
  margin-top: 0.55rem;
}

.legend-hub {
  border-color: var(--accent);
  border-radius: 50%;
  background: var(--accent);
}

.map-section {
  margin-top: 1.5rem;
}

@media (max-width: 48rem) {
  .map-canvas {
    min-width: 40rem;
  }

  .map-figure {
    overflow-x: auto;
  }
}
</style>
