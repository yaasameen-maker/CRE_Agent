import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import digestFixture from '../fixtures/signal_digest.json'
import type { SignalDigest } from '../types/signal_digest'

const digest = digestFixture as unknown as SignalDigest

// NYC ZIP coordinates (lat, lng)
const ZIP_COORDS: Record<string, [number, number]> = {
  '10001': [40.7506, -73.9971],
  '10014': [40.7335, -74.0027],
  '10036': [40.7580, -73.9855],
  '10128': [40.7794, -73.9524],
  '11201': [40.6926, -73.9900],
}

function scoreToColor(score: number): string {
  if (score >= 70) return '#ba1a1a'
  if (score >= 40) return '#d97706'
  return '#006c49'
}

function scoreToLabel(score: number): string {
  if (score >= 70) return 'MODEL'
  if (score >= 40) return 'MONITOR'
  return 'IGNORE'
}

export default function Research() {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<unknown>(null)

  const avgScore = Math.round(
    digest.zips.reduce((s, z) => s + z.distress_score, 0) / digest.zips.length
  )
  const modelCount = digest.zips.filter(z => z.action === 'Model').length

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return

    // Dynamic import so Leaflet CSS only loads when Research is visited
    import('leaflet').then(L => {
      import('leaflet/dist/leaflet.css')

      if (!mapContainerRef.current || mapRef.current) return

      const map = L.map(mapContainerRef.current, { zoomControl: false }).setView(
        [40.73, -73.98],
        12
      )

      // CartoDB Positron — light, minimal, matches design
      L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
        {
          attribution: '© OpenStreetMap © CARTO',
          subdomains: 'abcd',
          maxZoom: 19,
        }
      ).addTo(map)

      // Custom zoom control bottom-right
      L.control.zoom({ position: 'bottomright' }).addTo(map)

      // Drop pins for each scored ZIP
      digest.zips.forEach(entry => {
        const coords = ZIP_COORDS[entry.zip]
        if (!coords) return

        const color = scoreToColor(entry.distress_score)
        const label = scoreToLabel(entry.distress_score)

        const icon = L.divIcon({
          className: '',
          html: `<div style="
            background: ${color};
            color: white;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: 2.5px solid white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Inter', sans-serif;
            font-size: 11px;
            font-weight: 700;
          ">${entry.rank}</div>`,
          iconSize: [36, 36],
          iconAnchor: [18, 18],
        })

        const neighborhood = (entry as { neighborhood?: string }).neighborhood ?? entry.city

        const popup = L.popup({ offset: [0, -18], maxWidth: 280 }).setContent(`
          <div style="font-family: 'Inter', sans-serif; min-width: 240px;">
            <div style="background: #131b2e; color: white; padding: 12px 16px;">
              <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                  <div style="font-family: 'Manrope', sans-serif; font-size: 16px; font-weight: 700;">${neighborhood}</div>
                  <div style="font-size: 12px; color: #7c839b; margin-top: 2px;">ZIP ${entry.zip} · New York, NY</div>
                </div>
                <span style="background: ${color}22; color: ${color}; border: 1px solid ${color}44; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; letter-spacing: 0.05em;">${label}</span>
              </div>
            </div>
            <div style="padding: 12px 16px; background: white;">
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px;">
                <div style="background: #f2f4f6; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0;">
                  <div style="font-size: 10px; font-weight: 700; letter-spacing: 0.05em; color: #45464d; text-transform: uppercase;">DISTRESS</div>
                  <div style="font-size: 15px; font-weight: 700; color: ${color}; margin-top: 2px;">${entry.distress_score} / 100</div>
                </div>
                <div style="background: #f2f4f6; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0;">
                  <div style="font-size: 10px; font-weight: 700; letter-spacing: 0.05em; color: #45464d; text-transform: uppercase;">RANK</div>
                  <div style="font-size: 15px; font-weight: 700; color: #191c1e; margin-top: 2px;">#${entry.rank} of ${digest.zips.length}</div>
                </div>
              </div>
              <a href="/brief/${entry.zip}" style="display: block; text-align: center; padding: 8px; background: #006c49; color: white; border-radius: 6px; font-size: 11px; font-weight: 700; letter-spacing: 0.05em; text-decoration: none; text-transform: uppercase;">
                VIEW FULL BRIEF
              </a>
            </div>
          </div>
        `)

        L.marker(coords, { icon }).addTo(map).bindPopup(popup)
      })

      mapRef.current = map
    })

    return () => {
      if (mapRef.current) {
        ;(mapRef.current as { remove: () => void }).remove()
        mapRef.current = null
      }
    }
  }, [])

  return (
    // Escape the Layout's px-10 py-8 padding so map fills full bleed
    <div className="-mx-10 -my-8 relative" style={{ height: 'calc(100vh - 64px)' }}>
      {/* Map canvas */}
      <div ref={mapContainerRef} className="absolute inset-0 w-full h-full" />

      {/* Floating market summary card */}
      <div className="absolute top-4 left-4 z-[1000] bg-white/95 backdrop-blur-sm rounded-xl p-5 shadow-xl border-level-1 w-72">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-headline-sm text-primary">NYC Market</h3>
            <p className="text-body-md text-on-surface-variant">Commercial Real Estate</p>
          </div>
          <span className="material-symbols-outlined text-secondary text-[22px]">trending_up</span>
        </div>

        <div className="space-y-3">
          <div className="flex justify-between items-center py-2 border-b border-outline-variant">
            <span className="text-body-md text-on-surface-variant">Scored Markets</span>
            <span className="text-data-mono font-bold">{digest.zips.length}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-outline-variant">
            <span className="text-body-md text-on-surface-variant">Avg. Distress</span>
            <span className="text-data-mono font-bold">{avgScore} / 100</span>
          </div>
          <div className="flex justify-between items-center py-2">
            <span className="text-body-md text-on-surface-variant">Model Alerts</span>
            <div className="flex items-center gap-1">
              <span className="text-data-mono font-bold text-secondary">{modelCount}</span>
              <span className="text-label-caps text-on-surface-variant">/ {digest.zips.length}</span>
            </div>
          </div>
        </div>

        <Link
          to="/"
          className="mt-4 block w-full text-center py-2 border border-primary text-primary text-label-caps rounded-lg hover:bg-surface-container-low transition-colors"
        >
          VIEW FULL DIGEST
        </Link>
      </div>

      {/* Legend */}
      <div className="absolute bottom-6 left-4 z-[1000] bg-white/95 backdrop-blur-sm rounded-lg px-4 py-3 border-level-1 shadow-md">
        <p className="text-label-caps text-on-surface-variant mb-2">DISTRESS SCALE</p>
        <div className="flex gap-4">
          {[
            { color: '#ba1a1a', label: 'Model (≥70)' },
            { color: '#d97706', label: 'Monitor (40–69)' },
            { color: '#006c49', label: 'Ignore (<40)' },
          ].map(({ color, label }) => (
            <div key={label} className="flex items-center gap-1.5">
              <div
                className="w-3 h-3 rounded-full border border-white"
                style={{ background: color }}
              />
              <span className="text-[11px] text-on-surface-variant">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
