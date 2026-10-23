import type { ProjectDocument } from '~~/shared/types/project'

export function useProjectProgress(project: ProjectDocument) {
  const key = `factory-progress:${project.saveId}:${project.id}:${project.revision}`
  const completed = useState<string[]>(key, () => [])
  const storageError = ref<string | null>(null)
  const validIds = new Set([
    ...project.build.steps.map(step => step.id),
    ...project.build.commissioning.map((_, index) => `check-${String(index + 1).padStart(2, '0')}`)
  ])
  onMounted(() => {
    try {
      const stored: unknown = JSON.parse(localStorage.getItem(key) || '[]')
      completed.value = Array.isArray(stored) ? stored.filter((id): id is string => typeof id === 'string' && validIds.has(id)) : []
    } catch {
      storageError.value = 'Не удалось прочитать отметки. Новые отметки доступны до закрытия страницы.'
    }
  })
  function persist() {
    try { localStorage.setItem(key, JSON.stringify(completed.value)) }
    catch { storageError.value = 'Браузер запретил сохранение отметок. Они доступны только в этой вкладке.' }
  }
  function toggle(id: string) {
    if (!validIds.has(id)) return
    completed.value = completed.value.includes(id) ? completed.value.filter(value => value !== id) : [...completed.value, id]
    if (import.meta.client) persist()
  }
  function reset() { completed.value = []; if (import.meta.client) persist() }
  return { completed, isComplete: (id: string) => completed.value.includes(id), toggle, reset, storageError }
}
