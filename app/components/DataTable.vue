<script setup lang="ts">
const props = defineProps<{ columns: string[]; rows: string[][]; caption?: string }>()
const tableCaption = computed(() => props.caption?.trim() || 'Таблица данных')
const numeric = computed(() => props.columns.map((_, index) => props.rows.length > 0 && props.rows.every(row => !row[index]?.trim() || /^[+−-]?\d[\d\s.,%×/]*(?:\s*(?:м³|м|шт|МВт|кВт|\/мин))*$/u.test(row[index]!.trim()))))
</script>

<template>
  <div v-if="columns.length" class="table-wrap" role="region" :aria-label="`${tableCaption}: таблица`" tabindex="0">
    <table class="data-table" role="table"><caption>{{ constructionText(tableCaption) }}</caption><thead role="rowgroup"><tr role="row"><th v-for="(column, index) in columns" :key="index" scope="col" role="columnheader" :class="{ numeric: numeric[index] }">{{ constructionText(column) }}</th></tr></thead><tbody role="rowgroup"><template v-if="rows.length"><tr v-for="(row, rowIndex) in rows" :key="rowIndex" role="row"><td v-for="(column, index) in columns" :key="index" role="cell" :data-label="constructionText(column)" :class="{ numeric: numeric[index] }">{{ constructionText(row[index] ?? '') }}</td></tr></template><tr v-else role="row"><td :colspan="columns.length" class="muted table-empty" role="cell">Нет строк для отображения.</td></tr></tbody></table>
  </div>
  <p v-else class="empty-state">Таблица без колонок.</p>
</template>
