<script setup lang="ts">
import * as THREE from 'three'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import type { WorldNode, WorldSite } from '~~/shared/types/world'

const props = defineProps<{ sites: WorldSite[]; nodes: WorldNode[]; bounds: [number, number, number, number]; selected: string }>()
const emit = defineEmits<{ select: [id: string]; unavailable: [] }>()
const host = useTemplateRef<HTMLElement>('host')
let selectSite: ((id: string) => void) | undefined
let cleanup: (() => void) | undefined
let unmounted = false
onBeforeUnmount(() => { unmounted = true; cleanup?.() })
watch(() => props.selected, id => selectSite?.(id))

onMounted(async () => {
  await nextTick()
  if (unmounted) return
  const element = host.value
  if (!element) { emit('unavailable'); return }
  let renderer: THREE.WebGLRenderer
  try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' }) }
  catch { emit('unavailable'); return }
  gsap.registerPlugin(ScrollTrigger)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
  renderer.setClearColor(0x000000, 0)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.domElement.setAttribute('aria-hidden', 'true')
  element.prepend(renderer.domElement)
  const scene = new THREE.Scene()
  const model = new THREE.Group()
  scene.add(model)
  const camera = new THREE.OrthographicCamera(-7, 7, 7, -7, .1, 100)
  const target = new THREE.Vector3()
  camera.position.set(10, 14, 12)
  const light = new THREE.DirectionalLight(0xffffff, 3)
  light.position.set(-5, 12, 6)
  scene.add(light, new THREE.AmbientLight(0xcbd6bd, 2))
  const [minX, maxX, minY, maxY] = props.bounds
  const span = Math.max(maxX - minX, maxY - minY)
  const unit = 10 / span
  const cx = (minX + maxX) / 2
  const cy = (minY + maxY) / 2
  const point = (x: number, y: number) => new THREE.Vector3((x - cx) * unit, 0, (y - cy) * unit)
  const geometries = new Set<THREE.BufferGeometry>()
  const materials = new Set<THREE.Material>()
  const geometry = <T extends THREE.BufferGeometry>(value: T): T => { geometries.add(value); return value }
  const material = <T extends THREE.Material>(value: T): T => { materials.add(value); return value }
  const plateGeometry = geometry(new THREE.BoxGeometry(1, 1, 1))
  const edgeGeometry = geometry(new THREE.EdgesGeometry(plateGeometry))
  const edgeMaterial = material(new THREE.LineBasicMaterial({ color: 0x929c8d, transparent: true, opacity: .65 }))
  const floor = new THREE.Mesh(plateGeometry, material(new THREE.MeshStandardMaterial({ color: 0x343c34, roughness: .9, metalness: .15 })))
  floor.scale.set((maxX - minX) * unit + .8, .14, (maxY - minY) * unit + .8)
  floor.position.y = -.16
  model.add(floor)
  const grid = new THREE.GridHelper(11, 22, 0x8c9984, 0x52604f)
  geometries.add(grid.geometry)
  const gridMaterials = Array.isArray(grid.material) ? grid.material : [grid.material]
  gridMaterials.forEach(value => { value.transparent = true; value.opacity = .38; materials.add(value) })
  grid.position.y = -.075
  model.add(grid)
  const districts = props.sites.map((site, index) => {
    const group = new THREE.Group()
    group.position.copy(point(site.x, site.y))
    const height = .14 + site.tier * .035
    const surface = material(new THREE.MeshStandardMaterial({ color: 0xd8ddcc, roughness: .4, metalness: .35 }))
    const mesh = new THREE.Mesh(plateGeometry, surface)
    mesh.scale.set(site.width * unit, height, site.depth * unit)
    mesh.position.y = height / 2
    mesh.userData.siteId = site.id
    const edges = new THREE.LineSegments(edgeGeometry, edgeMaterial)
    edges.scale.copy(mesh.scale)
    edges.position.copy(mesh.position)
    group.add(mesh, edges)
    model.add(group)
    const label = document.createElement('span')
    label.className = 'scene-district-label'
    label.textContent = String(index + 1).padStart(2, '0')
    label.setAttribute('aria-hidden', 'true')
    element.append(label)
    return { site, group, mesh, surface, label, position: point(site.x, site.y).setY(height + .25) }
  })
  const districtMeshes = districts.map(district => district.mesh)
  const nodeGeometry = geometry(new THREE.CylinderGeometry(.045, .045, .28, 8))
  const nodeMaterial = material(new THREE.MeshStandardMaterial({ color: 0xb5e588, emissive: 0x334420, roughness: .4 }))
  const ringGeometry = geometry(new THREE.RingGeometry(.09, .12, 24))
  const ringMaterial = material(new THREE.MeshBasicMaterial({ color: 0xb5e588, side: THREE.DoubleSide }))
  props.nodes.forEach(node => {
    if (node.xyz_m.length < 2) return
    const pin = new THREE.Mesh(nodeGeometry, nodeMaterial)
    pin.position.copy(point(node.xyz_m[0]!, node.xyz_m[1]!)).setY(.15)
    const ring = new THREE.Mesh(ringGeometry, ringMaterial)
    ring.rotation.x = -Math.PI / 2
    ring.position.copy(pin.position).setY(.005)
    model.add(pin, ring)
  })
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)')
  const fine = window.matchMedia('(hover: hover) and (pointer: fine)')
  let visible = false
  let disposed = false
  let frame = 0
  let started = false
  const projected = new THREE.Vector3()
  const render = () => {
    frame = 0
    if (disposed || !visible || document.hidden) return
    camera.lookAt(target)
    renderer.render(scene, camera)
    districts.forEach(district => {
      projected.copy(district.position)
      model.localToWorld(projected)
      projected.project(camera)
      district.label.style.transform = `translate(${(projected.x * .5 + .5) * element.clientWidth}px,${(-projected.y * .5 + .5) * element.clientHeight}px) translate(-50%,-50%)`
      district.label.style.opacity = String(THREE.MathUtils.clamp(district.group.scale.y, 0, 1))
    })
    element.dataset.rendered = 'true'
  }
  const requestRender = () => { if (!frame && visible && !document.hidden && !disposed) frame = requestAnimationFrame(render) }
  const view = { x: 0, z: 0, zoom: 1 }
  const updateCamera = () => { target.set(view.x, 0, view.z); camera.zoom = view.zoom; camera.updateProjectionMatrix(); requestRender() }
  selectSite = id => {
    const active = districts.find(district => district.site.id === id)
    if (!active) return
    districts.forEach(district => {
      const selected = district === active
      district.label.dataset.selected = String(selected)
      const color = new THREE.Color(selected ? 0xff7439 : 0xd8ddcc)
      gsap.to(district.surface.color, { r: color.r, g: color.g, b: color.b, duration: reduced.matches ? 0 : .45, paused: !visible || document.hidden, overwrite: true, onUpdate: requestRender })
    })
    gsap.to(view, { x: active.position.x * .25, z: active.position.z * .25, zoom: 1.1, duration: reduced.matches ? 0 : .75, paused: !visible || document.hidden, ease: 'power3.out', overwrite: true, onUpdate: updateCamera })
  }
  const assembly = gsap.timeline({ paused: true, onUpdate: requestRender })
  if (!reduced.matches) {
    districts.forEach((district, index) => {
      assembly.from(district.group.position, { y: 1.5 + index * .07, duration: 1, ease: 'power3.out' }, index * .045)
      assembly.from(district.group.scale, { y: .01, duration: .8, ease: 'power3.out' }, index * .045)
    })
  }
  const scroll = ScrollTrigger.create({ trigger: element, start: 'top bottom', end: 'bottom top', onUpdate: trigger => {
    if (reduced.matches || !visible || document.hidden) return
    gsap.to(model.rotation, { y: (trigger.progress - .5) * .12, duration: .5, overwrite: true, onUpdate: requestRender })
  } })
  const tweenTargets = [view, model.rotation, ...districts.map(district => district.surface.color)]
  const animateVisibility = () => {
    const running = visible && !document.hidden
    element.dataset.running = String(running)
    if (running) {
      if (!started) { started = true; assembly.play() }
      else assembly.resume()
      gsap.getTweensOf(tweenTargets).forEach(tween => tween.resume())
      requestRender()
    } else {
      assembly.pause()
      gsap.getTweensOf(tweenTargets).forEach(tween => tween.pause())
      if (frame) cancelAnimationFrame(frame)
      frame = 0
    }
  }
  const observer = new IntersectionObserver(entries => { visible = entries[0]?.isIntersecting ?? false; animateVisibility() }, { threshold: .02 })
  observer.observe(element)
  const resize = new ResizeObserver(() => {
    const width = element.clientWidth
    const height = element.clientHeight
    if (!width || !height) return
    const aspect = width / height
    const halfHeight = aspect < 1 ? 8 : 6.7
    camera.left = -halfHeight * aspect
    camera.right = halfHeight * aspect
    camera.top = halfHeight
    camera.bottom = -halfHeight
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
    requestRender()
  })
  resize.observe(element)
  const raycaster = new THREE.Raycaster()
  const pointer = new THREE.Vector2()
  const hitDistrict = (event: PointerEvent) => {
    const rect = element.getBoundingClientRect()
    pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1)
    raycaster.setFromCamera(pointer, camera)
    return raycaster.intersectObjects(districtMeshes, false)[0]?.object.userData.siteId as string | undefined
  }
  const pointerMove = (event: PointerEvent) => {
    if (!fine.matches || reduced.matches || !visible || document.hidden) return
    const hit = hitDistrict(event)
    gsap.to(model.rotation, { x: pointer.y * .025, z: -pointer.x * .025, duration: .6, overwrite: 'auto', onUpdate: requestRender })
    element.style.cursor = hit ? 'pointer' : 'default'
  }
  const pointerLeave = () => { gsap.to(model.rotation, { x: 0, z: 0, duration: reduced.matches ? 0 : .6, paused: !visible || document.hidden, overwrite: 'auto', onUpdate: requestRender }) }
  const click = (event: PointerEvent) => { const id = hitDistrict(event); if (id) emit('select', id) }
  const motionChange = () => {
    if (reduced.matches) {
      assembly.progress(1).pause()
      gsap.killTweensOf(model.rotation)
      model.rotation.set(0, 0, 0)
    }
    selectSite?.(props.selected)
    requestRender()
  }
  const contextLost = (event: Event) => { event.preventDefault(); emit('unavailable') }
  element.addEventListener('pointermove', pointerMove)
  element.addEventListener('pointerleave', pointerLeave)
  element.addEventListener('click', click)
  renderer.domElement.addEventListener('webglcontextlost', contextLost)
  document.addEventListener('visibilitychange', animateVisibility)
  reduced.addEventListener('change', motionChange)
  selectSite(props.selected)
  cleanup = () => {
    disposed = true
    selectSite = undefined
    if (frame) cancelAnimationFrame(frame)
    observer.disconnect()
    resize.disconnect()
    scroll.kill()
    assembly.kill()
    gsap.killTweensOf([view, model.rotation])
    districts.forEach(district => { gsap.killTweensOf(district.surface.color); district.label.remove() })
    element.removeEventListener('pointermove', pointerMove)
    element.removeEventListener('pointerleave', pointerLeave)
    element.removeEventListener('click', click)
    document.removeEventListener('visibilitychange', animateVisibility)
    reduced.removeEventListener('change', motionChange)
    renderer.domElement.removeEventListener('webglcontextlost', contextLost)
    geometries.forEach(value => value.dispose())
    materials.forEach(value => value.dispose())
    renderer.dispose()
    renderer.forceContextLoss()
    renderer.domElement.remove()
  }
})
</script>

<template>
  <div ref="host" class="world-scene" role="img" aria-label="Объёмная схема реальных районов и ресурсных нод. Выбор района доступен в списке рядом.">
    <div class="scene-corner scene-corner-top" aria-hidden="true"><span>SPATIAL INDEX / X—Y</span><span>СЕВЕР −Y ↗</span></div>
    <div class="scene-corner scene-corner-bottom" aria-hidden="true"><span><i /> Ноды из сейва</span><span>Нажми на площадку</span></div>
  </div>
</template>
