import type { Action } from './signal_digest'

export interface BriefSignalValue {
  value: number
  change_30d?: number
  annualized?: number
  count?: number
  flag: boolean
  source: string
  as_of: string
}

export interface BriefSignals {
  vacancy: BriefSignalValue
  rent: BriefSignalValue
  price_growth: BriefSignalValue
  employment: BriefSignalValue
  foreclosure: BriefSignalValue
}

export interface SourceCitation {
  source: string
  metric: string
  value: number
  date: string
}

export interface OpportunityBrief {
  brief_id: string
  zip: string
  city: string
  state: string
  generated_at: string
  distress_score: number
  action: Action
  summary: string
  signals: BriefSignals
  source_citations: SourceCitation[]
}
