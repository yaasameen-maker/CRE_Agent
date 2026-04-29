import type { Action } from './signal_digest'

export interface Alert {
  zip: string
  action: Action
  distress_score: number
  primary_signal: 'vacancy' | 'rent' | 'price_growth' | 'employment' | 'foreclosure'
  brief_id: string
  message: string
}

export interface ActionAlertPayload {
  generated_at: string
  alerts: Alert[]
}
