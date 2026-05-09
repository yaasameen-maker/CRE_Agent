import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { SignalDigest, ZipEntry } from '../types/signal_digest'

const TRIGGER_SECRET = import.meta.env.VITE_TRIGGER_SECRET as string | undefined

function baseUrl(raw: string | undefined): string | undefined {
  if (!raw) return undefined
  try { return new URL(raw).origin } catch { return raw }
}
const TRIGGER_URL = baseUrl(import.meta.env.VITE_TRIGGER_URL as string | undefined)

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true,
  })
}

function nextRun(): string {
  const now = new Date()
  const next = new Date()
  next.setHours(8, 0, 0, 0)
  if (next <= now) next.setDate(next.getDate() + 1)
  return next.toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true,
  })
}

const ACTION_BADGE: Record<string, string> = {
  Model:   'bg-secondary-container text-on-secondary-container',
  Monitor: 'bg-[#fff3cd] text-[#856404]',
  Ignore:  'bg-surface-container text-on-surface-variant',
}

export default function Pipeline() {
  const [running, setRunning] = useState(false)
  const [lastRun, setLastRun] = useState<string | null>(null)
  const [digest, setDigest] = useState<SignalDigest | null>(null)
  const [syncState, setSyncState] = useState<'idle' | 'running' | 'done' | 'error'>('idle')

  useEffect(() => {
    if (!TRIGGER_URL) return

    let wasRunning = false

    const fetchDigest = async () => {
      try {
        const res = await fetch(`${TRIGGER_URL}/digest`)
        if (res.ok) {
          const data = await res.json()
          if (data.zips?.length) setDigest(data)
        }
      } catch { /* no-op */ }
    }

    const pollStatus = async () => {
      try {
        const res = await fetch(`${TRIGGER_URL}/status`)
        if (res.ok) {
          const data = await res.json()
          setRunning(data.running)
          if (data.last_run) setLastRun(data.last_run)
          if (wasRunning && !data.running) fetchDigest()
          wasRunning = data.running
        }
      } catch { /* Railway unreachable */ }
    }

    pollStatus()
    fetchDigest()
    const interval = setInterval(pollStatus, 15000)
    return () => clearInterval(interval)
  }, [])

  async function handleRun() {
    if (syncState === 'running') return
    if (!TRIGGER_URL || !TRIGGER_SECRET) {
      setSyncState('error')
      setTimeout(() => setSyncState('idle'), 3000)
      return
    }
    setSyncState('running')
    setRunning(true)
    try {
      await fetch(`${TRIGGER_URL}/run?token=${TRIGGER_SECRET}`)
      setSyncState('done')
      setTimeout(() => setSyncState('idle'), 4000)
    } catch {
      setSyncState('error')
      setRunning(false)
      setTimeout(() => setSyncState('idle'), 3000)
    }
  }

  const zips: ZipEntry[] = digest?.zips ?? []

  const btnLabel = {
    idle:    'RUN CYCLE NOW',
    running: 'RUNNING...',
    done:    'CYCLE STARTED',
    error:   !TRIGGER_URL ? 'NOT CONFIGURED' : 'ERROR',
  }[syncState]

  return (
    <div>
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-display-lg text-primary">Pipeline Monitor</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">
            Scoring cycle status and run history
          </p>
        </div>
        <button
          onClick={handleRun}
          disabled={syncState === 'running'}
          className={`px-5 py-2 rounded text-label-caps flex items-center gap-2 transition-all ${
            syncState === 'running'
              ? 'bg-surface-container-high text-on-surface-variant cursor-not-allowed'
              : syncState === 'done'
              ? 'bg-secondary text-white opacity-80'
              : syncState === 'error'
              ? 'bg-error text-white'
              : 'bg-secondary text-white hover:opacity-90'
          }`}
        >
          <span className="material-symbols-outlined text-[16px]">
            {syncState === 'running' ? 'hourglass_top' : 'play_arrow'}
          </span>
          {btnLabel}
        </button>
      </div>

      {/* Status cards */}
      <div className="grid grid-cols-12 gap-5 mb-8">
        <div className="col-span-12 md:col-span-4 bg-surface-container-lowest border-level-1 rounded-lg shadow-level-2 p-6">
          <p className="text-label-caps text-on-surface-variant mb-2">AGENT STATUS</p>
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${running ? 'bg-[#d97706] animate-pulse' : 'bg-secondary'}`} />
            <span className="text-display-lg text-primary">{running ? 'Running' : 'Online'}</span>
          </div>
          <p className="text-body-md text-on-surface-variant mt-1">Railway · 8am ET daily</p>
        </div>

        <div className="col-span-12 md:col-span-4 bg-surface-container-lowest border-level-1 rounded-lg shadow-level-2 p-6">
          <p className="text-label-caps text-on-surface-variant mb-2">LAST RUN</p>
          <p className="text-headline-sm text-primary">{formatTime(lastRun ?? digest?.generated_at ?? null)}</p>
          <p className="text-body-md text-on-surface-variant mt-1">
            {digest ? 'Live data' : 'No run yet'}
          </p>
        </div>

        <div className="col-span-12 md:col-span-4 bg-surface-container-lowest border-level-1 rounded-lg shadow-level-2 p-6">
          <p className="text-label-caps text-on-surface-variant mb-2">NEXT SCHEDULED RUN</p>
          <p className="text-headline-sm text-primary">{nextRun()}</p>
          <p className="text-body-md text-on-surface-variant mt-1">Automatic · no action needed</p>
        </div>
      </div>

      {/* Results table */}
      <div className="bg-surface-container-lowest border-level-1 rounded-lg shadow-level-2 overflow-hidden">
        <div className="px-6 py-4 border-b border-outline-variant">
          <h2 className="text-headline-sm text-primary">Last Scored Markets</h2>
        </div>

        {zips.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-on-surface-variant">
            <span className="material-symbols-outlined text-[48px] mb-4 opacity-30">analytics</span>
            <p className="text-body-lg font-medium">No results yet</p>
            <p className="text-body-md mt-1 opacity-70">Run a cycle to generate scored market data</p>
          </div>
        ) : (
          <table className="w-full text-left">
            <thead className="bg-surface-container-low">
              <tr>
                <th className="px-6 py-3 text-label-caps text-on-surface-variant border-b border-outline-variant">ZIP / AREA</th>
                <th className="px-6 py-3 text-label-caps text-on-surface-variant border-b border-outline-variant text-right">SCORE</th>
                <th className="px-6 py-3 text-label-caps text-on-surface-variant border-b border-outline-variant text-center">RANK</th>
                <th className="px-6 py-3 text-label-caps text-on-surface-variant border-b border-outline-variant text-center">ACTION</th>
                <th className="px-6 py-3 text-label-caps text-on-surface-variant border-b border-outline-variant text-right">GATHERED</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant">
              {zips.map((entry: ZipEntry) => (
                <Link key={entry.zip} to={`/brief/${entry.zip}`} className="contents">
                  <tr className="hover:bg-surface-container-low transition-colors cursor-pointer">
                    <td className="px-6 py-3">
                      <p className="text-body-md font-bold text-primary">{entry.zip}</p>
                      <p className="text-body-md text-on-surface-variant">
                        {'neighborhood' in entry ? (entry as { neighborhood?: string }).neighborhood : entry.city},&nbsp;{entry.state}
                      </p>
                    </td>
                    <td className="px-6 py-3 text-right">
                      <span className={`text-data-mono font-bold ${entry.distress_score >= 70 ? 'text-error' : entry.distress_score >= 40 ? 'text-[#d97706]' : 'text-secondary'}`}>
                        {entry.distress_score}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-center">
                      <span className="text-data-mono text-on-surface-variant">#{entry.rank}</span>
                    </td>
                    <td className="px-6 py-3 text-center">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${ACTION_BADGE[entry.action] ?? ACTION_BADGE.Ignore}`}>
                        {entry.action.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-right">
                      <p className="text-body-md text-on-surface tabular-nums">{formatTime(entry.scored_at)}</p>
                    </td>
                  </tr>
                </Link>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
