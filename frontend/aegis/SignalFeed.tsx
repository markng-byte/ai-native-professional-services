// SignalFeed.tsx — Mobile-first signal feed (home screen)
import React, { useEffect, useState } from 'react'
import { useAegisStore, Signal, ActiveModule } from './aegisStore'
import { aegisApi } from './aegisApi'

const C = {
  bg:     '#07100e',
  bg2:    '#0b1a16',
  bg3:    '#0f2018',
  teal:   '#3de8a0',
  gold:   '#f0c040',
  red:    '#f05060',
  green:  '#00ee77',
  blue:   '#40b0f0',
  muted:  '#5a8878',
  dim:    '#2a5040',
  text:   '#c8e6d8',
  border: 'rgba(61,232,160,0.12)',
}

const LEVEL_COLOR: Record<string, string> = {
  CRITICAL: C.red,
  HIGH:     C.gold,
  MEDIUM:   C.teal,
  LOW:      C.muted,
}

// Role → default CTAs when AI response doesn't specify
const ROLE_ACTIONS: Record<string, Signal['actions']> = {
  entrepreneur: [
    { label: 'What-if Analysis', module: 'REGO', icon: '⬡' },
    { label: 'Local Intel', module: 'VRIT', icon: '◈' },
  ],
  counsel: [
    { label: 'Compliance Check', module: 'VRIT', icon: '◈' },
    { label: 'Generate Brief', module: 'EIT1', icon: '▦' },
  ],
  pe_partner: [
    { label: 'Run Scenario', module: 'EIT2', icon: '★' },
    { label: 'Risk Projection', module: 'REGO', icon: '⬡' },
  ],
  // Admin sees every module's primary action
  admin: [
    { label: 'Analyze (Macro Radar)', module: 'REGO', icon: '⬡' },
    { label: 'Local Intel', module: 'VRIT', icon: '◈' },
    { label: 'Generate Brief', module: 'EIT1', icon: '▦' },
    { label: 'Run War Room', module: 'EIT2', icon: '★' },
  ],
}

function ConfidenceBar({ value, color }: { value: number; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        flex: 1, height: 3, background: C.dim, borderRadius: 2, overflow: 'hidden',
      }}>
        <div style={{
          width: `${value}%`, height: '100%',
          background: color, borderRadius: 2,
          transition: 'width 0.6s ease',
        }}/>
      </div>
      <span style={{ color, fontSize: 12, fontWeight: 700, minWidth: 34, textAlign: 'right' }}>
        {value}%
      </span>
    </div>
  )
}

function TimeAgo({ ts }: { ts: number }) {
  const diff = Date.now() - ts
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return <>{mins}m ago</>
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return <>{hrs}h ago</>
  return <>{Math.floor(hrs / 24)}d ago</>
}

function SignalCard({
  signal, onAction,
}: {
  signal: Signal
  onAction: (module: ActiveModule) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const color = LEVEL_COLOR[signal.level] ?? C.muted

  return (
    <div style={{
      background: C.bg2,
      border: `1px solid ${C.border}`,
      borderLeft: `3px solid ${color}`,
      borderRadius: 12,
      overflow: 'hidden',
      transition: 'box-shadow 0.15s',
    }}>
      {/* Main tap area */}
      <button
        onClick={() => setExpanded(v => !v)}
        style={{
          width: '100%', background: 'none', border: 'none',
          padding: '16px', textAlign: 'left', cursor: 'pointer',
        }}
      >
        {/* Top row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <span style={{
            background: `${color}20`, color,
            fontSize: 10, fontWeight: 700, letterSpacing: 1,
            padding: '2px 8px', borderRadius: 20,
          }}>
            {signal.level}
          </span>
          <span style={{ color: C.muted, fontSize: 11, marginLeft: 'auto' }}>
            <TimeAgo ts={signal.timestamp} />
          </span>
        </div>

        {/* Title */}
        <div style={{
          color: C.text, fontSize: 15, fontWeight: 600,
          lineHeight: 1.4, marginBottom: 10,
        }}>
          {signal.title}
        </div>

        {/* Confidence */}
        <ConfidenceBar value={signal.confidence} color={color} />

        {/* Sources */}
        <div style={{ color: C.muted, fontSize: 11, marginTop: 8 }}>
          {signal.sourceCount} source{signal.sourceCount !== 1 ? 's' : ''} ·{' '}
          {signal.sources.slice(0, 2).join(', ')}
          {signal.sources.length > 2 ? ` +${signal.sources.length - 2}` : ''}
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div style={{ padding: '0 16px 16px', borderTop: `1px solid ${C.border}` }}>
          <p style={{ color: C.text, fontSize: 13, lineHeight: 1.6, margin: '12px 0 16px' }}>
            {signal.summary}
          </p>

          {/* Tags */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
            {signal.tags.map(t => (
              <span key={t} style={{
                background: C.bg3, color: C.muted,
                fontSize: 11, padding: '3px 8px', borderRadius: 6,
              }}>{t}</span>
            ))}
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {signal.actions.map(a => (
              <button
                key={a.label}
                onClick={() => onAction(a.module)}
                style={{
                  padding: '12px 16px',
                  background: C.bg3,
                  border: `1px solid ${C.border}`,
                  borderRadius: 8,
                  color: C.teal,
                  fontSize: 13, fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 10,
                  transition: 'background 0.15s',
                  textAlign: 'left',
                }}
              >
                <span style={{ fontSize: 16 }}>{a.icon}</span>
                <span style={{ flex: 1 }}>{a.label}</span>
                <span style={{ color: C.muted }}>→</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function FilterBar({
  active, onChange,
}: {
  active: string
  onChange: (v: string) => void
}) {
  const filters = ['All', 'CRITICAL', 'HIGH', 'MEDIUM']
  return (
    <div style={{
      display: 'flex', gap: 8, overflowX: 'auto',
      padding: '0 20px 16px', scrollbarWidth: 'none',
    }}>
      {filters.map(f => {
        const isActive = active === f
        const color = LEVEL_COLOR[f] ?? C.teal
        return (
          <button
            key={f}
            onClick={() => onChange(f)}
            style={{
              flexShrink: 0,
              padding: '7px 16px',
              borderRadius: 20,
              border: `1.5px solid ${isActive ? color : C.border}`,
              background: isActive ? `${color}18` : 'none',
              color: isActive ? color : C.muted,
              fontSize: 12, fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s',
              whiteSpace: 'nowrap',
            }}
          >
            {f}
          </button>
        )
      })}
    </div>
  )
}

export default function SignalFeed() {
  const { userProfile, signals, setSignals, setActiveView, setActiveModule } = useAegisStore()
  const [filter, setFilter] = useState('All')
  const [loading, setLoading] = useState(false)
  const [fetchError, setFetchError] = useState('')
  const role = userProfile?.role ?? 'entrepreneur'

  // Fetch signals from API on first mount via ingestion pipeline
  useEffect(() => {
    if (signals.length > 0) return
    const fetchSignals = async () => {
      setLoading(true)
      setFetchError('')
      try {
        const jurisdictions = userProfile?.jurisdictions ?? []
        const org = userProfile?.orgData?.name ?? ''
        const sectors = userProfile?.sectors ?? []
        const input = [
          org ? `${org} regulatory and market intelligence` : '',
          jurisdictions.slice(0, 3).join(', '),
          sectors.slice(0, 2).join(', '),
          '2026 financial regulatory signals SEA',
        ].filter(Boolean).join('; ')

        const res = await aegisApi.ingest({
          mode: 'keywords',
          input,
          org_profile: {
            name: org || 'AEGIS Client',
            sectors,
            geos: jurisdictions,
            risk_appetite: 'moderate',
          },
        })
        const cards: any[] = (res as any)?.cards ?? []
        const defaultActions = ROLE_ACTIONS[role] ?? ROLE_ACTIONS.entrepreneur

        if (cards.length > 0) {
          const LEVEL_MAP: Record<string, Signal['level']> = {
            Escalate: 'CRITICAL', Act: 'HIGH', Investigate: 'MEDIUM', Monitor: 'LOW',
            high: 'HIGH', moderate: 'MEDIUM', monitoring: 'LOW',
          }
          setSignals(cards.slice(0, 12).map((c: any, i: number) => ({
            id: c.id ?? `sig_${i}`,
            title: c.headline ?? c.title ?? 'Signal',
            summary: c.synthesis ?? c.summary ?? c.description ?? '',
            confidence: typeof c.rawCredibility === 'number' ? c.rawCredibility
              : typeof c.impactScore === 'number' ? c.impactScore : 72,
            level: LEVEL_MAP[c.suggestedAction] ?? LEVEL_MAP[c.priority] ?? 'HIGH',
            sources: c.source ? [c.source] : [],
            sourceCount: 1,
            tags: [c.category ?? 'SIGNAL', ...(jurisdictions.slice(0, 1))].filter(Boolean),
            timestamp: Date.now() - i * 3600000,
            jurisdiction: jurisdictions[0] ?? 'GLOBAL',
            actions: defaultActions,
          })))
        }
      } catch (e) {
        setFetchError('Could not fetch live signals. Check your connection.')
      } finally {
        setLoading(false)
      }
    }
    fetchSignals()
  }, [])

  const displayed = filter === 'All'
    ? signals
    : signals.filter(s => s.level === filter)

  const handleAction = (module: ActiveModule) => {
    setActiveModule(module)
    setActiveView(module)
  }

  return (
    <div style={{
      flex: 1, overflowY: 'auto',
      background: C.bg,
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* Feed header */}
      <div style={{ padding: '20px 20px 8px' }}>
        <div style={{ color: C.text, fontSize: 18, fontWeight: 700, marginBottom: 4 }}>
          Signal Feed
        </div>
        <div style={{ color: C.muted, fontSize: 13 }}>
          {displayed.length} signal{displayed.length !== 1 ? 's' : ''} · filtered by your profile
        </div>
      </div>

      <FilterBar active={filter} onChange={setFilter} />

      {/* Signal list */}
      <div style={{ padding: '0 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {displayed.length === 0 ? (
          <div style={{
            padding: '48px 0', textAlign: 'center',
            color: C.muted, fontSize: 14,
          }}>
            No signals at this level right now.
          </div>
        ) : (
          displayed.map(s => (
            <SignalCard key={s.id} signal={s} onAction={handleAction} />
          ))
        )}
      </div>

      {loading && (
        <div style={{ padding: 48, textAlign: 'center', color: C.muted, fontSize: 14 }}>
          <div style={{ marginBottom: 12, fontSize: 24, animation: 'aegis-spin 1s linear infinite', display: 'inline-block' }}>◈</div>
          <div>Fetching signals for your profile…</div>
        </div>
      )}

      {!loading && fetchError && signals.length === 0 && (
        <div style={{ padding: '48px 20px', textAlign: 'center' }}>
          <div style={{ color: C.gold, fontSize: 14, marginBottom: 12 }}>{fetchError}</div>
          <button onClick={() => { setFetchError(''); setSignals([]) }}
            style={{ background: 'none', border: `1px solid ${C.border}`, borderRadius: 8, color: C.teal, fontSize: 13, padding: '10px 20px', cursor: 'pointer' }}>
            Retry
          </button>
        </div>
      )}

      {!loading && !fetchError && signals.length === 0 && (
        <div style={{ padding: '48px 20px', textAlign: 'center', color: C.muted, fontSize: 14 }}>
          No signals yet. Add jurisdictions to your profile to see relevant signals.
        </div>
      )}

      <div style={{ height: 80 }} />
    </div>
  )
}
