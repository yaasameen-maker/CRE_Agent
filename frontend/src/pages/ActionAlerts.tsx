import { Link } from 'react-router-dom'
import alertFixture from '../fixtures/action_alert.json'
import type { ActionAlertPayload, Alert } from '../types/action_alert'

const payload = alertFixture as ActionAlertPayload

const ACTION_STYLES: Record<string, { card: string; badge: string }> = {
  Model: {
    card:  'border-red-700 bg-red-950/40',
    badge: 'bg-red-900 text-red-200 border border-red-700',
  },
  Monitor: {
    card:  'border-yellow-700 bg-yellow-950/30',
    badge: 'bg-yellow-900 text-yellow-200 border border-yellow-700',
  },
}

const SIGNAL_LABELS: Record<string, string> = {
  vacancy:      'Vacancy',
  rent:         'Rent',
  price_growth: 'Price Growth',
  employment:   'Employment',
  foreclosure:  'Foreclosure',
}

function AlertCard({ alert }: { alert: Alert }) {
  const styles = ACTION_STYLES[alert.action]
  const scoreColor =
    alert.distress_score >= 70 ? 'text-red-400' :
    alert.distress_score >= 40 ? 'text-yellow-400' : 'text-green-400'

  return (
    <Link
      to={`/brief/${alert.zip}`}
      className={`block rounded-lg border px-5 py-4 hover:brightness-110 transition-all ${styles.card}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-white font-semibold text-lg">{alert.zip}</span>
            <span className={`text-xs px-2 py-0.5 rounded font-medium ${styles.badge}`}>
              {alert.action}
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
              {SIGNAL_LABELS[alert.primary_signal]}
            </span>
          </div>
          <p className="text-slate-300 text-sm leading-snug">{alert.message}</p>
        </div>
        <div className="text-right shrink-0">
          <p className={`text-2xl font-bold tabular-nums ${scoreColor}`}>
            {alert.distress_score}
          </p>
          <p className="text-slate-500 text-xs">distress</p>
        </div>
      </div>
    </Link>
  )
}

export default function ActionAlerts() {
  const modelAlerts   = payload.alerts.filter(a => a.action === 'Model')
  const monitorAlerts = payload.alerts.filter(a => a.action === 'Monitor')

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-white">Action Alerts</h1>
        <p className="text-slate-400 text-sm mt-1">
          Generated {new Date(payload.generated_at).toLocaleString()} · {payload.alerts.length} active alerts
        </p>
      </div>

      {modelAlerts.length > 0 && (
        <section className="mb-6">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-red-400 mb-3">
            Model — Immediate Action
          </h2>
          <div className="flex flex-col gap-3">
            {modelAlerts.map(a => <AlertCard key={a.zip} alert={a} />)}
          </div>
        </section>
      )}

      {monitorAlerts.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-yellow-400 mb-3">
            Monitor — Watch Closely
          </h2>
          <div className="flex flex-col gap-3">
            {monitorAlerts.map(a => <AlertCard key={a.zip} alert={a} />)}
          </div>
        </section>
      )}
    </div>
  )
}
