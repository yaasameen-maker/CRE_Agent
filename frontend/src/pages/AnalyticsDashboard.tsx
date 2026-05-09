import { useState } from 'react'
import { Link } from 'react-router-dom'
import digestFixture from '../fixtures/signal_digest.json'
import alertFixture from '../fixtures/action_alert.json'
import type { SignalDigest, ZipEntry } from '../types/signal_digest'
import type { ActionAlertPayload, Alert } from '../types/action_alert'

const TRIGGER_URL = import.meta.env.VITE_TRIGGER_URL as string | undefined
const TRIGGER_SECRET = import.meta.env.VITE_TRIGGER_SECRET as string | undefined

const digest = digestFixture as unknown as SignalDigest
const alertPayload = alertFixture as ActionAlertPayload

// ── Derived KPIs ──────────────────────────────────────────────────────────────

const totalMarkets = digest.zips.length
const modelAlerts = alertPayload.alerts.filter(a => a.action === 'Model').length
const avgScore = Math.round(
  digest.zips.reduce((sum, z) => sum + z.distress_score, 0) / totalMarkets
)
const maxScore = Math.max(...digest.zips.map(z => z.distress_score))

// ── Helpers ───────────────────────────────────────────────────────────────────

const ACTION_BADGE: Record<string, string> = {
  Model:   'bg-secondary-container text-on-secondary-container',
  Monitor: 'bg-[#fff3cd] text-[#856404]',
  Ignore:  'bg-surface-container text-on-surface-variant',
}

function scoreColor(s: number) {
  if (s >= 70) return { bar: 'bg-error', text: 'text-error' }
  if (s >= 40) return { bar: 'bg-[#d97706]', text: 'text-[#d97706]' }
  return { bar: 'bg-secondary', text: 'text-secondary' }
}

// ── Sub-components ────────────────────────────────────────────────────────────

function KpiCard({
  label, value, sub, trend, subColor,
}: {
  label: string
  value: string
  sub?: string
  trend?: string
  subColor?: string
}) {
  return (
    <div className="bg-surface-container-lowest p-6 border-level-1 rounded-lg shadow-level-2">
      <p className="text-label-caps text-on-surface-variant mb-2">{label}</p>
      <div className="flex items-baseline gap-2">
        <span className="text-display-lg text-primary">{value}</span>
        {trend && (
          <span className="text-body-md font-bold text-secondary flex items-center gap-0.5">
            <span className="material-symbols-outlined text-[18px]">arrow_drop_up</span>
            {trend}
          </span>
        )}
      </div>
      {sub && (
        <p className={`text-body-md mt-1 ${subColor ?? 'text-on-surface-variant'}`}>{sub}</p>
      )}
      <div className="mt-3 h-1 bg-surface-container-low rounded-full overflow-hidden">
        <div
          className="h-full bg-secondary rounded-full"
          style={{ width: `${Math.min(100, (parseInt(value) / (label === 'AVG. DISTRESS' ? 100 : totalMarkets * 2)) * 100)}%` }}
        />
      </div>
    </div>
  )
}

function BarChart() {
  const bars = digest.zips.map(z => ({
    label: z.zip,
    score: z.distress_score,
  }))
  const peak = Math.max(...bars.map(b => b.score))

  return (
    <div className="bg-surface-container-lowest border-level-1 rounded-lg shadow-level-2 p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-headline-sm text-primary">Distress Score by ZIP Code</h2>
        <div className="flex gap-4">
          <span className="flex items-center gap-1.5 text-label-caps text-on-surface-variant">
            <span className="w-3 h-3 rounded-full bg-primary-container inline-block" />
            SCORE
          </span>
          <span className="flex items-center gap-1.5 text-label-caps text-on-surface-variant">
            <span className="w-3 h-3 rounded-full bg-secondary inline-block" />
            THRESHOLD (70)
          </span>
        </div>
      </div>

      <div className="h-48 flex items-end gap-4 relative">
        {/* Grid lines */}
        <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
          {[100, 70, 40, 0].map(v => (
            <div key={v} className="flex items-center gap-2">
              <span className="text-[10px] text-outline w-6 text-right shrink-0">{v}</span>
              <div className="flex-1 border-t border-surface-container-high" />
            </div>
          ))}
        </div>

        {/* Bars */}
        <div className="flex-1 flex items-end gap-3 pl-8">
          {bars.map(({ label, score }) => {
            const { bar } = scoreColor(score)
            const heightPct = (score / peak) * 100
            return (
              <div key={label} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-data-mono text-on-surface-variant">{score}</span>
                <div className="w-full relative" style={{ height: `${(heightPct / 100) * 160}px` }}>
                  <div className={`absolute inset-0 ${bar} rounded-t opacity-90`} />
                  {/* model threshold line */}
                  {score >= 70 && (
                    <div className="absolute bottom-0 left-0 right-0 border-t-2 border-secondary opacity-50" />
                  )}
                </div>
                <span className="text-[10px] text-outline">{label}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function AssetTable() {
  const SIGNAL_LABELS: Record<string, string> = {
    vacancy: 'Vacancy',
    rent: 'Rent',
    price_growth: 'Price',
    employment: 'Jobs',
    foreclosure: 'Fcl.',
  }

  return (
    <div className="bg-surface-container-lowest border-level-1 rounded-lg shadow-level-2 overflow-hidden">
      <div className="px-6 py-4 border-b border-outline-variant flex justify-between items-center">
        <h2 className="text-headline-sm text-primary">Market Digest</h2>
        <div className="flex gap-2">
          <button className="p-1.5 hover:bg-surface-container-low rounded">
            <span className="material-symbols-outlined text-on-surface-variant text-[20px]">filter_list</span>
          </button>
          <button className="p-1.5 hover:bg-surface-container-low rounded">
            <span className="material-symbols-outlined text-on-surface-variant text-[20px]">download</span>
          </button>
        </div>
      </div>

      <table className="w-full text-left">
        <thead className="bg-surface-container-low">
          <tr>
            <th className="px-6 py-3 text-label-caps text-on-surface-variant border-b border-outline-variant">ZIP / AREA</th>
            <th className="px-6 py-3 text-label-caps text-on-surface-variant border-b border-outline-variant text-right">DISTRESS</th>
            <th className="px-6 py-3 text-label-caps text-on-surface-variant border-b border-outline-variant text-center">ACTION</th>
            <th className="px-6 py-3 text-label-caps text-on-surface-variant border-b border-outline-variant">SIGNALS</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant">
          {digest.zips.map((entry: ZipEntry) => {
            const flagged = Object.entries(entry.signals)
              .filter(([, s]) => s.flag)
              .map(([k]) => SIGNAL_LABELS[k])
            const { text } = scoreColor(entry.distress_score)

            return (
              <tr key={entry.zip} className="hover:bg-surface-container-low transition-colors">
                <td className="px-6 py-3">
                  <Link to={`/brief/${entry.zip}`} className="hover:underline">
                    <p className="text-body-md font-bold text-primary">{entry.zip}</p>
                    <p className="text-body-md text-on-surface-variant">
                      {'neighborhood' in entry ? (entry as { neighborhood?: string }).neighborhood : entry.city}, {entry.state}
                    </p>
                  </Link>
                </td>
                <td className="px-6 py-3 text-right">
                  <span className={`text-data-mono font-bold ${text}`}>{entry.distress_score}</span>
                </td>
                <td className="px-6 py-3 text-center">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${ACTION_BADGE[entry.action] ?? ACTION_BADGE.Ignore}`}>
                    {entry.action.toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-3">
                  <div className="flex flex-wrap gap-1">
                    {flagged.map(f => (
                      <span key={f} className="text-[10px] px-1.5 py-0.5 bg-error-container text-error rounded font-medium">
                        {f}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function AiInsightsPanel() {
  const modelOps = alertPayload.alerts.filter((a: Alert) => a.action === 'Model')
  const monitorOps = alertPayload.alerts.filter((a: Alert) => a.action === 'Monitor')

  return (
    <div className="bg-primary-container rounded-lg shadow-level-2 p-6 text-white">
      <div className="flex items-center gap-3 mb-5">
        <span className="material-symbols-outlined text-secondary-fixed text-[22px]">smart_toy</span>
        <h2 className="text-headline-sm">AI Insights Engine</h2>
      </div>

      <div className="space-y-4">
        {modelOps.map((alert: Alert) => (
          <div
            key={alert.zip}
            className="bg-white/10 p-4 border border-white/15 rounded-lg"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="material-symbols-outlined text-secondary-fixed text-[18px]">trending_up</span>
              <span className="text-label-caps">OPPORTUNITY DETECTED</span>
            </div>
            <p className="text-body-md text-on-primary-container mb-3">{alert.message}</p>
            <Link
              to={`/brief/${alert.zip}`}
              className="block w-full text-center py-1.5 bg-secondary text-white text-label-caps rounded hover:bg-on-secondary-container transition-colors"
            >
              VIEW ANALYSIS
            </Link>
          </div>
        ))}

        {monitorOps.map((alert: Alert) => (
          <div
            key={alert.zip}
            className="bg-white/10 p-4 border border-white/15 rounded-lg"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="material-symbols-outlined text-error text-[18px]">warning</span>
              <span className="text-label-caps">MARKET SHIFT ALERT</span>
            </div>
            <p className="text-body-md text-on-primary-container">{alert.message}</p>
          </div>
        ))}

        {/* Accuracy meter */}
        <div className="pt-4 border-t border-white/15">
          <div className="flex justify-between items-center mb-2">
            <span className="text-label-caps text-on-primary-container">PROCESSING ACCURACY</span>
            <span className="text-data-mono text-secondary-fixed font-bold">99.4%</span>
          </div>
          <div className="h-1 bg-white/20 rounded-full overflow-hidden">
            <div className="w-[99%] h-full bg-secondary-fixed" />
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AnalyticsDashboard() {
  const [syncState, setSyncState] = useState<'idle' | 'running' | 'done' | 'error'>('idle')

  async function handleSync() {
    if (syncState === 'running') return
    if (!TRIGGER_URL || !TRIGGER_SECRET) {
      setSyncState('error')
      setTimeout(() => setSyncState('idle'), 3000)
      return
    }
    setSyncState('running')
    try {
      await fetch(`${TRIGGER_URL}?token=${TRIGGER_SECRET}`)
      setSyncState('done')
    } catch {
      setSyncState('error')
    }
    setTimeout(() => setSyncState('idle'), 4000)
  }

  return (
    <div>
      {/* Page header */}
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-display-lg text-primary">Market Intelligence Dashboard</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">
            AI-scored distress signals for NYC commercial real estate — {new Date(digest.generated_at).toLocaleDateString('en-US', { dateStyle: 'long' })}
          </p>
        </div>
        <div className="flex gap-3">
          <button className="px-5 py-2 border border-outline-variant rounded text-label-caps bg-white hover:bg-surface-container-low transition-colors">
            EXPORT DATA
          </button>
          <button
            onClick={handleSync}
            disabled={syncState === 'running'}
            className="px-5 py-2 bg-secondary text-white rounded text-label-caps flex items-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <span className={`material-symbols-outlined text-[16px] ${syncState === 'running' ? 'animate-spin' : ''}`}>
              refresh
            </span>
            {syncState === 'running' ? 'RUNNING...' : syncState === 'done' ? 'CYCLE STARTED' : syncState === 'error' ? 'NOT CONFIGURED' : 'SYNC LIVE FEEDS'}
          </button>
        </div>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-12 gap-5 mb-8">
        <div className="col-span-12 md:col-span-4">
          <KpiCard
            label="MARKETS SCORED"
            value={String(totalMarkets)}
            sub={`Run ID: ${digest.run_id.slice(0, 8)}…`}
          />
        </div>
        <div className="col-span-12 md:col-span-4">
          <KpiCard
            label="MODEL ALERTS"
            value={String(modelAlerts)}
            trend="Active"
            sub={`${alertPayload.alerts.length} total alerts`}
          />
        </div>
        <div className="col-span-12 md:col-span-4">
          <KpiCard
            label="AVG. DISTRESS"
            value={String(avgScore)}
            sub={`Peak: ${maxScore} / 100`}
            subColor={avgScore >= 70 ? 'text-error' : avgScore >= 40 ? 'text-[#d97706]' : 'text-secondary'}
          />
        </div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-12 gap-5">
        {/* Left: chart + table */}
        <div className="col-span-12 lg:col-span-8 space-y-5">
          <BarChart />
          <AssetTable />
        </div>

        {/* Right: AI panel */}
        <div className="col-span-12 lg:col-span-4">
          <AiInsightsPanel />
        </div>
      </div>
    </div>
  )
}
