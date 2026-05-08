import { Link } from 'react-router-dom'
import digestFixture from '../fixtures/signal_digest.json'
import type { SignalDigest, ZipEntry } from '../types/signal_digest'

const digest = digestFixture as unknown as SignalDigest

const ACTION_STYLES: Record<string, string> = {
  Model:   'bg-red-900 text-red-200 border border-red-700',
  Monitor: 'bg-yellow-900 text-yellow-200 border border-yellow-700',
  Ignore:  'bg-slate-800 text-slate-400 border border-slate-700',
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? 'bg-red-500' : score >= 40 ? 'bg-yellow-500' : 'bg-green-500'
  return (
    <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
    </div>
  )
}

function ZipRow({ entry }: { entry: ZipEntry }) {
  const flaggedSignals = Object.entries(entry.signals)
    .filter(([, s]) => s.flag)
    .map(([name]) => name)

  return (
    <Link
      to={`/brief/${entry.zip}`}
      className="flex items-center gap-4 px-5 py-4 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-600 transition-colors"
    >
      <span className="text-slate-500 text-sm w-5 text-right">{entry.rank}</span>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-white">
          {entry.zip}
          <span className="text-slate-400 text-sm font-normal ml-2">
            {entry.city}, {entry.state}
          </span>
        </p>
        {flaggedSignals.length > 0 && (
          <p className="text-xs text-slate-500 mt-0.5 truncate">
            Flags: {flaggedSignals.join(' · ')}
          </p>
        )}
      </div>
      <ScoreBar score={entry.distress_score} />
      <span className="text-slate-300 text-sm w-8 text-right">{entry.distress_score}</span>
      <span className={`text-xs px-2 py-0.5 rounded font-medium ${ACTION_STYLES[entry.action] ?? ACTION_STYLES.Ignore}`}>
        {entry.action}
      </span>
    </Link>
  )
}

export default function DigestList() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-white">Signal Digest</h1>
        <p className="text-slate-400 text-sm mt-1">
          Generated {new Date(digest.generated_at).toLocaleString()} · {digest.zips.length} markets scored
        </p>
      </div>
      <div className="flex flex-col gap-3">
        {digest.zips.map((entry) => (
          <ZipRow key={entry.zip} entry={entry} />
        ))}
      </div>
    </div>
  )
}
