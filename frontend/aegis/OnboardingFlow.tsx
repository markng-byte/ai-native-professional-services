// OnboardingFlow.tsx — 3-step onboarding after role selection
import React, { useState } from 'react'
import { useAegisStore } from './aegisStore'

const C = {
  bg:     '#07100e',
  bg2:    '#0b1a16',
  bg3:    '#0f2018',
  teal:   '#3de8a0',
  gold:   '#f0c040',
  red:    '#f05060',
  green:  '#00ee77',
  muted:  '#5a8878',
  dim:    '#2a5040',
  text:   '#c8e6d8',
  border: 'rgba(61,232,160,0.12)',
}

const JURISDICTIONS = [
  { code: 'VN', label: 'Vietnam' },
  { code: 'SG', label: 'Singapore' },
  { code: 'EU', label: 'European Union' },
  { code: 'US', label: 'United States' },
  { code: 'HK', label: 'Hong Kong' },
  { code: 'TH', label: 'Thailand' },
  { code: 'ID', label: 'Indonesia' },
  { code: 'MY', label: 'Malaysia' },
]

const SECTORS = [
  { code: 'fintech', label: 'Fintech / Payments' },
  { code: 'crypto', label: 'Crypto / Digital Assets' },
  { code: 'pe', label: 'Private Equity / VC' },
  { code: 'real_estate', label: 'Real Estate' },
  { code: 'healthcare', label: 'Healthcare' },
  { code: 'tech', label: 'Technology / SaaS' },
  { code: 'manufacturing', label: 'Manufacturing' },
  { code: 'trade', label: 'Trade / Logistics' },
]

function ToggleChip({
  label, selected, color = C.teal, onClick,
}: { label: string; selected: boolean; color?: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '9px 16px',
        borderRadius: 24,
        border: `1.5px solid ${selected ? color : C.border}`,
        background: selected ? `${color}18` : C.bg2,
        color: selected ? color : C.muted,
        fontSize: 13, fontWeight: selected ? 600 : 400,
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        whiteSpace: 'nowrap',
      }}
    >
      {selected ? '✓ ' : ''}{label}
    </button>
  )
}

function StepDots({ total, current }: { total: number; current: number }) {
  return (
    <div style={{ display: 'flex', gap: 6, justifyContent: 'center', marginBottom: 36 }}>
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} style={{
          width: i === current ? 20 : 6,
          height: 6,
          borderRadius: 3,
          background: i <= current ? C.teal : C.dim,
          transition: 'all 0.3s ease',
        }}/>
      ))}
    </div>
  )
}

export default function OnboardingFlow() {
  const { userProfile, setUserProfile } = useAegisStore()
  const [step, setStep] = useState(0)
  const [name, setName] = useState('')
  const [jurisdictions, setJurisdictions] = useState<string[]>([])
  const [sectors, setSectors] = useState<string[]>([])

  const toggle = (arr: string[], val: string, set: (a: string[]) => void) =>
    set(arr.includes(val) ? arr.filter(x => x !== val) : [...arr, val])

  const finish = () => {
    if (!userProfile) return
    setUserProfile({
      ...userProfile,
      name: name.trim() || 'User',
      jurisdictions,
      sectors,
      onboardingComplete: true,
    })
  }

  const canNext = [
    name.trim().length > 0,
    jurisdictions.length > 0,
    sectors.length > 0,
  ]

  const roleLabel: Record<string, string> = {
    entrepreneur: 'Founder',
    counsel: 'General Counsel',
    pe_partner: 'PE Partner',
  }

  return (
    <div style={{
      minHeight: '100dvh',
      background: C.bg,
      display: 'flex', flexDirection: 'column',
      fontFamily: "'Inter', system-ui, sans-serif",
      padding: '0 0 40px',
    }}>
      <style>{`
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Header */}
      <div style={{
        padding: '20px 24px 0',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <svg width={24} height={24} viewBox="0 0 24 24">
            <polygon points="12,2 22,8 22,16 12,22 2,16 2,8"
              fill="none" stroke={C.teal} strokeWidth={1.5}/>
            <circle cx={12} cy={12} r={2} fill={C.teal}/>
          </svg>
          <span style={{ color: C.teal, fontSize: 14, fontWeight: 700, letterSpacing: 3 }}>AEGIS</span>
        </div>
        <span style={{
          background: `${C.teal}18`, color: C.teal,
          fontSize: 11, fontWeight: 600, letterSpacing: 1,
          padding: '4px 10px', borderRadius: 20,
        }}>
          {userProfile ? roleLabel[userProfile.role] ?? userProfile.role : ''}
        </span>
      </div>

      {/* Content */}
      <div style={{
        flex: 1, padding: '40px 24px 0',
        display: 'flex', flexDirection: 'column',
        maxWidth: 480, margin: '0 auto', width: '100%',
        animation: 'fadeUp 0.4s ease both',
      }}>
        <StepDots total={3} current={step} />

        {/* Step 0 — Name */}
        {step === 0 && (
          <div>
            <div style={{ color: C.text, fontSize: 22, fontWeight: 700, marginBottom: 8 }}>
              What should we call you?
            </div>
            <div style={{ color: C.muted, fontSize: 14, marginBottom: 32 }}>
              Your name personalises your briefs and reports.
            </div>
            <input
              autoFocus
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && canNext[0] && setStep(1)}
              placeholder="First name or full name"
              style={{
                width: '100%',
                padding: '14px 16px',
                background: C.bg2,
                border: `1.5px solid ${name.trim() ? C.teal : C.border}`,
                borderRadius: 10,
                color: C.text,
                fontSize: 16,
                outline: 'none',
                transition: 'border-color 0.15s',
                fontFamily: 'inherit',
              }}
            />
          </div>
        )}

        {/* Step 1 — Jurisdictions */}
        {step === 1 && (
          <div>
            <div style={{ color: C.text, fontSize: 22, fontWeight: 700, marginBottom: 8 }}>
              Which markets matter to you?
            </div>
            <div style={{ color: C.muted, fontSize: 14, marginBottom: 32 }}>
              Select all that apply. Your feed will prioritise signals from these jurisdictions.
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              {JURISDICTIONS.map(j => (
                <ToggleChip
                  key={j.code}
                  label={j.label}
                  selected={jurisdictions.includes(j.code)}
                  onClick={() => toggle(jurisdictions, j.code, setJurisdictions)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Step 2 — Sectors */}
        {step === 2 && (
          <div>
            <div style={{ color: C.text, fontSize: 22, fontWeight: 700, marginBottom: 8 }}>
              Which sectors are you in?
            </div>
            <div style={{ color: C.muted, fontSize: 14, marginBottom: 32 }}>
              Signals will be filtered and ranked by sector relevance.
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              {SECTORS.map(s => (
                <ToggleChip
                  key={s.code}
                  label={s.label}
                  selected={sectors.includes(s.code)}
                  onClick={() => toggle(sectors, s.code, setSectors)}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer nav */}
      <div style={{
        padding: '32px 24px 0',
        maxWidth: 480, margin: '0 auto', width: '100%',
        display: 'flex', gap: 12,
      }}>
        {step > 0 && (
          <button
            onClick={() => setStep(s => s - 1)}
            style={{
              flex: 0, padding: '15px 20px',
              borderRadius: 12, border: `1.5px solid ${C.border}`,
              background: 'none', color: C.muted,
              fontSize: 15, cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            ←
          </button>
        )}
        <button
          onClick={() => step < 2 ? setStep(s => s + 1) : finish()}
          disabled={!canNext[step]}
          style={{
            flex: 1, padding: '15px',
            borderRadius: 12, border: 'none',
            background: canNext[step] ? C.teal : C.dim,
            color: canNext[step] ? C.bg : C.muted,
            fontSize: 15, fontWeight: 700,
            cursor: canNext[step] ? 'pointer' : 'not-allowed',
            transition: 'all 0.18s ease',
            boxShadow: canNext[step] ? '0 0 24px rgba(61,232,160,0.25)' : 'none',
            fontFamily: 'inherit',
          }}
        >
          {step < 2 ? 'Next →' : 'Enter AEGIS →'}
        </button>
      </div>

      {/* Skip */}
      <div style={{ textAlign: 'center', marginTop: 16, padding: '0 24px' }}>
        <button
          onClick={finish}
          style={{
            background: 'none', border: 'none',
            color: C.dim, fontSize: 12, cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >
          Skip setup — I'll configure later
        </button>
      </div>
    </div>
  )
}
