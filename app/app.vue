<script setup lang="ts">
import { Factory, Moon, Sun, FolderOpen } from '@lucide/vue'
const colorMode = useColorMode()
const themeLabel = computed(() => colorMode.value === 'dark' ? 'Светлая тема' : 'Тёмная тема')
function toggleTheme() { colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark' }
</script>

<template>
  <div class="atlas-app">
    <a class="skip-link" href="#main">К содержимому</a>
    <header class="site-header">
      <NuxtLink class="wordmark" to="/" aria-label="Заводской атлас: все проекты"><Factory :size="27" :stroke-width="1.8" aria-hidden="true" /><span><span class="wordmark-title">Заводской атлас</span><span class="wordmark-sub">Satisfactory · личные проекты</span></span></NuxtLink>
      <nav class="global-nav" aria-label="Главная навигация">
        <NuxtLink class="header-link" to="/" aria-label="Мои проекты"><FolderOpen :size="17" aria-hidden="true" /><span>Мои проекты</span></NuxtLink>
        <ClientOnly><button class="icon-button theme-toggle" type="button" :aria-label="themeLabel" :title="themeLabel" @click="toggleTheme"><Sun v-if="colorMode.value === 'dark'" :size="20" /><Moon v-else :size="20" /></button><template #fallback><span class="theme-placeholder" /></template></ClientOnly>
      </nav>
    </header>
    <NuxtLoadingIndicator color="var(--accent)" />
    <NuxtPage :transition="{ name: 'page', mode: 'out-in' }" />
    <footer class="site-footer"><span>Заводской атлас <span class="muted">/ Satisfactory</span></span><span>Планы и личные отметки. Сохранение игры не изменяется.</span></footer>
  </div>
</template>
