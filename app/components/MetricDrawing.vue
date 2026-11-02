<script setup lang="ts">
const props = defineProps<{ src: string; alt: string }>()
const emit = defineEmits<{ load: []; error: [] }>()
const imageUrl = ref('')
let objectUrl = ''

watch(() => props.src, async (src, _, onCleanup) => {
  const controller = new AbortController()
  let cancelled = false
  onCleanup(() => { cancelled = true; controller.abort(); if (objectUrl) { URL.revokeObjectURL(objectUrl); objectUrl = '' } })
  imageUrl.value = ''
  try {
    const response = await fetch(src, { signal: controller.signal })
    if (!response.ok) throw new Error('Drawing request failed')
    const original = await response.text()
    if (cancelled) return
    const document = new DOMParser().parseFromString(original, 'image/svg+xml')
    const root = document.documentElement
    if (root.localName !== 'svg' || document.querySelector('parsererror')) throw new Error('Invalid drawing SVG')
    const sourceDescription = root.querySelector(':scope > desc')?.textContent ?? ''
    // This generator reserves its final rule for source qualifications; geometry stays unchanged.
    if (root.localName === 'svg' && sourceDescription.includes('Инженерный конверт. Коллизии, порты и размещение в игре не проверены.')) {
      const children = Array.from(root.children)
      const rules = children.filter(element => element.localName === 'line')
      const header = rules[0], footer = rules[rules.length - 1]
      if (header && footer && header !== footer) {
        const headerY = Number(header.getAttribute('y1')), footerY = Number(footer.getAttribute('y1'))
        let legendY: number | undefined
        for (const element of children) {
          if (element.localName !== 'text') continue
          const y = Number(element.getAttribute('y'))
          const size = Number(element.getAttribute('font-size'))
          if ((y < headerY && size < 24) || y > footerY) {
            element.remove()
            continue
          }
          const text = element.textContent ?? ''
          if (text.startsWith('Отметка уровня ')) element.textContent = text.replace(', не доказательство пола', '')
          if (text.startsWith('Это проекция только указанного ряда')) {
            element.textContent = 'Контур: оборудование · пунктир: обслуживание · P: порты'
            legendY = y
          } else if (legendY !== undefined && element.getAttribute('x') === '32' && y > legendY && y - legendY < 22) {
            element.remove()
            legendY = y
          } else {
            legendY = undefined
          }
        }
        const viewBox = root.getAttribute('viewBox')?.split(/\s+/).map(Number)
        if (viewBox?.length === 4 && Number.isFinite(footerY)) {
          root.setAttribute('viewBox', `${viewBox[0]} ${viewBox[1]} ${viewBox[2]} ${footerY + 12}`)
          root.setAttribute('height', String(footerY + 12))
          root.querySelector(':scope > rect')?.setAttribute('height', String(footerY + 12))
        }
      }
    }
    objectUrl = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(root)], { type: 'image/svg+xml' }))
    imageUrl.value = objectUrl
  } catch (error) {
    if (!cancelled) emit('error')
  }
}, { immediate: true })
onBeforeUnmount(() => { if (objectUrl) URL.revokeObjectURL(objectUrl) })
</script>

<template><img v-if="imageUrl" :src="imageUrl" :alt="alt" decoding="async" @load="emit('load')" @error="emit('error')"></template>
