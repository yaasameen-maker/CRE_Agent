import { NavLink } from 'react-router-dom'

export default function Header() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1 rounded text-sm font-medium transition-colors ${
      isActive
        ? 'bg-slate-800 text-white'
        : 'text-slate-400 hover:text-white'
    }`

  return (
    <header className="bg-slate-900 border-b border-slate-700 px-6 py-3 flex items-center gap-6">
      <span className="text-white font-semibold tracking-tight">
        CRE Signal Agent
      </span>
      <nav className="flex gap-2">
        <NavLink to="/" end className={linkClass}>
          Digest
        </NavLink>
        <NavLink to="/alerts" className={linkClass}>
          Alerts
        </NavLink>
      </nav>
    </header>
  )
}
