import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import type { ZipEntry } from '../types/signal_digest'

const ACTION_BADGE: Record<string, string> = {
  Model:   'bg-secondary-container text-on-secondary-container',
  Monitor: 'bg-[#fff3cd] text-[#856404]',
  Ignore:  'bg-surface-container text-on-surface-variant',
}

const SIGNAL_LABELS: Record<string, string> = {
  vacancy:      'Vacancy Rate',
  rent:         'Rent Change',
  price_growth: 'Price Growth',
  employment:   'Employment',
  foreclosure:  'Foreclosures',
}

const SIGNAL_SOURCES: Record<string, string> = {
  vacancy:      'RentCast',
  rent:         'RentCast',
  price_growth: 'FHFA',
  employment:   'BLS',
  foreclosure:  'ATTOM',
}

function baseUrl() {
  const raw = (import.meta.env.VITE_TRIGGER_URL as string | undefined) ?? ''
  if (!raw) return ''
  try { return new URL(raw).origin } catch { return '' }
}

function fmt(n: number, suffix = '%') {
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(1)}${suffix}`
}

function scoreColor(s: number) {
  if (s >= 70) return 'text-error'
  if (s >= 40) return 'text-[#d97706]'
  return 'text-secondary'
}

type SignalKey = keyof ZipEntry['signals']

function SignalRow({
  name,
  entry,
  asOf,
}: {
  name: SignalKey
  entry: ZipEntry
  asOf: string
}) {
  const signal = entry.signals[name]
  const isForeclosure = name === 'foreclosure'

  const primaryValue = isForeclosure
    ? `${signal.count ?? 0} filing${signal.count !== 1 ? 's' : ''}`
    : name === 'price_growth'
      ? fmt(signal.annualized ?? signal.value)
      : fmt(signal.value)

  const secondary =
    !isForeclosure && signal.change_30d !== undefined
      ? `${fmt(signal.change_30d)} 30d`
      : name === 'price_growth' && signal.annualized !== undefined
        ? 'annualized'
        : null

  const dateStr = asOf ? new Date(asOf).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: '2-digit' }) : '—'

  return (
    <div
      className={`flex items-center gap-4 px-4 py-3 rounded-lg border transition-colors ${
        signal.flag
          ? 'border-error/30 bg-error-container/20'
          : 'border-outline-variant bg-surface-container-low'
      }`}
    >
      <div
        className="w-2 h-2 rounded-full shrink-0"
        style={{ backgroundColor: signal.flag ? '#ba1a1a' : '#006c49' }}
      />
      <div className="flex-1 min-w-0">
        <p className="text-body-md font-medium text-on-surface">{SIGNAL_LABELS[name]}</p>
        <p className="text-body-md text-on-surface-variant text-[12px]">
          {SIGNAL_SOURCES[name]} · {dateStr}
        </p>
      </div>
      <div className="text-right shrink-0">
        <p className={`text-data-mono font-bold ${signal.flag ? 'text-error' : 'text-on-surface'}`}>
          {primaryValue}
        </p>
        {secondary && <p className="text-[12px] text-on-surface-variant">{secondary}</p>}
      </div>
    </div>
  )
}

const SIGNAL_KEYS: SignalKey[] = ['vacancy', 'rent', 'price_growth', 'employment', 'foreclosure']

const CITATION_METRICS: Record<SignalKey, string> = {
  vacancy:      'Vacancy Rate',
  rent:         'Rent Change (30d)',
  price_growth: 'HPI QoQ Change',
  employment:   'Unemployment Rate',
  foreclosure:  'Foreclosure Filings (90d)',
}

export default function OpportunityDetail() {
  const { zip } = useParams<{ zip: string }>()
  const [entry, setEntry] = useState<ZipEntry | null>(null)
  const [generatedAt, setGeneratedAt] = useState<string>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!zip) return
    const url = baseUrl()
    if (!url) { setLoading(false); return }

    fetch(`${url}/digest`)
      .then(r => r.json())
      .then((data: { zips?: ZipEntry[]; generated_at?: string }) => {
        const match = (data.zips ?? []).find(z => z.zip === zip)
        setEntry(match ?? null)
        setGeneratedAt(data.generated_at ?? '')
      })
      .catch(() => setEntry(null))
      .finally(() => setLoading(false))
  }, [zip])

  if (loading) {
    return (
      <div className="max-w-2xl">
        <Link to="/" className="inline-flex items-center gap-1 text-body-md text-on-surface-variant hover:text-primary mb-6 transition-colors">
          <span className="material-symbols-outlined text-[18px]">arrow_back</span>
          Back to Dashboard
        </Link>
        <div className="flex flex-col items-center justify-center py-20 text-on-surface-variant">
          <span className="material-symbols-outlined text-[48px] mb-4 opacity-30 animate-spin">refresh</span>
          <p className="text-body-lg">Loading brief…</p>
        </div>
      </div>
    )
  }

  if (!entry) {
    return (
      <div className="max-w-2xl">
        <Link to="/" className="inline-flex items-center gap-1 text-body-md text-on-surface-variant hover:text-primary mb-6 transition-colors">
          <span className="material-symbols-outlined text-[18px]">arrow_back</span>
          Back to Dashboard
        </Link>
        <div className="flex flex-col items-center justify-center py-20 text-on-surface-variant">
          <span className="material-symbols-outlined text-[48px] mb-4 opacity-30">search_off</span>
          <p className="text-body-lg font-medium">No data for ZIP {zip}</p>
          <p className="text-body-md mt-1 opacity-70">Run a scoring cycle to generate a brief for this market.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-body-md text-on-surface-variant hover:text-primary mb-6 transition-colors"
      >
        <span className="material-symbols-outlined text-[18px]">arrow_back</span>
        Back to Dashboard
      </Link>

      {/* Header card */}
      <div className="bg-surface-container-lowest border-level-1 rounded-lg shadow-level-2 p-6 mb-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-headline-md text-primary">
              {entry.zip}
              <span className="text-on-surface-variant font-normal ml-2 text-[18px]">
                {entry.city}, {entry.state}
              </span>
            </h1>
            <p className="text-body-md text-on-surface-variant mt-1">
              Generated {generatedAt ? new Date(generatedAt).toLocaleString() : '—'}
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className={`text-display-lg font-bold tabular-nums ${scoreColor(entry.distress_score)}`}>
              {entry.distress_score}
            </p>
            <span className={`text-[10px] px-2 py-0.5 rounded font-bold mt-1 inline-block ${ACTION_BADGE[entry.action] ?? ACTION_BADGE.Ignore}`}>
              {entry.action.toUpperCase()}
            </span>
          </div>
        </div>
      </div>

      {/* Signals */}
      <h2 className="text-label-caps text-on-surface-variant mb-3">SIGNAL BREAKDOWN</h2>
      <div className="flex flex-col gap-2 mb-5">
        {SIGNAL_KEYS.map(name => (
          <SignalRow key={name} name={name} entry={entry} asOf={generatedAt} />
        ))}
      </div>

      {/* Source citations */}
      <h2 className="text-label-caps text-on-surface-variant mb-3">SOURCE CITATIONS</h2>
      <div className="bg-surface-container-lowest border-level-1 rounded-lg shadow-level-2 px-6 py-2 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr>
              <th className="text-left text-label-caps text-on-surface-variant py-3 pr-4 border-b border-outline-variant">PROVIDER</th>
              <th className="text-left text-label-caps text-on-surface-variant py-3 pr-4 border-b border-outline-variant">METRIC</th>
              <th className="text-right text-label-caps text-on-surface-variant py-3 pr-4 border-b border-outline-variant">VALUE</th>
              <th className="text-right text-label-caps text-on-surface-variant py-3 border-b border-outline-variant">DATE</th>
            </tr>
          </thead>
          <tbody>
            {SIGNAL_KEYS.map(name => {
              const sig = entry.signals[name]
              const rawVal = name === 'foreclosure' ? (sig.count ?? 0) : (sig.value)
              const displayVal =
                name === 'foreclosure'
                  ? `${rawVal} filings`
                  : name === 'price_growth'
                    ? fmt(sig.annualized ?? sig.value)
                    : fmt(sig.value)
              const dateStr = generatedAt
                ? new Date(generatedAt).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: '2-digit' })
                : '—'
              return (
                <tr key={name} className="border-t border-outline-variant hover:bg-surface-container-low transition-colors">
                  <td className="py-2.5 pr-4 text-body-md text-on-surface-variant">{SIGNAL_SOURCES[name]}</td>
                  <td className="py-2.5 pr-4 text-body-md text-on-surface">{CITATION_METRICS[name]}</td>
                  <td className="py-2.5 pr-4 text-data-mono text-on-surface text-right">{displayVal}</td>
                  <td className="py-2.5 text-body-md text-on-surface-variant text-right">{dateStr}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
