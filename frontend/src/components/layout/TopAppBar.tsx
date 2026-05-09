import { Link, useLocation } from 'react-router-dom'

const NAV_LINKS = [
  { label: 'Analytics', to: '/' },
  { label: 'Research', to: '/research' },
  { label: 'Pipeline', to: '/pipeline' },
]

export default function TopAppBar() {
  const { pathname } = useLocation()

  const isActive = (to: string) =>
    to === '/' ? pathname === '/' : pathname.startsWith(to)

  return (
    <header className="bg-surface text-primary border-b border-outline-variant flex justify-between items-center w-full px-10 h-16 z-40 fixed top-0 left-0">
      <div className="flex items-center gap-8">
        <span className="text-headline-md font-bold text-primary">CRE Intel AI</span>
        <nav className="hidden md:flex h-full items-center gap-1">
          {NAV_LINKS.map(({ label, to }) => (
            <Link
              key={to}
              to={to}
              className={`px-3 py-1.5 text-body-md font-medium rounded transition-colors ${
                isActive(to)
                  ? 'text-primary font-bold border-b-2 border-primary'
                  : 'text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative hidden lg:block">
          <span className="material-symbols-outlined absolute left-2 top-1/2 -translate-y-1/2 text-outline text-[20px]">
            search
          </span>
          <input
            type="text"
            placeholder="Search markets..."
            className="pl-8 pr-3 py-1.5 bg-surface-container-low border border-outline-variant rounded-lg text-body-md focus:outline-none focus:border-primary-container w-56"
          />
        </div>
        <button className="material-symbols-outlined p-2 rounded-full hover:bg-surface-container-high text-on-surface-variant text-[22px]">
          notifications
        </button>
        <button className="material-symbols-outlined p-2 rounded-full hover:bg-surface-container-high text-on-surface-variant text-[22px]">
          help_outline
        </button>
        <button className="material-symbols-outlined p-2 rounded-full hover:bg-surface-container-high text-on-surface-variant text-[22px]">
          settings
        </button>
        <div className="w-8 h-8 rounded-full bg-primary-container border border-outline-variant flex items-center justify-center">
          <span className="material-symbols-outlined text-on-primary-container text-[18px]">person</span>
        </div>
      </div>
    </header>
  )
}
