// ProfileMappingLoader.tsx — brief transition screen after onboarding
import React, { useEffect, useState } from 'react'
import { useAegisStore } from './aegisStore'

const C = {
  bg: '#07100e', teal: '#3de8a0', muted: '#5a8878', dim: '#2a5040', text: '#c8e6d8',
  border: 'rgba(61,232,160,0.12)',
}

const ROLE_LABEL: Record<string, string> = {
  entrepreneur: 'Founder / Entrepreneur',
  counsel: 'General Counsel',
  pe_partner: 'PE / Managing Partner',
}

const STEPS = [
  'Reading your profile…',
  'Mapping jurisdictions…',
  'Calibrating signal filters…',
  'Building your feed…',
]

export default function ProfileMappingLoader({ onDone }: { onDone: () => void }) {
  const userProfile = useAegisStore(s => s.userProfile)
  const [stepIdx, setStepIdx] = useState(0)

  useEffect(() => {
    const timers = STEPS.map((_, i) =>
      setTimeout(() => setStepIdx(i), i * 600)
    )
    const done = setTimeout(onDone, STEPS.length * 600 + 400)
    return () => { timers.forEach(clearTimeout); clearTimeout(done) }
  }, [])

  return (
    <div style={{
      minHeight: '100dvh', background: C.bg,
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      fontFamily: "'Inter', system-ui, sans-serif",
      padding: 32,
    }}>
      <style>{`
        @keyframes pulse { 0%,100%{opacity:1}50%{opacity:0.3} }
        @keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
      `}</style>

      {/* Logo pulse */}
      <svg width={56} height={56} viewBox="0 0 24 24" style={{ marginBottom: 32, animation: 'pulse 2s ease infinite' }}>
        <polygon points="12,2 22,8 22,16 12,22 2,16 2,8" fill="none" stroke={C.teal} strokeWidth={1.5}/>
        <polygon points="12,6 18,10 18,14 12,18 6,14 6,10" fill="none" stroke={C.teal} strokeWidth={1} opacity={0.4}/>
        <circle cx={12} cy={12} r={2.5} fill={C.teal}/>
      </svg>

      {/* Profile summary */}
      {userProfile && (
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{ color: C.teal, fontSize: 13, fontWeight: 700, letterSpacing: 2, marginBottom: 4 }}>
            {ROLE_LABEL[userProfile.role] ?? userProfile.role}
          </div>
          {userProfile.name && (
            <div style={{ color: C.text, fontSize: 20, fontWeight: 700 }}>{userProfile.name}</div>
          )}
          {userProfile.orgData?.name && (
            <div style={{ color: C.muted, fontSize: 14, marginTop: 4 }}>{userProfile.orgData.name}</div>
          )}
        </div>
      )}

      {/* Steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, minWidth: 240 }}>
        {STEPS.map((s, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 12,
            opacity: i <= stepIdx ? 1 : 0.2,
            transition: 'opacity 0.4s ease',
          }}>
            <div style={{
              width: 20, height: 20, borderRadius: '50%',
              border: `1.5px solid ${i < stepIdx ? C.teal : i === stepIdx ? C.teal : C.dim}`,
              background: i < stepIdx ? C.teal : 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, transition: 'all 0.3s',
            }}>
              {i < stepIdx && (
                <svg width={10} height={10} viewBox="0 0 10 10">
                  <polyline points="2,5 4.5,7.5 8,3" fill="none" stroke={C.bg} strokeWidth={1.5} strokeLinecap="round"/>
                </svg>
              )}
              {i === stepIdx && (
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: C.teal, animation: 'pulse 1s ease infinite' }}/>
              )}
            </div>
            <span style={{ color: i <= stepIdx ? C.text : C.dim, fontSize: 14 }}>{s}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
