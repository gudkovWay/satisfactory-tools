import type { ProjectDocument } from '~~/shared/types/project'

export function useConstructionUnits(project: MaybeRefOrGetter<ProjectDocument>) {
  const blockGrid = computed(() => toValue(project).parts.items.some(part =>
    part.code === 'FND' && part.recipeKey === 'Recipe_Concrete_Block_8x8x2_C'
  ))
  const horizontal = (value: number) => formatRate(value / (blockGrid.value ? 8 : 1), 4)
  const vertical = (value: number) => formatRate(value / (blockGrid.value ? 2 : 1), 4)
  const floorHeight = (value: number) => blockGrid.value ? `H${vertical(value)} слоёв CC Block` : `${vertical(value)} м`
  const coordinateLabel = computed(() => blockGrid.value ? 'X / Y, ф.; H, сл.' : 'X / Y / Z, м')
  return { blockGrid, horizontal, vertical, floorHeight, coordinateLabel }
}
