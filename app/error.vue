<script setup lang="ts">
import type { NuxtError } from '#app'
defineProps<{ error: NuxtError }>()
</script>
<template>
  <main id="main" class="error-page page-width"><p class="muted">Строительный атлас / {{ error.statusCode }}</p><h1>{{ error.statusCode === 404 ? 'Такого мира, проекта или раздела нет' : 'Не удалось открыть атлас' }}</h1><p>Адрес мог измениться. Выбери мир в каталоге и открой нужный проект.</p><Button @click="clearError({ redirect: '/world' })">Вернуться к мирам</Button></main>
</template>
