<script setup lang="ts">
import type { ContentNote } from '~~/shared/types/project'
defineProps<{ notes: ContentNote[] }>()
</script>
<template><div v-if="notes.length" class="content-notes"><details v-for="note in notes" :key="note.title" class="reference-disclosure"><summary>{{ constructionText(note.title) }}</summary><p>{{ constructionText(note.body) }}</p></details></div></template>
