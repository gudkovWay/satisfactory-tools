import type { SectionId } from '../../shared/types/project'
import type { WorldManifest } from '../../shared/types/world'

export const projectSections: Array<{ id: SectionId; label: string }> = [
  { id: 'overview', label: 'Обзор' },
  { id: 'build', label: 'Стройка по этапам' },
  { id: 'drawings', label: 'Этажи и чертежи' },
  { id: 'balance', label: 'Рецепты и потоки' },
  { id: 'site', label: 'Площадка и сырьё' },
  { id: 'infrastructure', label: 'Соединения и вывоз' },
  { id: 'parts', label: 'Материалы и детали' },
  { id: 'evidence', label: 'Проверки и данные' }
]
export function worldUrl(worldId: string) {
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(worldId)) throw new Error('Invalid world ID')
  return `/worlds/${worldId}`
}
export function projectUrl(manifest: WorldManifest, projectId: string, section: SectionId = 'overview') {
  const project = manifest.projects.find(item => item.id === projectId)
  if (!project) throw new Error(`Project ${projectId} does not belong to world ${manifest.id}`)
  const base = `${worldUrl(manifest.id)}/tiers/${project.tier}/${project.category}/${project.id}`
  return section === 'overview' ? base : `${base}/${section}`
}
