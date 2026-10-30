import type { ComputedRef, InjectionKey } from 'vue'
import type { WorldAnalysis, WorldContext, WorldManifest, WorldRegistry } from '~~/shared/types/world'
import { worldUrl } from '~/utils/world-routes'

export const worldContextKey: InjectionKey<ComputedRef<WorldContext>> = Symbol('atlas-world')

export function useWorld() {
  const context = inject(worldContextKey)
  if (!context) throw new Error('World components require a selected world context')
  return context
}

export async function loadWorld(worldId: string): Promise<WorldContext> {
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(worldId)) {
    throw createError({ statusCode: 404, statusMessage: 'Мир не найден' })
  }
  const registry = await $fetch<WorldRegistry>('/worlds/index.json')
  const record = registry.worlds.find(item => item.id === worldId)
  if (!record) throw createError({ statusCode: 404, statusMessage: 'Мир не найден' })
  const base = worldUrl(worldId)
  const manifest = await $fetch<WorldManifest>(`${base}/manifest.json`)
  if (manifest.id !== worldId || manifest.saveId !== record.saveId) {
    throw createError({ statusCode: 500, statusMessage: 'Данные мира не соответствуют реестру' })
  }
  const source = manifest.analyses.find(entry => entry.id === manifest.sourceAnalysisId)
  if (!source) throw new Error('World source analysis is missing')
  const analyses = await Promise.all(manifest.analyses.map(async entry => {
    if (entry.path !== `analysis/${entry.id}.json` || !/^[a-z0-9-]+$/.test(entry.id) || !/^[0-9a-f]{64}$/.test(entry.sha256)) throw new Error('Invalid analysis descriptor')
    // Fetch integrity works on the HTTP deployment, unlike secure-context-only SubtleCrypto.
    const integrity = 'sha256-' + btoa(String.fromCharCode(...entry.sha256.match(/../g)!.map(byte => Number.parseInt(byte, 16))))
    const analysis = await $fetch<WorldAnalysis>(`${base}/${entry.path}`, { integrity })
    if (analysis.id !== entry.id || analysis.worldId !== worldId || analysis.saveId !== record.saveId || analysis.saveSha256 !== manifest.saveSha256) throw new Error('Analysis identity differs from selected world')
    if (analysis.id !== manifest.sourceAnalysisId && analysis.sourceSha256 !== source.sha256) throw new Error('Analysis uses a stale source snapshot')
    if (analysis.dependsOn?.some(id => !manifest.analyses.some(entry => entry.id === id))) throw new Error('Unknown analysis dependency')
    return analysis
  }))
  return { record, manifest, analyses }
}
