import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

export function useAtlasMotion() {
  const nuxt = useNuxtApp()
  let media: gsap.MatchMedia | undefined
  let removeHook: (() => void) | undefined
  const setup = () => {
    media?.revert()
    const main = document.querySelector('main')
    if (!main) return
    gsap.registerPlugin(ScrollTrigger)
    media = gsap.matchMedia()
    media.add('screen and (prefers-reduced-motion: no-preference)', () => {
      const title = main.querySelector('h1')
      if (title) {
        const lines = title.querySelectorAll(':scope > span')
        gsap.from(lines.length ? lines : title, { y: 38, opacity: 0, duration: .85, stagger: .1, ease: 'power3.out', clearProps: 'transform,opacity' })
      }
      main.querySelectorAll('.world-section-heading,.world-visual-intro,.atlas-home-note').forEach(section => {
        gsap.from(section, { y: 28, opacity: 0, duration: .8, ease: 'power3.out', clearProps: 'transform,opacity', scrollTrigger: { trigger: section, start: 'top 94%', once: true } })
      })
      const feature = main.querySelector('.world-feature-image img')
      if (feature) gsap.from(feature, { clipPath: 'inset(0 0 100% 0)', duration: 1.1, ease: 'power3.inOut', clearProps: 'clipPath' })
    }, main)
  }
  onMounted(() => { setup(); removeHook = nuxt.hook('page:finish', setup) })
  onBeforeUnmount(() => { removeHook?.(); media?.revert() })
}
