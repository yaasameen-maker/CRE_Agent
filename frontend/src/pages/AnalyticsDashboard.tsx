import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { SignalDigest, ZipEntry } from '../types/signal_digest'
import type { ActionAlertPayload, Alert } from '../types/action_alert'

const TRIGGER_SECRET = import.meta.env.VITE_TRIGGER_SECRET as string | undefined

function baseUrl(raw: string | undefined): string | undefined {
  if (!raw) return undefined
  try { return new URL(raw).origin } catch { return raw }
}
const TRIGGER_URL = baseUrl(import.meta.env.VITE_TRIGGER_URL as string | undefined)

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

function EmptyState({ icon, label }: { icon: string; label: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-on-surface-variant">
      <span className="material-symbols-outlined text-[40px] mb-3 opacity-25">{icon}</span>
      <p className="text-body-md opacity-50">{label}</p>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function KpiCard({
  label, value, sub, trend, subColor, total,
}: {
  label: string; value: string; sub?: string; trend?: string; subColor?: string; total: number
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
          className="h-full bg-secondary rounded-full transition-all duration-500"
          style={{ width: `${Math.min(100, (parseInt(value) / (label === 'AVG. DISTRESS' ? 100 : Math.max(total * 2, 1))) * 100)}%` }}
        />
      </div>
    </div>
  )
}

function BarChart({ zips }: { zips: ZipEntry[] }) {
  if (!zips.length) {
    return (
      <div className="bg-surface-container-lowest border-level-1 rounded-lg shadow-level-2 p-6">
        <h2 className="text-headline-sm text-primary mb-6">Distress Score by ZIP Code</h2>
        <EmptyState icon="bar_chart" label="No scored markets yet" />
      </div>
    )
  }

  const bars = zips.map(z => ({ label: z.zip, score: z.distress_score }))
  const peak = Math.max(...bars.map(b => b.score), 1)

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
        <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
          {[100, 70, 40, 0].map(v => (
            <div key={v} className="flex items-center gap-2">
              <span className="text-[10px] text-outline w-6 text-right shrink-0">{v}</span>
              <div className="flex-1 border-t border-surface-container-high" />
            </div>
          ))}
        </div>
        <div className="flex-1 flex items-end gap-3 pl-8">
          {bars.map(({ label, score }) => {
            const { bar } = scoreColor(score)
            const heightPct = (score / peak) * 100
            return (
              <div key={label} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-data-mono text-on-surface-variant">{score}</span>
                <div className="w-full relative" style={{ height: `${(heightPct / 100) * 160}px` }}>
                  <div className={`absolute inset-0 ${bar} rounded-t opacity-90`} />
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

function AssetTable({ zips }: { zips: ZipEntry[] }) {
  const SIGNAL_LABELS: Record<string, string> = {
    vacancy: 'Vacancy', rent: 'Rent', price_growth: 'Price',
    employment: 'Jobs', foreclosure: 'Fcl.',
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

      {!zips.length ? (
        <EmptyState icon="table_rows" label="Run a cycle to populate market data" />
      ) : (
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
            {zips.map((entry: ZipEntry) => {
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
      )}
    </div>
  )
}

function AiInsightsPanel({ alerts }: { alerts: Alert[] }) {
  const modelOps = alerts.filter((a: Alert) => a.action === 'Model')
  const monitorOps = alerts.filter((a: Alert) => a.action === 'Monitor')

  return (
    <div className="bg-primary-container rounded-lg shadow-level-2 p-6 text-white">
      <div className="flex items-center gap-3 mb-5">
        <span className="material-symbols-outlined text-secondary-fixed text-[22px]">smart_toy</span>
        <h2 className="text-headline-sm">AI Insights Engine</h2>
      </div>
      <div className="space-y-4">
        {!modelOps.length && !monitorOps.length ? (
          <div className="flex flex-col items-center justify-center py-10 text-white/40">
            <span className="material-symbols-outlined text-[36px] mb-3">smart_toy</span>
            <p className="text-body-md text-center">No insights yet — run a cycle to generate AI analysis</p>
          </div>
        ) : (
          <>
            {modelOps.map((alert: Alert) => (
              <div key={alert.zip} className="bg-white/10 p-4 border border-white/15 rounded-lg">
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
              <div key={alert.zip} className="bg-white/10 p-4 border border-white/15 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <span className="material-symbols-outlined text-error text-[18px]">warning</span>
                  <span className="text-label-caps">MARKET SHIFT ALERT</span>
                </div>
                <p className="text-body-md text-on-primary-container">{alert.message}</p>
              </div>
            ))}
          </>
        )}
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
  const [digest, setDigest] = useState<SignalDigest | null>(null)
  const [alertPayload, setAlertPayload] = useState<ActionAlertPayload | null>(null)
  const [syncState, setSyncState] = useState<'idle' | 'running' | 'done' | 'error'>('idle')

  useEffect(() => {
    if (!TRIGGER_URL) return
    const fetchLive = async () => {
      try {
        const [dRes, aRes] = await Promise.all([
          fetch(`${TRIGGER_URL}/digest`),
          fetch(`${TRIGGER_URL}/alerts`),
        ])
        if (dRes.ok) {
          const d = await dRes.json()
          if (d.zips?.length) setDigest(d)
        }
        if (aRes.ok) {
          const a = await aRes.json()
          if (a.alerts?.length) setAlertPayload(a)
        }
      } catch { /* no-op */ }
    }
    fetchLive()
  }, [])

  const zips = digest?.zips ?? []
  const alerts = alertPayload?.alerts ?? []
  const totalMarkets = zips.length
  const modelAlerts = alerts.filter(a => a.action === 'Model').length
  const avgScore = totalMarkets
    ? Math.round(zips.reduce((sum, z) => sum + z.distress_score, 0) / totalMarkets)
    : 0
  const maxScore = totalMarkets ? Math.max(...zips.map(z => z.distress_score)) : 0

  async function handleSync() {
    if (syncState === 'running') return
    if (!TRIGGER_URL || !TRIGGER_SECRET) {
      setSyncState('error')
      setTimeout(() => setSyncState('idle'), 3000)
      return
    }
    setSyncState('running')
    try {
      await fetch(`${TRIGGER_URL}/run?token=${TRIGGER_SECRET}`)
      setSyncState('done')
    } catch {
      setSyncState('error')
    }
    setTimeout(() => setSyncState('idle'), 4000)
  }

  return (
    <div>
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-display-lg text-primary">Market Intelligence Dashboard</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">
            {digest
              ? `AI-scored distress signals for NYC — ${new Date(digest.generated_at).toLocaleDateString('en-US', { dateStyle: 'long' })}`
              : 'AI-scored distress signals for NYC commercial real estate'}
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
            value={totalMarkets ? String(totalMarkets) : '—'}
            sub={digest ? `Run ID: ${digest.run_id.slice(0, 8)}…` : 'No run yet'}
            total={totalMarkets}
          />
        </div>
        <div className="col-span-12 md:col-span-4">
          <KpiCard
            label="MODEL ALERTS"
            value={totalMarkets ? String(modelAlerts) : '—'}
            trend={modelAlerts > 0 ? 'Active' : undefined}
            sub={totalMarkets ? `${alerts.length} total alerts` : 'No run yet'}
            total={totalMarkets}
          />
        </div>
        <div className="col-span-12 md:col-span-4">
          <KpiCard
            label="AVG. DISTRESS"
            value={totalMarkets ? String(avgScore) : '—'}
            sub={totalMarkets ? `Peak: ${maxScore} / 100` : 'No run yet'}
            subColor={avgScore >= 70 ? 'text-error' : avgScore >= 40 ? 'text-[#d97706]' : 'text-secondary'}
            total={totalMarkets}
          />
        </div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-12 gap-5">
        <div className="col-span-12 lg:col-span-8 space-y-5">
          <BarChart zips={zips} />
          <AssetTable zips={zips} />
        </div>
        <div className="col-span-12 lg:col-span-4">
          <AiInsightsPanel alerts={alerts} />
        </div>
      </div>
    </div>
  )
}
