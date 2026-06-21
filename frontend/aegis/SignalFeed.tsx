// SignalFeed.tsx — Mobile-first signal feed (home screen)
import React, { useEffect, useRef, useState } from 'react'
import { useAegisStore, Signal, ActiveModule, UserRole } from './aegisStore'
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

// Seed signals per role (shown instantly before AI fetch)
const SEED_SIGNALS: Record<UserRole, Signal[]> = {
  entrepreneur: [
    {
      id: 's1', level: 'CRITICAL', confidence: 91,
      title: 'Vietnam tightens foreign ownership caps in fintech',
      summary: 'SBV draft circular limits foreign equity to 30% in licensed payment institutions. Comment period closes June 30.',
      sources: ['VIR', 'SBV Official Gazette', 'Reuters'],
      sourceCount: 3, tags: ['VN', 'Fintech', 'Regulatory'],
      timestamp: Date.now() - 3600000, jurisdiction: 'VN',
      actions: [
        { label: 'What-if Analysis', module: 'REGO', icon: '⬡' },
        { label: 'Check Local Intel', module: 'VRIT', icon: '◈' },
      ],
    },
    {
      id: 's2', level: 'HIGH', confidence: 78,
      title: 'MAS issues new digital token guidelines',
      summary: 'Monetary Authority of Singapore expands Digital Payment Token framework, affecting cross-border remittance products.',
      sources: ['MAS', 'CoinDesk Asia'],
      sourceCount: 2, tags: ['SG', 'Crypto', 'Payment'],
      timestamp: Date.now() - 7200000, jurisdiction: 'SG',
      actions: [
        { label: 'Stakeholder Map', module: 'REGO', icon: '⬡' },
        { label: 'Run Scenario', module: 'EIT2', icon: '★' },
      ],
    },
    {
      id: 's3', level: 'MEDIUM', confidence: 64,
      title: 'EU AI Act enforcement: high-risk system checklist updated',
      summary: 'European Commission published revised high-risk AI system classification. Affects credit scoring and recruitment tools.',
      sources: ['EU Official Journal', 'TechCrunch EU'],
      sourceCount: 2, tags: ['EU', 'AI', 'Compliance'],
      timestamp: Date.now() - 18000000, jurisdiction: 'EU',
      actions: [
        { label: 'Regulatory Lookup', module: 'REGO', icon: '⬡' },
        { label: 'Advocacy Brief', module: 'REGO', icon: '⬡' },
      ],
    },
  ],
  counsel: [
    {
      id: 'c1', level: 'CRITICAL', confidence: 95,
      title: 'FATF Travel Rule enforcement deadline: 30 days',
      summary: 'Virtual asset service providers in VN, SG, TH must comply with Travel Rule data sharing. Non-compliance penalties active July 1.',
      sources: ['FATF', 'SBV', 'MAS', 'BOT'],
      sourceCount: 4, tags: ['FATF', 'VASP', 'Deadline'],
      timestamp: Date.now() - 1800000, jurisdiction: 'GLOBAL',
      actions: [
        { label: 'Compliance Check', module: 'VRIT', icon: '◈' },
        { label: 'Sanctions Screen', module: 'VRIT', icon: '◈' },
      ],
    },
    {
      id: 'c2', level: 'HIGH', confidence: 83,
      title: 'Vietnam sanctions list updated — 12 new entities',
      summary: 'MOIT updated restricted entity list. Cross-check required for any ongoing contracts or due diligence.',
      sources: ['MOIT Vietnam', 'UN Sanctions'],
      sourceCount: 2, tags: ['VN', 'Sanctions', 'Due Diligence'],
      timestamp: Date.now() - 5400000, jurisdiction: 'VN',
      actions: [
        { label: 'Screen Entities', module: 'VRIT', icon: '◈' },
        { label: 'Verify Org', module: 'EIT1', icon: '▦' },
      ],
    },
    {
      id: 'c3', level: 'HIGH', confidence: 71,
      title: 'SBV Circular 02/2026 open for public comment',
      summary: 'New draft regulation on credit classification and provisioning. Comment window closes May 25. High impact on lending products.',
      sources: ['SBV', 'VietnamPlus'],
      sourceCount: 2, tags: ['VN', 'Banking', 'Credit'],
      timestamp: Date.now() - 14400000, jurisdiction: 'VN',
      actions: [
        { label: 'Generate Brief', module: 'EIT1', icon: '▦' },
        { label: 'Advocacy Brief', module: 'REGO', icon: '⬡' },
      ],
    },
  ],
  pe_partner: [
    {
      id: 'p1', level: 'CRITICAL', confidence: 88,
      title: 'Southeast Asia PE exit multiples compressing — macro headwinds',
      summary: 'Rising interest rates and USD strength shrinking exit valuations across SEA. Three portfolio companies in affected sectors.',
      sources: ['Preqin', 'DealStreetAsia', 'Bloomberg'],
      sourceCount: 3, tags: ['SEA', 'PE', 'Exit Risk'],
      timestamp: Date.now() - 2700000, jurisdiction: 'SEA',
      actions: [
        { label: 'Run War Room', module: 'EIT2', icon: '★' },
        { label: 'Scenario Planning', module: 'EIT2', icon: '★' },
      ],
    },
    {
      id: 'p2', level: 'HIGH', confidence: 76,
      title: 'Vietnam restricts repatriation of foreign capital gains',
      summary: 'New MoF guidance limits timing windows for PE fund repatriation. Affects Q3/Q4 planned exits.',
      sources: ['MoF Vietnam', 'VIR', 'KPMG Vietnam'],
      sourceCount: 3, tags: ['VN', 'PE', 'Tax', 'Exit'],
      timestamp: Date.now() - 9000000, jurisdiction: 'VN',
      actions: [
        { label: 'What-if Analysis', module: 'REGO', icon: '⬡' },
        { label: 'Jurisdiction Compare', module: 'REGO', icon: '⬡' },
      ],
    },
    {
      id: 'p3', level: 'MEDIUM', confidence: 61,
      title: 'ESG disclosure requirements expanding in SG, HK by 2027',
      summary: 'SGX and HKEX tightening mandatory ESG reporting. Portfolio companies need 18-month preparation timeline.',
      sources: ['SGX', 'HKEX', 'PWC'],
      sourceCount: 3, tags: ['SG', 'HK', 'ESG', 'Compliance'],
      timestamp: Date.now() - 21600000, jurisdiction: 'SG',
      actions: [
        { label: 'Risk Projection', module: 'REGO', icon: '⬡' },
        { label: 'Run Scenarios', module: 'EIT2', icon: '★' },
      ],
    },
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
  const role = userProfile?.role ?? 'entrepreneur'

  // Load seed signals immediately
  useEffect(() => {
    if (signals.length === 0) {
      setSignals(SEED_SIGNALS[role] ?? SEED_SIGNALS.entrepreneur)
    }
  }, [role])

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
        <div style={{ padding: 24, textAlign: 'center', color: C.muted, fontSize: 13 }}>
          Refreshing signals…
        </div>
      )}

      <div style={{ height: 80 }} />
    </div>
  )
}
