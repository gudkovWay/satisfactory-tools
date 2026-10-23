import type { ProjectDocument, ProjectIndex, SaveRegistry } from '~~/shared/types/project'

export function useProjectCatalogue() {
  const projects = useFetch<ProjectIndex>('/atlas/projects.json', { key: 'atlas-projects', lazy: true })
  const saves = useFetch<SaveRegistry>('/atlas/saves.json', { key: 'atlas-saves', lazy: true })
  return { projects, saves }
}

export function useProjectDocument(saveId: string, projectId: string) {
  const valid = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
  if (!valid.test(saveId) || !valid.test(projectId)) {
    throw createError({ statusCode: 404, statusMessage: 'Проект не найден' })
  }
  return useFetch<ProjectDocument>(`/atlas/${saveId}/${projectId}/project.json`, {
    key: `atlas-project:${saveId}:${projectId}`, lazy: true
  })
}
