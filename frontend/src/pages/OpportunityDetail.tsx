import { useParams, Link } from 'react-router-dom'

export default function OpportunityDetail() {
  const { zip } = useParams<{ zip: string }>()

  return (
    <div>
      <Link to="/" className="text-slate-400 text-sm hover:text-white mb-6 inline-block">
        ← Back to Digest
      </Link>
      <h1 className="text-2xl font-semibold text-white mb-2">Opportunity Brief — {zip}</h1>
      <p className="text-slate-400">
        Full brief view coming in Phase B once the Gold layer is producing data.
      </p>
    </div>
  )
}
