export default defineNuxtPlugin({
  name: 'atlas-stable-query-scroll',
  dependsOn: ['nuxt:router'],
  setup(nuxtApp) {
    const router = useRouter()
    // Nuxt restores its native policy during app:created, before this boundary.
    nuxtApp.hook('app:mounted', () => {
      const original = router.options.scrollBehavior
      router.options.scrollBehavior = (to, from, savedPosition) => {
        const keys = to.params.analysis ? ['topic'] : to.params.project ? ['stage', 'drawing', 'view', 'zone'] : []
        if (to.path === from.path && keys.some(key => to.query[key] !== from.query[key])) return savedPosition ?? false
        return original?.(to, from, savedPosition)
      }
    })
  },
})
