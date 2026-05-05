import { Link } from 'react-router-dom'
import briefFixture from '../fixtures/opportunity_brief.json'
import type { OpportunityBrief, BriefSignalValue, SourceCitation } from '../types/opportunity_brief'

const brief = briefFixture as OpportunityBrief

const ACTION_STYLES: Record<string, string> = {
  Model:   'bg-red-900 text-red-200 border border-red-700',
  Monitor: 'bg-yellow-900 text-yellow-200 border border-yellow-700',
  Ignore:  'bg-slate-800 text-slate-400 border border-slate-700',
}

const SIGNAL_LABELS: Record<string, string> = {
  vacancy:      'Vacancy Rate',
  rent:         'Rent Change',
  price_growth: 'Price Growth',
  employment:   'Employment',
  foreclosure:  'Foreclosures',
}

function fmt(n: number, suffix = '%') {
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(1)}${suffix}`
}

function SignalRow({ name, signal }: { name: string; signal: BriefSignalValue }) {
  const isForeclosure = name === 'foreclosure'

  const primaryValue = isForeclosure
    ? `${signal.count} filing${signal.count !== 1 ? 's' : ''}`
    : name === 'price_growth'
      ? fmt(signal.annualized ?? signal.value)
      : fmt(signal.value)

  const secondary = !isForeclosure && signal.change_30d !== undefined
    ? `${fmt(signal.change_30d)} 30d`
    : name === 'price_growth' && signal.annualized !== undefined
      ? 'annualized'
      : null

  return (
    <div className={`rounded-lg border px-4 py-3 flex items-center gap-4 ${
      signal.flag
        ? 'border-red-800 bg-red-950/30'
        : 'border-slate-700 bg-slate-900'
    }`}>
      <div className="w-2 h-2 rounded-full shrink-0 mt-0.5" style={{
        backgroundColor: signal.flag ? '#ef4444' : '#22c55e',
      }} />
      <div className="flex-1 min-w-0">
        <p className="text-slate-300 text-sm font-medium">{SIGNAL_LABELS[name]}</p>
        <p className="text-slate-500 text-xs">{signal.source} · {signal.as_of}</p>
      </div>
      <div className="text-right shrink-0">
        <p className={`font-semibold tabular-nums ${signal.flag ? 'text-red-400' : 'text-slate-200'}`}>
          {primaryValue}
        </p>
        {secondary && (
          <p className="text-slate-500 text-xs">{secondary}</p>
        )}
      </div>
    </div>
  )
}

function CitationRow({ c }: { c: SourceCitation }) {
  return (
    <tr className="border-t border-slate-800">
      <td className="py-2 pr-4 text-slate-400 text-sm">{c.source}</td>
      <td className="py-2 pr-4 text-slate-300 text-sm">{c.metric}</td>
      <td className="py-2 pr-4 text-slate-200 text-sm tabular-nums text-right">{c.value}</td>
      <td className="py-2 text-slate-500 text-sm text-right">{c.date}</td>
    </tr>
  )
}

export default function OpportunityDetail() {
  const scoreColor =
    brief.distress_score >= 70 ? 'text-red-400' :
    brief.distress_score >= 40 ? 'text-yellow-400' : 'text-green-400'

  return (
    <div className="max-w-2xl">
      <Link to="/" className="text-slate-400 text-sm hover:text-white mb-6 inline-block">
        ← Back to Digest
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-white">
            {brief.zip}
            <span className="text-slate-400 font-normal ml-2 text-lg">
              {brief.city}, {brief.state}
            </span>
          </h1>
          <p className="text-slate-500 text-xs mt-1">
            Generated {new Date(brief.generated_at).toLocaleString()}
          </p>
        </div>
        <div className="text-right shrink-0">
          <p className={`text-4xl font-bold tabular-nums ${scoreColor}`}>
            {brief.distress_score}
          </p>
          <span className={`text-xs px-2 py-0.5 rounded font-medium mt-1 inline-block ${ACTION_STYLES[brief.action]}`}>
            {brief.action}
          </span>
        </div>
      </div>

      {/* Summary */}
      <div className="rounded-lg border border-slate-700 bg-slate-900 px-5 py-4 mb-6">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">
          Analysis
        </h2>
        <p className="text-slate-300 text-sm leading-relaxed">{brief.summary}</p>
      </div>

      {/* Signals */}
      <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
        Signals
      </h2>
      <div className="flex flex-col gap-2 mb-6">
        {Object.entries(brief.signals).map(([name, signal]) => (
          <SignalRow key={name} name={name} signal={signal} />
        ))}
      </div>

      {/* Source Citations */}
      <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
        Sources
      </h2>
      <div className="rounded-lg border border-slate-700 bg-slate-900 px-5 py-2">
        <table className="w-full">
          <thead>
            <tr>
              <th className="text-left text-xs text-slate-500 font-medium py-2 pr-4">Provider</th>
              <th className="text-left text-xs text-slate-500 font-medium py-2 pr-4">Metric</th>
              <th className="text-right text-xs text-slate-500 font-medium py-2 pr-4">Value</th>
              <th className="text-right text-xs text-slate-500 font-medium py-2">Date</th>
            </tr>
          </thead>
          <tbody>
            {brief.source_citations.map((c, i) => (
              <CitationRow key={i} c={c} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
