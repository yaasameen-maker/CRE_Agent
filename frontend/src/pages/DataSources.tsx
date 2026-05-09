const SOURCES: {
  id: string
  label: string
  fullName: string
  provider: string
  icon: string
  color: string
  bg: string
  url: string
  siteUrl: string
  keyLabel: string
  keyValue: string
  metric: string
  description: string
  refreshRate: string
  coverage: string
  badge?: string
}[] = [
  {
    id: 'fred',
    label: 'FRED',
    fullName: 'Federal Reserve Economic Data',
    provider: 'St. Louis Fed',
    icon: 'account_balance',
    color: 'text-[#1565c0]',
    bg: 'bg-[#e3f2fd]',
    url: 'https://fred.stlouisfed.org/series/DRSREACBS',
    siteUrl: 'https://fred.stlouisfed.org',
    keyLabel: 'Series ID',
    keyValue: 'DRSREACBS',
    metric: 'Delinquency Rate — Real Estate Loans',
    description: 'Quarterly delinquency rate on all real estate loans held by commercial banks. Used as the national CRE credit-stress benchmark across all scored ZIP codes.',
    refreshRate: 'Quarterly',
    coverage: 'National',
  },
  {
    id: 'bls',
    label: 'BLS',
    fullName: 'Bureau of Labor Statistics',
    provider: 'U.S. Dept. of Labor',
    icon: 'groups',
    color: 'text-[#2e7d32]',
    bg: 'bg-[#e8f5e9]',
    url: 'https://www.bls.gov/lau/',
    siteUrl: 'https://www.bls.gov',
    keyLabel: 'Metro Code',
    keyValue: 'LAUMT364002000000003',
    metric: 'Unemployment Rate — NYC Metro',
    description: 'Local Area Unemployment Statistics (LAUS) series for the New York–Newark–Jersey City MSA. Provides current unemployment rate and month-over-month change for all NYC ZIP codes.',
    refreshRate: 'Monthly',
    coverage: 'NYC Metro',
  },
  {
    id: 'rentcast',
    label: 'RentCast',
    fullName: 'RentCast Markets API',
    provider: 'RentCast',
    icon: 'home_work',
    color: 'text-[#6a1b9a]',
    bg: 'bg-[#f3e5f5]',
    url: 'https://app.rentcast.io/app/api-keys',
    siteUrl: 'https://rentcast.io',
    keyLabel: 'Key',
    keyValue: 'ZIP Code (per market)',
    metric: 'Rent · Vacancy · Rent Change %',
    description: 'Per-ZIP rental market data: average rent, median rent, 30-day rent change percentage, and vacancy rate. Called once per ZIP per cycle — 50 calls/month quota preserved via Bronze cache.',
    refreshRate: 'Monthly',
    coverage: 'Per ZIP',
  },
  {
    id: 'acris',
    label: 'ACRIS',
    fullName: 'Automated City Register Information System',
    provider: 'NYC Open Data',
    icon: 'receipt_long',
    color: 'text-[#b71c1c]',
    bg: 'bg-[#ffebee]',
    url: 'https://data.cityofnewyork.us/City-Government/ACRIS-Real-Property-Master/bnx9-e6tj',
    siteUrl: 'https://acris.nyc.gov',
    keyLabel: 'Dataset',
    keyValue: 'bnx9-e6tj + 636b-3b5g',
    metric: 'Deed Transfers · Buyer Name · Mailing Address',
    description: 'Every property deed transfer recorded in NYC — buyer name, mailing address, sale price, and date. Used by the outreach agent to surface acquisition leads in high-distress ZIP codes. No API key required.',
    refreshRate: 'Daily',
    coverage: 'NYC (all 5 boroughs)',
    badge: 'FREE',
  },
  {
    id: 'dob',
    label: 'DOB',
    fullName: 'NYC Department of Buildings',
    provider: 'NYC Open Data',
    icon: 'domain',
    color: 'text-[#e65100]',
    bg: 'bg-[#fff3e0]',
    url: 'https://data.cityofnewyork.us/Housing-Development/DOB-Violations/3h2n-5cm9',
    siteUrl: 'https://www.nyc.gov/site/buildings/index.page',
    keyLabel: 'Dataset',
    keyValue: '3h2n-5cm9',
    metric: 'Building Violations (90-day count)',
    description: 'Building violations filed against properties in each ZIP code. A spike in violations signals structural neglect and owner financial stress — fed into the Haiku scoring model as the DOB distress signal. No API key required.',
    refreshRate: 'Daily',
    coverage: 'NYC (all 5 boroughs)',
    badge: 'FREE',
  },
]

const NYC_ZIPS = [
  { zip: '10001', neighborhood: 'Midtown',           borough: 'Manhattan' },
  { zip: '10014', neighborhood: 'West Village',       borough: 'Manhattan' },
  { zip: '10036', neighborhood: 'Times Square',       borough: 'Manhattan' },
  { zip: '10128', neighborhood: 'Upper East Side',    borough: 'Manhattan' },
  { zip: '11201', neighborhood: 'Brooklyn Heights',   borough: 'Brooklyn'  },
]

export default function DataSources() {
  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-display-lg text-primary">Data Sources</h1>
        <p className="text-body-lg text-on-surface-variant mt-1">
          Live market signals powering the scoring pipeline — all cached in the Bronze layer before scoring runs.
        </p>
      </div>

      {/* Core source cards */}
      <div className="flex flex-col gap-5 mb-10">
        {SOURCES.map(src => (
          <div
            key={src.id}
            className="bg-surface-container-lowest border-level-1 rounded-lg shadow-level-2 p-6"
          >
            <div className="flex items-start gap-4">
              {/* Icon */}
              <div className={`w-11 h-11 rounded-lg ${src.bg} flex items-center justify-center shrink-0`}>
                <span className={`material-symbols-outlined text-[24px] ${src.color}`}>{src.icon}</span>
              </div>

              {/* Body */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 flex-wrap mb-1">
                  <h2 className="text-headline-sm text-primary">{src.label}</h2>
                  <span className="text-label-caps text-on-surface-variant opacity-60">{src.fullName}</span>
                  {src.badge && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#e8f5e9] text-[#2e7d32]">
                      {src.badge}
                    </span>
                  )}
                  <span className="ml-auto flex items-center gap-1 text-secondary text-body-md font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-secondary inline-block" />
                    Active
                  </span>
                </div>

                <p className="text-body-md text-on-surface-variant mb-3">{src.description}</p>

                {/* Key / value row */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                  <div className="bg-surface-container-low rounded px-3 py-2">
                    <p className="text-label-caps text-on-surface-variant mb-0.5">{src.keyLabel}</p>
                    <p className="text-data-mono text-on-surface text-[13px] break-all">{src.keyValue}</p>
                  </div>
                  <div className="bg-surface-container-low rounded px-3 py-2">
                    <p className="text-label-caps text-on-surface-variant mb-0.5">METRIC</p>
                    <p className="text-body-md text-on-surface text-[13px]">{src.metric}</p>
                  </div>
                  <div className="bg-surface-container-low rounded px-3 py-2">
                    <p className="text-label-caps text-on-surface-variant mb-0.5">REFRESH</p>
                    <p className="text-body-md text-on-surface text-[13px]">{src.refreshRate}</p>
                  </div>
                  <div className="bg-surface-container-low rounded px-3 py-2">
                    <p className="text-label-caps text-on-surface-variant mb-0.5">COVERAGE</p>
                    <p className="text-body-md text-on-surface text-[13px]">{src.coverage}</p>
                  </div>
                </div>

                {/* Links */}
                <div className="flex items-center gap-4">
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-body-md text-primary hover:underline"
                  >
                    <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                    View Series
                  </a>
                  <a
                    href={src.siteUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-body-md text-on-surface-variant hover:text-primary hover:underline"
                  >
                    <span className="material-symbols-outlined text-[16px]">language</span>
                    {src.provider}
                  </a>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Scored ZIP codes */}
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-label-caps text-on-surface-variant">SCORED MARKETS</h2>
        <span className="text-label-caps text-on-surface-variant opacity-60">NYC SCOPE · 5 ZIP CODES</span>
      </div>
      <div className="bg-surface-container-lowest border-level-1 rounded-lg shadow-level-2 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-outline-variant">
              <th className="text-left text-label-caps text-on-surface-variant px-6 py-3">ZIP</th>
              <th className="text-left text-label-caps text-on-surface-variant px-6 py-3">NEIGHBORHOOD</th>
              <th className="text-left text-label-caps text-on-surface-variant px-6 py-3">BOROUGH</th>
              <th className="text-left text-label-caps text-on-surface-variant px-6 py-3">FRED SERIES</th>
              <th className="text-left text-label-caps text-on-surface-variant px-6 py-3">BLS CODE</th>
            </tr>
          </thead>
          <tbody>
            {NYC_ZIPS.map(({ zip, neighborhood, borough }) => (
              <tr key={zip} className="border-t border-outline-variant hover:bg-surface-container-low transition-colors">
                <td className="px-6 py-3 text-data-mono font-bold text-primary">{zip}</td>
                <td className="px-6 py-3 text-body-md text-on-surface">{neighborhood}</td>
                <td className="px-6 py-3 text-body-md text-on-surface-variant">{borough}</td>
                <td className="px-6 py-3 text-data-mono text-[13px] text-on-surface-variant">DRSREACBS</td>
                <td className="px-6 py-3 text-data-mono text-[13px] text-on-surface-variant">LAUMT364002000000003</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
