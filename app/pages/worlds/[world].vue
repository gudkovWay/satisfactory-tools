<script setup lang="ts">
import { loadWorld, worldContextKey } from '~/composables/useWorld'
definePageMeta({ key: route => String(route.params.world) })
const route = useRoute()
const worldId = String(route.params.world)
const { data, error } = await useAsyncData(`atlas-world:${worldId}`, () => loadWorld(worldId))
if (error.value) throw createError({ statusCode: error.value.statusCode || 500, statusMessage: error.value.statusMessage || 'Не удалось загрузить мир' })
if (!data.value) throw createError({ statusCode: 404, statusMessage: 'Мир не найден' })
provide(worldContextKey, computed(() => data.value!))
</script>
<template><div class="world-context"><NuxtPage :page-key="route => route.path" /></div></template>
