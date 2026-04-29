export type Action = 'Model' | 'Monitor' | 'Ignore'

export interface SignalValue {
  value: number
  change_30d?: number
  annualized?: number
  count?: number
  flag: boolean
}

export interface ZipSignals {
  vacancy: SignalValue
  rent: SignalValue
  price_growth: SignalValue
  employment: SignalValue
  foreclosure: SignalValue
}

export interface ZipEntry {
  zip: string
  city: string
  state: string
  distress_score: number
  rank: number
  action: Action
  signals: ZipSignals
  brief_id: string
}

export interface SignalDigest {
  generated_at: string
  run_id: string
  zips: ZipEntry[]
}
