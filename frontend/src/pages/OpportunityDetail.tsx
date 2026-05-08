import { Link } from 'react-router-dom'
import briefFixture from '../fixtures/opportunity_brief.json'
import type { OpportunityBrief, BriefSignalValue, SourceCitation } from '../types/opportunity_brief'

const brief = briefFixture as OpportunityBrief

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
    <div className={`flex items-center gap-4 px-4 py-3 rounded-lg border transition-colors ${
      signal.flag
        ? 'border-error/30 bg-error-container/20'
        : 'border-outline-variant bg-surface-container-low'
    }`}>
      <div
        className="w-2 h-2 rounded-full shrink-0"
        style={{ backgroundColor: signal.flag ? '#ba1a1a' : '#006c49' }}
      />
      <div className="flex-1 min-w-0">
        <p className="text-body-md font-medium text-on-surface">{SIGNAL_LABELS[name]}</p>
        <p className="text-body-md text-on-surface-variant text-[12px]">
          {signal.source} · {signal.as_of}
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

function CitationRow({ c }: { c: SourceCitation }) {
  return (
    <tr className="border-t border-outline-variant hover:bg-surface-container-low transition-colors">
      <td className="py-2.5 pr-4 text-body-md text-on-surface-variant">{c.source}</td>
      <td className="py-2.5 pr-4 text-body-md text-on-surface">{c.metric}</td>
      <td className="py-2.5 pr-4 text-data-mono text-on-surface text-right">{c.value}</td>
      <td className="py-2.5 text-body-md text-on-surface-variant text-right">{c.date}</td>
    </tr>
  )
}

function scoreColor(s: number) {
  if (s >= 70) return 'text-error'
  if (s >= 40) return 'text-[#d97706]'
  return 'text-secondary'
}

export default function OpportunityDetail() {
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
              {brief.zip}
              <span className="text-on-surface-variant font-normal ml-2 text-[18px]">
                {brief.city}, {brief.state}
              </span>
            </h1>
            <p className="text-body-md text-on-surface-variant mt-1">
              Generated {new Date(brief.generated_at).toLocaleString()}
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className={`text-display-lg font-bold tabular-nums ${scoreColor(brief.distress_score)}`}>
              {brief.distress_score}
            </p>
            <span className={`text-[10px] px-2 py-0.5 rounded font-bold mt-1 inline-block ${ACTION_BADGE[brief.action] ?? ACTION_BADGE.Ignore}`}>
              {brief.action.toUpperCase()}
            </span>
          </div>
        </div>
      </div>

      {/* Analysis summary */}
      <div className="bg-surface-container-lowest border-level-1 rounded-lg shadow-level-2 px-6 py-5 mb-5">
        <h2 className="text-label-caps text-on-surface-variant mb-3">AI ANALYSIS</h2>
        <p className="text-body-lg text-on-surface leading-relaxed">{brief.summary}</p>
      </div>

      {/* Signals */}
      <h2 className="text-label-caps text-on-surface-variant mb-3">SIGNAL BREAKDOWN</h2>
      <div className="flex flex-col gap-2 mb-5">
        {Object.entries(brief.signals).map(([name, signal]) => (
          <SignalRow key={name} name={name} signal={signal} />
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
            {brief.source_citations.map((c, i) => (
              <CitationRow key={i} c={c} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
