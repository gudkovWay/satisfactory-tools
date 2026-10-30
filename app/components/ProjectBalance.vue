<script setup lang="ts">
import type { ProjectDocument } from '~~/shared/types/project'
const props = defineProps<{ project: ProjectDocument }>()
const targets = computed(() => props.project.production?.targets ?? (props.project.target ? [props.project.target] : []))
const search = ref('')
const selectedItem = ref(props.project.production?.comparisons.find(item => item.itemId === 'Desc_Motor_C')?.itemId || props.project.production?.comparisons[0]?.itemId || '')
const selectedOnly = ref(false)
const allOpen = ref(false)
const groups = computed(() => props.project.production?.processes.filter(process => [process.id, process.recipeName, ...process.outputs.map(flow => flow.label)].join(' ').toLocaleLowerCase('ru').includes(search.value.trim().toLocaleLowerCase('ru'))) || [])
const comparison = computed(() => props.project.production?.comparisons.find(item => item.itemId === selectedItem.value))
const variants = computed(() => comparison.value?.variants.filter(variant => !selectedOnly.value || variant.selected) || [])
const comparisonOptions = computed(() => props.project.production?.comparisons.map(item => ({ value: item.itemId, label: item.label })) || [])
const levelLabels = (id: string) => [...new Set(props.project.placements.filter(placement => placement.processId === id).map(placement => placement.levelId))].join(', ')
</script>
<template>
  <div v-if="!project.production" class="empty-state"><h2>У этого проекта нет производственного баланса</h2><p>Дороги, депо и склады описывают свою пропускную способность в разделе инфраструктуры.</p></div>
  <div v-else class="stack">
    <section><h2>Целевой выпуск</h2><FlowList :flows="targets" /><p class="fine">Полезные продукты проекта, отдельно от побочного остатка.</p></section>
    <section class="balance-summary split"><div><h2>Сырьё для завода</h2><FlowList :flows="project.production.rawInputs" /><p class="fine">{{ project.source.planning ? 'Расчёт стандартной цепочки и WB; фактическое влияние всех модов ещё не измерено.' : 'Расход в минуту по закреплённому источнику.' }}</p></div><div><h2>Побочный остаток</h2><FlowList :flows="project.production.disposal" /><p v-if="project.production.disposal.length">Предусмотри вывоз или полезное потребление. Буфер сам по себе не устраняет риск остановки.</p><p v-else>Побочных продуктов в выбранной цепочке нет. Полезные нетто-выходы перечислены выше.</p><details class="reference-disclosure"><summary>Допущения расчёта</summary><p v-for="note in project.production.notes" :key="note" class="fine">{{ constructionText(note) }}</p></details></div></section>
    <section>
      <div class="section-heading"><h2>Полная цепочка</h2><span class="muted">{{ project.production.processes.length }} рецептурных групп</span></div>
      <div class="process-controls">
        <label class="field" for="process-search"><span>Найти изделие или рецепт</span><Input id="process-search" :model-value="search" variant="filled" type="search" placeholder="Мотор, резина, P05" @update:model-value="search = String($event)" /></label>
        <Button variant="outline" @click="allOpen = !allOpen">{{ allOpen ? 'Свернуть группы' : 'Раскрыть группы' }}</Button>
      </div>
      <p v-if="!groups.length" class="empty-state">Такой группы нет. Попробуй название изделия или номер процесса.</p>
      <details v-for="process in groups" :key="process.id" class="process-group" :open="allOpen"><summary><span class="process-code">{{ process.id }}</span><span class="process-name"><strong>{{ process.outputs.map(flow => flow.label).join(' + ') }}</strong><small>{{ process.recipeName }} · {{ process.machineName }}</small></span><span class="process-machine">{{ process.machines }} × {{ formatRate(process.clock * 100, 6) }}%</span></summary><div class="process-details"><p>{{ constructionText(process.note) }}</p><p class="fine">{{ levelLabels(process.id) }} · Частота каждой машины {{ formatRate(process.clock * 100, 6) }}%.</p><div class="split"><div><h3>На всю группу: вход</h3><FlowList :flows="process.inputs" /><h3>На всю группу: выход</h3><FlowList :flows="process.outputs" /></div><div><h3>На одну машину: вход</h3><FlowList :flows="process.inputs" :divisor="process.machines" /><h3>На одну машину: выход</h3><FlowList :flows="process.outputs" :divisor="process.machines" /></div></div><details class="reference-disclosure"><summary>Точный рецепт и коэффициенты</summary><p class="fine">Базовый цикл {{ formatRate(process.durationSeconds) }} с. Множитель {{ process.speedMultiplier }}. Частота {{ process.clockFraction || formatRate(process.clock, 8) }}.</p><p class="recipe-path fine">{{ process.recipePath }}</p></details></div></details>
    </section>
    <section v-if="project.production.comparisons.length">
      <h2>Почему выбран этот рецепт</h2>
      <div class="comparison-controls">
        <div class="field"><label for="comparison-item">Изделие</label><TheSelect trigger-id="comparison-item" :model-value="selectedItem" :options="comparisonOptions" @update:model-value="selectedItem = String($event)" /></div>
        <label class="check-row"><input v-model="selectedOnly" type="checkbox">Только выбранные рецепты</label>
      </div>
      <p v-if="!variants.length" class="empty-state">Для этого изделия в выбранной цепи нет отдельного рецепта. Покажи все варианты.</p>
      <div v-for="variant in variants" :key="variant.key" class="recipe-variant"><div class="section-heading"><h3>{{ variant.name }}</h3><span v-if="variant.selected" class="tag">В этой цепи</span></div><div class="split"><div><h4>Входы на единицу продукта</h4><FlowList :flows="variant.inputs" /></div><div><h4>Побочные на единицу</h4><FlowList :flows="variant.byproducts" /><p class="fine">Mk.3 на 100%: {{ formatRate(variant.outputAtFullClock, 6) }} / мин</p></div></div><details><summary>Точный путь рецепта</summary><p class="recipe-path fine">{{ variant.path }}</p></details></div>
      <details class="reference-disclosure"><summary>Как сравнивались рецепты</summary><p class="fine">{{ project.production.normalizedRecipeCount }} открытых производственных рецепта, {{ project.production.candidateRecipeCount }} кандидатов в цепочке зависимостей. Сравнение одного рецепта не заменяет сравнение всей производственной цепи.</p></details>
    </section>
    <details class="reference-disclosure"><summary>Сравнить полные производственные сценарии</summary><DataTable :columns="project.production.scenarios.columns" :rows="project.production.scenarios.rows" :caption="project.production.scenarios.caption" /></details>
  </div>
</template>
