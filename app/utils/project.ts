import type { ProjectKind, ProjectStatus, SectionId } from '../../shared/types/project'

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
export const projectKindLabels: Record<ProjectKind, string> = {
  factory: 'Заводы', road: 'Дороги', depot: 'Депо', warehouse: 'Склады'
}
export const projectStatusLabels: Record<ProjectStatus, string> = {
  blocked: 'Нужно проверить площадку', draft: 'В проектировании', ready: 'Готов к строительству'
}
export function formatRate(value: number, digits = 3) {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: digits }).format(value)
}
export function projectUrl(saveId: string, projectId: string, section: SectionId = 'overview') {
  const base = `/projects/${saveId}/${projectId}`
  return section === 'overview' ? base : `${base}/${section}`
}
