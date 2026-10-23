<script setup lang="ts">
import type { NuxtError } from '#app'
defineProps<{ error: NuxtError }>()
</script>
<template>
  <main id="main" class="error-page page-width"><p class="muted">Заводской атлас / {{ error.statusCode }}</p><h1>{{ error.statusCode === 404 ? 'Такого проекта или раздела нет' : 'Не удалось открыть атлас' }}</h1><p>Адрес мог измениться. В каталоге находятся опубликованные проекты доступных сейвов.</p><Button @click="clearError({ redirect: '/' })">Вернуться к проектам</Button></main>
</template>
