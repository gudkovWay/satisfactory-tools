import tailwindcss from '@tailwindcss/vite'
import { projectSections, projectUrl, worldUrl } from './app/utils/world-routes'
import type { WorldManifest } from './shared/types/world'
import registry from './public/worlds/index.json'

// The data registry selects manifests; static imports would require code edits for each world.
const worldRoutes = (await Promise.all(registry.worlds.map(async record => {
  const base = worldUrl(record.id)
  const { default: manifest }: { default: WorldManifest } = await import(`./public${base}/manifest.json`, { with: { type: 'json' } })
  return [base, ...manifest.analyses.map(item => `${base}/analysis/${item.id}`), ...manifest.tiers.map(tier => `${base}/tiers/${tier.id}`), ...manifest.projects.flatMap(project => projectSections.map(section => projectUrl(manifest, project.id, section.id)))]
}))).flat()

export default defineNuxtConfig({
  compatibilityDate: '2026-10-22',
  ssr: false,
  telemetry: false,
  devtools: { enabled: false },
  modules: ['@nuxtjs/color-mode'],
  components: [{ path: '~/components', pathPrefix: false, extensions: ['vue'] }],
  vite: { plugins: [tailwindcss()] },
  css: ['~/assets/css/main.css'],
  colorMode: { preference: 'dark', fallback: 'dark', classSuffix: '' },
  app: { head: {
    htmlAttrs: { lang: 'ru' },
    title: 'Строительный атлас Satisfactory',
    meta: [{ name: 'description', content: 'Миры Satisfactory: анализ, архитектура, заводы и пошаговое строительство.' }],
    link: [{ rel: 'preload', href: '/fonts/onest-variable.ttf', as: 'font', type: 'font/ttf', crossorigin: 'anonymous' }]
  } },
  typescript: { strict: true },
  nitro: { prerender: { crawlLinks: true, routes: ['/', '/world', ...worldRoutes] } }
})
