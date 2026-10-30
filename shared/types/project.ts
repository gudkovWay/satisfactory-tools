export type ProjectKind = 'factory' | 'road' | 'depot' | 'warehouse'
export type ProjectStatus = 'draft' | 'blocked' | 'ready'
export type EvidenceStatus = 'verified' | 'unverified' | 'blocked' | 'not-applicable'
export type SectionId = 'overview' | 'build' | 'drawings' | 'balance' | 'site' | 'infrastructure' | 'parts' | 'evidence'

export interface SaveRecord {
  id: string
  name: string
  sessionName: string
  sourceLabel: string
  sourceSha256: string
  snapshotAt: string
  modCount: number
}

export interface SaveRegistry { schemaVersion: 1; saves: SaveRecord[] }
export interface ProjectTarget { itemId: string; label: string; rate: number; unit: string }
export interface Asset { src: string; alt: string; caption: string; kind: 'schematic' | 'concept' | 'game-render' | 'map' | 'reference' }
export interface ProjectSummary {
  id: string
  saveId: string
  kind: ProjectKind
  title: string
  subtitle: string
  revision: string
  updatedAt: string
  status: ProjectStatus
  target?: ProjectTarget
  preview?: Asset
  drawingCount: number
  zoneCount?: number
}
export interface ProjectIndex { schemaVersion: 1; projects: ProjectSummary[] }
export interface Evidence { id: string; label: string; status: EvidenceStatus; detail: string; source?: string }
export interface ContentNote { title: string; body: string }
export interface TableData { caption: string; columns: string[]; rows: string[][] }
export interface Decision { choice: string; instead: string; reason: string; tradeoff: string }
export interface Flow { itemId: string; label: string; rate: number; unit: string; exact?: string }
export interface Process {
  id: string
  recipeKey: string
  recipePath: string
  recipeName: string
  machineKind: string
  machineName: string
  machines: number
  clock: number
  clockFraction?: string
  speedMultiplier: number
  durationSeconds: number
  cyclesPerMinute: number
  cyclesFraction?: string
  inputs: Flow[]
  outputs: Flow[]
  note: string
}
export interface RecipeVariant {
  key: string
  path: string
  name: string
  inputs: Flow[]
  byproducts: Flow[]
  outputAtFullClock: number
  machineKind: string
  selected: boolean
}
export interface RecipeComparison { itemId: string; label: string; variants: RecipeVariant[] }
export interface ProductionPlan {
  targetItemId: string
  targetRate: number
  targets?: ProjectTarget[]
  recipesFile: string
  recipesSha256: string
  rawInputs: Flow[]
  disposal: Flow[]
  processes: Process[]
  comparisons: RecipeComparison[]
  scenarios: TableData
  notes: string[]
  normalizedRecipeCount: number
  candidateRecipeCount: number
}
export interface Level { id: string; name: string; z: number; type: string; purpose: string }
export interface Placement {
  id: string
  processId: string
  levelId: string
  x: number
  y: number
  z: number
  kind: string
  clock: number
  width: number
  depth: number
  height: number
}
export interface Drawing {
  id: string
  family: 'floors' | 'volumes' | 'technical' | 'facades' | 'assembly'
  label: string
  caption: string
  levelId?: string
  svg: string
  png?: string
}
export interface GuideStep {
  id: string
  title: string
  body: string
  prerequisites: string[]
  actions: string[]
  materials: string[]
  checks: string[]
  levelIds: string[]
  drawingIds: string[]
  zoneIds?: string[]
}
export interface Stream {
  id: string
  itemId: string
  label: string
  from: string[]
  to: string
  rate: number
  fluid: boolean
  capacity: number
  lanes: number
}
export interface MapFeed {
  id: string
  itemId: string
  nodeId?: string
  locationRole?: 'waterbody-reference'
  label: string
  x: number
  y: number
  z: number
  required: number
  capacity: number
  clock: number
  purity: string
  note: string
}
export interface ProtectedExtractor {
  id: string
  label: string
  node: string
  x: number
  y: number
  z: number
  nominal?: number
  clock?: number
}
export interface MapScale { id: string; label: string; bounds: [number, number, number, number] }
export interface ProjectMap {
  terrain: Asset
  worldBounds: [number, number, number, number]
  scales: MapScale[]
  site: { x: number; y: number; baseZ: number; origin: [number, number]; width: number; depth: number; label: string }
  hub: number[]
  railPoints: number[][]
  protectedBox: [number, number, number, number]
  protectedFactoryBounds: [number, number, number, number]
  protectedExtractors: ProtectedExtractor[]
  withdrawnMarker: { x: number; y: number; z: number; label: string }
  feeds: MapFeed[]
  notes: ContentNote[]
  tables: TableData[]
}
export interface Part { code: string; name: string; recipeKey: string; recipePath: string; mod: string; role: string; quantity: string; availability: string }
export interface ZoneGroup {
  processId: string
  machines: number
  inputs: Flow[]
  outputs: Flow[]
}
export interface ZoneView {
  id: string
  levelId: string
  title: string
  scope: string
  variance: string
  image: Asset
  sheet: Asset
  position?: Asset
  width: number
  height: number
  actions: string[]
  network: string
  partCodes: string[]
  referenceIds: string[]
  placementIds: string[]
  ownsProduction: boolean
  groups: ZoneGroup[]
}
export interface ZoneAtlas {
  title: string
  engineeringSha256: string
  fidelity: string
  levels: Array<{ id: string; name: string; z: number | null; type: string; purpose?: string }>
  views: ZoneView[]
  references: Array<{ id: string; name: string; image: Asset; sourceUrl: string; sha256: string }>
}
export interface ProjectDocument extends ProjectSummary {
  schemaVersion: 1
  progressRevision?: string
  progressSignature?: string
  source: { saveSha256: string; snapshotLabel: string; recipeSha256?: string; modSnapshotSha256?: string; sourceSession?: string; planSha256?: string; snapshotAt?: string; planning?: { mode: 'forecast'; tier: number; density: number; prerequisites: string[] } }
  dependencies: Array<{ saveId: string; projectId: string; role: string }>
  readiness: { constructionReady: boolean; blockers: string[] }
  overview: { paragraphs: string[]; decisions: Decision[]; concept?: Asset }
  build: { steps: GuideStep[]; commissioning: string[]; notes: string[] }
  drawings: Drawing[]
  zoneAtlas?: ZoneAtlas
  levels: Level[]
  placements: Placement[]
  production?: ProductionPlan
  map?: ProjectMap
  infrastructure: { notes: ContentNote[]; tables: TableData[]; diagrams: Asset[]; streams: Stream[] }
  parts: { items: Part[]; notes: ContentNote[]; facade?: Asset }
  evidence: { items: Evidence[]; notes: string[]; sources: Array<{ label: string; url: string }>; downloads: Array<{ label: string; path: string }> }
}
