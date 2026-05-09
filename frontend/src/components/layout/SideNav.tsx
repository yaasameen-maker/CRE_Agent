import { Link, useLocation } from 'react-router-dom'

const NAV_ITEMS = [
  { label: 'Analytics', to: '/', icon: 'dashboard' },
  { label: 'AI Assistant', to: '/assistant', icon: 'smart_toy' },
  { label: 'Research', to: '/research', icon: 'map' },
  { label: 'Pipeline', to: '/pipeline', icon: 'view_kanban' },
]

export default function SideNav() {
  const { pathname } = useLocation()
  const isResearch = pathname === '/research'

  const isActive = (to: string) =>
    to === '/' ? pathname === '/' : pathname.startsWith(to)

  return (
    <nav className="bg-surface-container-low border-r border-outline-variant fixed left-0 top-16 h-[calc(100vh-64px)] w-64 flex flex-col p-4 z-50 overflow-y-auto">
      {/* Portfolio header */}
      <div className="mb-6 px-2">
        <p className="text-headline-sm font-black text-primary">Global Assets</p>
        <p className="text-label-caps text-on-surface-variant opacity-60 mt-0.5">
          INSTITUTIONAL GRADE
        </p>
      </div>

      {/* Nav items */}
      <div className="space-y-0.5 flex-grow">
        {NAV_ITEMS.map(({ label, to, icon }) => (
          <Link
            key={to}
            to={to}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-body-md ${
              isActive(to)
                ? 'bg-secondary-container text-on-secondary-container font-bold translate-x-0.5'
                : 'text-on-surface-variant hover:bg-surface-container-high hover:text-primary'
            }`}
          >
            <span className="material-symbols-outlined text-[22px]">{icon}</span>
            {label}
          </Link>
        ))}

        {/* Research-specific filters */}
        {isResearch && (
          <div className="pt-6 space-y-4 border-t border-outline-variant mt-4">
            <p className="text-label-caps text-on-surface-variant px-2">FILTERS</p>

            <div className="px-2 space-y-4">
              <div>
                <label className="block text-label-caps text-on-surface-variant mb-1">
                  ZONING TYPE
                </label>
                <select className="w-full bg-white border border-outline-variant rounded px-2 py-1.5 text-body-md focus:outline-none focus:border-primary-container">
                  <option>Commercial — High Density</option>
                  <option>Industrial — Light</option>
                  <option>Residential — Multi</option>
                </select>
              </div>

              <div>
                <label className="block text-label-caps text-on-surface-variant mb-1">
                  SQUARE FOOTAGE
                </label>
                <div className="flex items-center gap-2">
                  <input
                    className="w-full bg-white border border-outline-variant rounded px-2 py-1.5 text-body-md focus:outline-none"
                    placeholder="Min"
                    type="text"
                  />
                  <span className="text-outline text-sm">to</span>
                  <input
                    className="w-full bg-white border border-outline-variant rounded px-2 py-1.5 text-body-md focus:outline-none"
                    placeholder="Max"
                    type="text"
                  />
                </div>
              </div>

              <div>
                <label className="block text-label-caps text-on-surface-variant mb-1">
                  DEMOGRAPHICS
                </label>
                <div className="space-y-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      defaultChecked
                      type="checkbox"
                      className="rounded border-outline-variant accent-secondary"
                    />
                    <span className="text-body-md">HHI &gt; $150k</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      className="rounded border-outline-variant accent-secondary"
                    />
                    <span className="text-body-md">Pop Growth &gt; 5%</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bottom CTA + footer links */}
      <div className="mt-auto pt-4">
        <button className="w-full bg-primary text-white py-3 rounded-lg text-label-caps flex items-center justify-center gap-2 hover:opacity-90 transition-opacity mb-4">
          <span className="material-symbols-outlined text-[18px]">add</span>
          NEW OPPORTUNITY
        </button>
        <div className="border-t border-outline-variant pt-3 space-y-0.5">
          <Link
            to="/settings"
            className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary text-body-md rounded-lg hover:bg-surface-container-high transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">settings</span>
            Settings
          </Link>
          <Link
            to="/support"
            className="flex items-center gap-3 px-3 py-2 text-on-surface-variant hover:text-primary text-body-md rounded-lg hover:bg-surface-container-high transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">contact_support</span>
            Support
          </Link>
        </div>
      </div>
    </nav>
  )
}
