<script setup lang="ts">
import { Factory, Moon, Sun } from '@lucide/vue'
import type { WorldRegistry } from '~~/shared/types/world'
const colorMode = useColorMode()
const route = useRoute()
useAtlasMotion()
const { data: registry } = await useFetch<WorldRegistry>('/worlds/index.json', { key: 'atlas-world-registry' })
const activeWorld = computed(() => registry.value?.worlds.find(world => world.id === route.params.world))
const worldOptions = computed(() => registry.value?.worlds.map(world => ({ value: world.id, label: world.title })) ?? [])
const themeLabel = computed(() => colorMode.value === 'dark' ? 'Светлая тема' : 'Тёмная тема')
function toggleTheme() { colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark' }
function switchWorld(value: string | number) {
  if (registry.value?.worlds.some(world => world.id === value)) void navigateTo(worldUrl(String(value)))
}
</script>
<template>
  <div class="atlas-app">
    <a class="skip-link" href="#main">К содержимому</a>
    <header class="site-header">
      <NuxtLink class="wordmark" to="/world" aria-label="Строительный атлас: каталог миров"><Factory :size="27" :stroke-width="1.8" aria-hidden="true" /><span><span class="wordmark-title">Satisfactory<span class="wordmark-sub">Строительный атлас</span></span></span></NuxtLink>
      <nav class="global-nav" aria-label="Главная навигация">
        <NuxtLink class="header-link" to="/world"><RollLabel text="Все миры" /><span aria-hidden="true">↗</span></NuxtLink>
        <div v-if="worldOptions.length > 1" class="field world-switch"><label class="sr-only" for="world-switch">Переключить мир</label><TheSelect trigger-id="world-switch" :model-value="activeWorld?.id || ''" :options="worldOptions" placeholder="Выбрать мир" @update:model-value="switchWorld" /></div>
        <ClientOnly><button class="icon-button theme-toggle" type="button" :aria-label="themeLabel" :title="themeLabel" @click="toggleTheme"><Sun v-if="colorMode.value === 'dark'" :size="20" /><Moon v-else :size="20" /></button><template #fallback><span class="theme-placeholder" /></template></ClientOnly>
      </nav>
    </header>
    <NuxtLoadingIndicator color="var(--accent)" />
    <NuxtPage :transition="{ name: 'page', mode: 'out-in' }" />
    <footer class="site-footer"><span>Строительный атлас <span class="muted">/ Satisfactory</span></span><span>Планы привязаны к снимку мира. Отметки личные; сохранение игры не меняется.</span></footer>
  </div>
</template>
