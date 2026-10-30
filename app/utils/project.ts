import type { ProjectKind, ProjectStatus } from '~~/shared/types/project'

export const projectKindLabels: Record<ProjectKind, string> = {
  factory: 'Заводы', road: 'Дороги', depot: 'Депо', warehouse: 'Склады'
}
export const projectStatusLabels: Record<ProjectStatus, string> = {
  blocked: 'Нужно проверить площадку', draft: 'В проектировании', ready: 'Готов к строительству'
}
export function formatRate(value: number, digits = 3) {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: digits }).format(value)
}
