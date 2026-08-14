// LoginScreen.tsx — AEGIS profile selection (no backend auth)
import React, { useState } from 'react'
import { useAegisStore, UserRole } from './aegisStore'

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
  glow:   '0 0 32px rgba(61,232,160,0.15)',
}

interface RoleCard {
  role: UserRole
  icon: string
  title: string
  subtitle: string
  color: string
  description: string
  tags: string[]
}

const ROLES: RoleCard[] = [
  {
    role: 'entrepreneur',
    icon: '◈',
    title: 'Founder / Entrepreneur',
    subtitle: 'Solo or early-stage',
    color: C.teal,
    description: 'Regulatory signals, market entry risk, jurisdiction compare',
    tags: ['Macro Radar', 'What-if', 'Advocacy'],
  },
  {
    role: 'counsel',
    icon: '⬡',
    title: 'General Counsel',
    subtitle: 'In-house or advisory',
    color: C.gold,
    description: 'Compliance deadlines, sanctions screening, local intel',
    tags: ['Local Intel', 'Org Verify', 'Compliance'],
  },
  {
    role: 'pe_partner',
    icon: '★',
    title: 'PE / Managing Partner',
    subtitle: 'Fund or portfolio level',
    color: C.red,
    description: 'Scenario planning, exit risk, portfolio stress-test',
    tags: ['War Room', 'Scenarios', 'Simulation'],
  },
]

export default function LoginScreen() {
  const setUserProfile = useAegisStore(s => s.setUserProfile)
  const clearUserProfile = useAegisStore(s => s.clearUserProfile)
  const setFeedInitialized = useAegisStore(s => s.setFeedInitialized)
  const [selected, setSelected] = useState<UserRole | null>(null)
  const [hovering, setHovering] = useState<UserRole | null>(null)
  const [adminOpen, setAdminOpen] = useState(false)
  const [adminUser, setAdminUser] = useState('')
  const [adminPass, setAdminPass] = useState('')
  const [adminError, setAdminError] = useState('')

  const ADMIN_USER = (import.meta as any).env?.VITE_ADMIN_USER || 'admin'
  const ADMIN_PASS = (import.meta as any).env?.VITE_ADMIN_PASSCODE || 'aegis-admin-2026'

  const loginAdmin = () => {
    if (adminUser.trim() !== ADMIN_USER || adminPass !== ADMIN_PASS) {
      setAdminError('Invalid admin credentials.')
      return
    }
    clearUserProfile()
    setFeedInitialized(false)
    setUserProfile({
      role: 'admin',
      name: adminUser.trim() || 'Administrator',
      jurisdictions: ['VN', 'SG', 'EU', 'US', 'HK'],
      sectors: ['pe', 'fintech', 'crypto', 'tech', 'real_estate'],
      orgData: {
        name: 'AEGIS Control',
        country: 'Global',
        sector: 'All Sectors',
        registrationId: '',
        verified: true,
        raw: {},
      },
      onboardingComplete: true,
    })
  }

  const proceed = () => {
    if (!selected) return
    setUserProfile({
      role: selected,
      name: '',
      jurisdictions: [],
      sectors: [],
      orgData: null,
      onboardingComplete: false,
    })
  }

  // One-tap full-access demo profile (PE partner unlocks every module + CTA)
  const startDemo = () => {
    setUserProfile({
      role: 'pe_partner',
      name: 'Alex Tan',
      jurisdictions: ['VN', 'SG', 'EU'],
      sectors: ['pe', 'fintech', 'crypto'],
      orgData: {
        name: 'Meridian Capital Partners',
        country: 'Singapore',
        sector: 'Private Equity / VC',
        registrationId: '',
        verified: false,
        raw: {},
      },
      onboardingComplete: true,
    })
  }

  return (
    <div style={{
      minHeight: '100dvh',
      background: C.bg,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px 20px',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      <style>{`
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Logo */}
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        gap: 12, marginBottom: 48,
        animation: 'fadeUp 0.5s ease both',
      }}>
        <svg width={48} height={48} viewBox="0 0 24 24">
          <polygon points="12,2 22,8 22,16 12,22 2,16 2,8"
            fill="none" stroke={C.teal} strokeWidth={1.5}/>
          <polygon points="12,6 18,10 18,14 12,18 6,14 6,10"
            fill="none" stroke={C.teal} strokeWidth={1} opacity={0.4}/>
          <circle cx={12} cy={12} r={2.5} fill={C.teal}/>
        </svg>
        <div style={{ textAlign: 'center' }}>
          <div style={{ color: C.teal, fontSize: 28, fontWeight: 700, letterSpacing: 6 }}>AEGIS</div>
          <div style={{ color: C.muted, fontSize: 11, letterSpacing: 3, marginTop: 2 }}>INTELLIGENCE OS</div>
        </div>
      </div>

      {/* Prompt */}
      <div style={{
        color: C.text, fontSize: 17, fontWeight: 600,
        marginBottom: 8, textAlign: 'center',
        animation: 'fadeUp 0.5s 0.1s ease both',
      }}>
        Who are you today?
      </div>
      <div style={{
        color: C.muted, fontSize: 13, marginBottom: 32, textAlign: 'center',
        animation: 'fadeUp 0.5s 0.15s ease both',
      }}>
        Your feed and actions will be tailored to your role.
      </div>

      {/* Role cards */}
      <div style={{
        width: '100%', maxWidth: 420,
        display: 'flex', flexDirection: 'column', gap: 12,
        animation: 'fadeUp 0.5s 0.2s ease both',
      }}>
        {ROLES.map((r, i) => {
          const isSelected = selected === r.role
          const isHover = hovering === r.role
          return (
            <button
              key={r.role}
              onClick={() => setSelected(r.role)}
              onMouseEnter={() => setHovering(r.role)}
              onMouseLeave={() => setHovering(null)}
              style={{
                background: isSelected ? `${r.color}14` : isHover ? `${r.color}08` : C.bg2,
                border: `1.5px solid ${isSelected ? r.color : isHover ? `${r.color}60` : C.border}`,
                borderRadius: 12,
                padding: '16px 18px',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.18s ease',
                boxShadow: isSelected ? `0 0 24px ${r.color}22` : 'none',
                display: 'flex',
                alignItems: 'center',
                gap: 16,
                animationDelay: `${0.25 + i * 0.07}s`,
                animation: 'fadeUp 0.5s ease both',
              }}
            >
              {/* Icon */}
              <div style={{
                width: 44, height: 44, borderRadius: 10,
                background: `${r.color}18`,
                border: `1px solid ${r.color}40`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 20, color: r.color,
                flexShrink: 0,
                filter: isSelected ? `drop-shadow(0 0 8px ${r.color})` : 'none',
                transition: 'filter 0.18s',
              }}>
                {r.icon}
              </div>

              {/* Text */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  color: isSelected ? r.color : C.text,
                  fontSize: 15, fontWeight: 600,
                  transition: 'color 0.18s',
                }}>
                  {r.title}
                </div>
                <div style={{ color: C.muted, fontSize: 12, marginTop: 2 }}>
                  {r.subtitle}
                </div>
                <div style={{
                  display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap',
                }}>
                  {r.tags.map(t => (
                    <span key={t} style={{
                      background: `${r.color}18`,
                      color: r.color,
                      fontSize: 10, fontWeight: 600,
                      letterSpacing: 0.5,
                      padding: '2px 8px', borderRadius: 20,
                    }}>{t}</span>
                  ))}
                </div>
              </div>

              {/* Check */}
              <div style={{
                width: 20, height: 20, borderRadius: '50%',
                border: `1.5px solid ${isSelected ? r.color : C.dim}`,
                background: isSelected ? r.color : 'none',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
                transition: 'all 0.18s',
              }}>
                {isSelected && (
                  <svg width={10} height={10} viewBox="0 0 10 10">
                    <polyline points="2,5 4.5,7.5 8,3" fill="none"
                      stroke={C.bg} strokeWidth={1.5} strokeLinecap="round"/>
                  </svg>
                )}
              </div>
            </button>
          )
        })}
      </div>

      {/* CTA */}
      <button
        onClick={proceed}
        disabled={!selected}
        style={{
          marginTop: 28,
          width: '100%', maxWidth: 420,
          padding: '16px',
          borderRadius: 12,
          border: 'none',
          background: selected ? C.teal : C.dim,
          color: selected ? C.bg : C.muted,
          fontSize: 15, fontWeight: 700, letterSpacing: 1,
          cursor: selected ? 'pointer' : 'not-allowed',
          transition: 'all 0.18s ease',
          boxShadow: selected ? `0 0 24px rgba(61,232,160,0.3)` : 'none',
          animation: 'fadeUp 0.5s 0.45s ease both',
        }}
      >
        Continue →
      </button>

      {/* Divider */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        width: '100%', maxWidth: 420, margin: '20px 0 4px',
        animation: 'fadeUp 0.5s 0.5s ease both',
      }}>
        <div style={{ flex: 1, height: 1, background: C.border }}/>
        <span style={{ color: C.dim, fontSize: 11 }}>or</span>
        <div style={{ flex: 1, height: 1, background: C.border }}/>
      </div>

      {/* One-tap demo */}
      <button
        onClick={startDemo}
        style={{
          width: '100%', maxWidth: 420,
          padding: '14px',
          borderRadius: 12,
          border: `1.5px solid ${C.gold}40`,
          background: `${C.gold}10`,
          color: C.gold,
          fontSize: 14, fontWeight: 600,
          cursor: 'pointer',
          transition: 'all 0.18s ease',
          animation: 'fadeUp 0.5s 0.55s ease both',
        }}
      >
        ★ Explore demo — Alex Tan, Meridian Capital (PE)
      </button>

      {/* Admin access */}
      {!adminOpen ? (
        <button
          onClick={() => setAdminOpen(true)}
          style={{
            marginTop: 18, background: 'none', border: 'none',
            color: C.muted, fontSize: 12, cursor: 'pointer',
            letterSpacing: 0.5, animation: 'fadeUp 0.5s 0.6s ease both',
          }}
        >
          ⛨ Super admin access
        </button>
      ) : (
        <div style={{
          width: '100%', maxWidth: 420, marginTop: 20,
          padding: 16, borderRadius: 12,
          border: `1.5px solid ${C.red}30`, background: `${C.red}08`,
          display: 'flex', flexDirection: 'column', gap: 10,
          animation: 'fadeUp 0.3s ease both',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: C.red, fontSize: 12, fontWeight: 700, letterSpacing: 1 }}>⛨ SUPER ADMIN</span>
            <button onClick={() => { setAdminOpen(false); setAdminError('') }}
              style={{ background: 'none', border: 'none', color: C.muted, cursor: 'pointer', fontSize: 14 }}>×</button>
          </div>
          <input
            type="text" value={adminUser} autoFocus
            onChange={e => { setAdminUser(e.target.value); setAdminError('') }}
            placeholder="Admin username"
            style={{
              padding: '12px 14px', background: C.bg2,
              border: `1.5px solid ${C.border}`, borderRadius: 8,
              color: C.text, fontSize: 14, outline: 'none', fontFamily: 'inherit',
            }}
          />
          <input
            type="password" value={adminPass}
            onChange={e => { setAdminPass(e.target.value); setAdminError('') }}
            onKeyDown={e => e.key === 'Enter' && loginAdmin()}
            placeholder="Passcode"
            style={{
              padding: '12px 14px', background: C.bg2,
              border: `1.5px solid ${adminError ? C.red : C.border}`, borderRadius: 8,
              color: C.text, fontSize: 14, outline: 'none', fontFamily: 'inherit',
            }}
          />
          {adminError && <div style={{ color: C.red, fontSize: 12 }}>{adminError}</div>}
          <button
            onClick={loginAdmin}
            style={{
              padding: '13px', borderRadius: 8, border: 'none',
              background: C.red, color: '#fff',
              fontSize: 14, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
            }}
          >
            Enter as Administrator →
          </button>
        </div>
      )}

      <div style={{
        marginTop: 16, color: C.dim, fontSize: 11, textAlign: 'center',
        animation: 'fadeUp 0.5s 0.6s ease both',
      }}>
        Admin bypasses all profile filters — sees every role's signals merged.
      </div>
    </div>
  )
}
