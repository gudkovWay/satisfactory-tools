import tailwindcss from '@tailwindcss/vite'
import catalogue from './public/atlas/projects.json'
import { projectSections, projectUrl } from './app/utils/project'

const projectRoutes = catalogue.projects.flatMap(project => projectSections.map(section => projectUrl(project.saveId, project.id, section.id)))

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
  app: {
    head: {
      htmlAttrs: { lang: 'ru' },
      title: 'Заводской атлас',
      meta: [{ name: 'description', content: 'Проекты и пошаговые инструкции для мира Satisfactory.' }],
      link: [{ rel: 'preload', href: '/fonts/onest-variable.ttf', as: 'font', type: 'font/ttf', crossorigin: 'anonymous' }],
    }
  },
  typescript: { strict: true },
  nitro: { prerender: { crawlLinks: true, routes: ['/', ...projectRoutes] } }
})
