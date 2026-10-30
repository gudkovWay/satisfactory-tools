import type { Asset, Flow, ProjectDocument, TableData } from './project'

export interface WorldRecord {
  id: string
  saveId: string
  title: string
  summary: string
  snapshotAt: string
}
export interface WorldRegistry { schemaVersion: 1; worlds: WorldRecord[] }
export interface WorldSite {
  id: string; label: string; x: number; y: number; width: number; depth: number; tier: number; role: string; verified: boolean; projectId?: string
}
export interface WorldNode {
  id: string; resource: string; purity: string; xyz_m: number[]; hub_distance_m: number; save_actor: string
}
export interface WorldAnalysis {
  worldId: string; saveId: string; saveSha256: string; sourceSha256?: string; dependsOn?: string[]
  id: string; title: string; summary: string
  sections: Array<{ title: string; paragraphs: string[] }>
  sources: Array<{ label: string; url: string }>
  nodes?: WorldNode[]; sites?: WorldSite[]
  tables?: TableData[]; media?: Asset[]
  extractors?: Array<{ id: number; label: string; tier: number }>
  states?: Array<{ miner: number; tier: number; purity: string; clock: number; shards: number; raw: number; ports: number; belt: number; lanes: number; perLane: number; powerMW: number; transportLimited: boolean }>
}
export interface WorldTier {
  id: number; title: string; goal: string; gate: string
  milestones: Array<{ id: string; name: string; cost: Array<{ item: string; amount: number }>; purchased: boolean; optional: boolean }>
  sequence: Array<{ project: string; action: string }>; globals: string[]; factories: string[]; exitChecks: string[]
}
export interface WorldProjectSummary {
  id: string; title: string; tier: number; category: string; stages: number; site: string; powerMW?: number | null; outputs: Flow[]; optional: boolean; revision: string
}
export interface WorldManifest {
  schemaVersion: 1; id: string; saveId: string; title: string; summary: string; saveSha256: string; snapshotAt: string; sourceAnalysisId: string
  analyses: Array<{ id: string; title: string; summary: string; path: string; sha256: string }>
  tiers: WorldTier[]; projects: WorldProjectSummary[]
  presentation: {
    eyebrow: string; intro: string; facts: Array<{ label: string; value: string }>
    architectureTitle: string; architectureBody: string; concept?: Asset
    links: Array<{ label: string; url: string }>
    boundary?: { title: string; body: string; analysisId: string }
    limitations: string
  }
  map?: { nodeAnalysisId: string; siteAnalysisId: string; bounds: [number, number, number, number]; gridMeters: number; north: string; caption: string }
}
export interface WorldContext { record: WorldRecord; manifest: WorldManifest; analyses: WorldAnalysis[] }
export interface WorldProject extends ProjectDocument {
  sitePlan: WorldSite
  extraction?: Array<{ nodeId: string; actor: string; xyz: number[]; miner: number; clock: number; raw: number; ports: number; belt: number; lanes: number; perLane: number; powerMW: number }>
  powerMW?: number
}
