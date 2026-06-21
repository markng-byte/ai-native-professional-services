// aegis.tsx — AEGIS Unified Shell
// The single entry point that houses all 4 intelligence modules

import React, { Suspense, useEffect, useRef, useState } from 'react'
import { useAegisStore, ActiveModule, AegisNotification } from './aegisStore'
import { aegisBus } from './eventBus'
import { ModuleErrorBoundary } from './ModuleErrorBoundary'
import LoginScreen from './LoginScreen'
import OnboardingFlow from './OnboardingFlow'
import ProfileMappingLoader from './ProfileMappingLoader'
import SignalFeed from './SignalFeed'

// ─── Lazy-load modules (keeps bundle fast) ──────────────────────────────────
const MacroRadar  = React.lazy(() => import('./rego_dashboard_v4'))
const LocalIntel  = React.lazy(() => import('./vrit_v4'))
const Newsfeed    = React.lazy(() => import('./eit_module1'))
const WarRoom     = React.lazy(() => import('./eit_module2'))

// ─── Design tokens (shared, matches all 4 modules) ───────────────────────────
const C = {
  bg:    '#07100e',
  bg2:   '#0b1a16',
  bg3:   '#0f2018',
  teal:  '#3de8a0',
  gold:  '#f0c040',
  green: '#00ee77',
  red:   '#f05060',
  blue:  '#40b0f0',
  muted: '#5a8878',
  dim:   '#2a5040',
  text:  '#c8e6d8',
  glow:  '0 0 16px rgba(61,232,160,0.22)',
  border:'rgba(61,232,160,0.12)',
}

// ─── Module Config ───────────────────────────────────────────────────────────
const MODULES: {
  id: ActiveModule; label: string; shortLabel: string;
  icon: string; color: string; desc: string
}[] = [
  { id:'REGO', label:'Macro Radar',          shortLabel:'RADAR', icon:'⬡', color: C.gold,  desc:'Global regulatory intelligence' },
  { id:'VRIT', label:'Local Intel',          shortLabel:'INTEL', icon:'◈', color: C.green, desc:'Vietnam / SEA local signals' },
  { id:'EIT1', label:'Intelligence Newsfeed',shortLabel:'NEWS',  icon:'▦', color: C.teal,  desc:'Signal synthesis & pipeline' },
  { id:'EIT2', label:'War Room',             shortLabel:'WAR',   icon:'★', color: C.red,   desc:'Scenario planning & simulation' },
]

// ─── Loading Fallback ─────────────────────────────────────────────────────────
function ModuleLoader({ color }: { color: string }) {
  return (
    <div style={{
      display:'flex', flexDirection:'column', alignItems:'center',
      justifyContent:'center', height:'100%', gap:24,
    }}>
      <div style={{
        width:48, height:48, borderRadius:'50%',
        border:`2px solid ${color}`, borderTopColor:'transparent',
        animation:'aegis-spin 0.8s linear infinite',
      }}/>
      <div style={{ color: C.muted, fontSize:13, letterSpacing:2 }}>LOADING MODULE</div>
    </div>
  )
}

// ─── Global Ticker ────────────────────────────────────────────────────────────
function GlobalTicker() {
  const alerts = useAegisStore(s => s.tickerAlerts)
  const addTickerAlert = useAegisStore(s => s.addTickerAlert)
  const [tickKey, setTickKey] = useState(0)
  const prevLen = useRef(alerts.length)

  // Restart animation when new items arrive
  useEffect(() => {
    if (alerts.length !== prevLen.current) {
      prevLen.current = alerts.length
      setTickKey(k => k + 1)
    }
  }, [alerts.length])

  // Fetch RSS headlines once and push to ticker
  useEffect(() => {
    const base = (import.meta as any).env?.VITE_API_BASE || ''
    fetch(`${base}/api/news/feed`, { signal: AbortSignal.timeout(8000) })
      .then(r => r.json())
      .then(d => {
        ;(d.items || []).slice(0, 10).forEach((item: any, i: number) => {
          setTimeout(() => {
            addTickerAlert({
              id: `rss_${i}_${Date.now()}`,
              level: 'HIGH',
              source: item.source || 'NEWS',
              text: item.title,
            })
          }, i * 400)
        })
      })
      .catch(() => {})
  }, [])

  // Speed: chars / s ≈ text.length / duration. ~120px/s feels right.
  const text = alerts.map(a => `[ ${a.level} · ${a.source} ]  ${a.text}`).join('          ·          ')
  const duration = Math.max(20, text.length * 0.12)

  return (
    <div style={{
      height: 28, background: C.bg2, borderBottom: `1px solid ${C.border}`,
      overflow: 'hidden', display: 'flex', alignItems: 'center',
    }}>
      <div style={{
        background: C.red, color: '#fff', fontSize: 10, fontWeight: 700,
        letterSpacing: 2, padding: '0 12px', height: '100%',
        display: 'flex', alignItems: 'center', flexShrink: 0,
      }}>LIVE</div>
      <div style={{ overflow: 'hidden', flex: 1 }}>
        <div
          key={tickKey}
          style={{
            display: 'inline-block',
            color: C.text, fontSize: 11, letterSpacing: 0.5,
            whiteSpace: 'nowrap', paddingLeft: '100%',
            animation: `aegis-ticker ${duration}s linear infinite`,
          }}
        >
          {text}
        </div>
      </div>
    </div>
  )
}

// ─── Board Strip (bottom) ────────────────────────────────────────────────────
function BoardStrip() {
  const score = useAegisStore(s => s.globalRiskScore)
  const [open, setOpen] = useState(false)
  const scoreColor = score > 70 ? C.red : score > 40 ? C.gold : C.teal
  return (
    <div style={{
      background: C.bg2, borderTop:`1px solid ${C.border}`,
      display:'flex', alignItems:'center', padding:'0 20px',
      height: open ? 64 : 32, transition:'height 0.2s ease',
      flexShrink:0,
    }}>
      <div style={{ display:'flex', alignItems:'center', gap:16, flex:1 }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ color: C.muted, fontSize:10, letterSpacing:1 }}>GLOBAL RISK</span>
          <span style={{ color: scoreColor, fontSize:16, fontWeight:700 }}>{score || '—'}</span>
        </div>
        <div style={{ width:1, height:16, background: C.border }}/>
        <span style={{ color: C.muted, fontSize:10 }}>
          FATF Deadline: <span style={{ color: C.gold }}>30d</span>
        </span>
        <div style={{ width:1, height:16, background: C.border }}/>
        <span style={{ color: C.muted, fontSize:10 }}>
          SBV Circular: <span style={{ color: C.gold }}>12d</span>
        </span>
      </div>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          background:'none', border:`1px solid ${C.border}`, borderRadius:4,
          color: C.teal, fontSize:10, letterSpacing:1, padding:'3px 10px',
          cursor:'pointer', transition:'all 0.15s',
        }}
      >
        BOARD BRIEF {open ? '▼' : '▲'}
      </button>
    </div>
  )
}

// ─── Notification Panel ──────────────────────────────────────────────────────
function NotificationPanel({ onClose }: { onClose: () => void }) {
  const { notifications, markAllRead } = useAegisStore()
  useEffect(() => { markAllRead() }, [])
  const levelColor = (n: AegisNotification) =>
    n.type === 'CRITICAL' ? C.red : n.type === 'HIGH' ? C.gold : C.teal
  return (
    <div style={{
      position:'absolute', top:48, right:16, width:340, maxHeight:480,
      background: C.bg3, border:`1px solid ${C.border}`, borderRadius:8,
      boxShadow:'0 8px 32px rgba(0,0,0,0.6)', overflow:'hidden',
      zIndex:200, display:'flex', flexDirection:'column',
    }}>
      <div style={{
        padding:'12px 16px', borderBottom:`1px solid ${C.border}`,
        display:'flex', justifyContent:'space-between', alignItems:'center',
      }}>
        <span style={{ color: C.teal, fontSize:12, letterSpacing:2, fontWeight:700 }}>NOTIFICATIONS</span>
        <button onClick={onClose} style={{
          background:'none', border:'none', color: C.muted, cursor:'pointer', fontSize:16,
        }}>×</button>
      </div>
      <div style={{ overflowY:'auto', flex:1 }}>
        {notifications.length === 0 ? (
          <div style={{ padding:24, color: C.muted, fontSize:12, textAlign:'center' }}>
            No notifications
          </div>
        ) : notifications.map(n => (
          <div key={n.id} style={{
            padding:'10px 16px', borderBottom:`1px solid ${C.border}`,
            display:'flex', gap:10,
          }}>
            <div style={{
              width:6, height:6, borderRadius:'50%', marginTop:4, flexShrink:0,
              background: levelColor(n),
              boxShadow:`0 0 8px ${levelColor(n)}`,
            }}/>
            <div>
              <div style={{ color: C.text, fontSize:12, marginBottom:2 }}>{n.title}</div>
              <div style={{ color: C.muted, fontSize:11 }}>{n.body}</div>
              <div style={{ color: C.dim, fontSize:10, marginTop:4 }}>
                {n.source} · {new Date(n.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── API Status Bar ───────────────────────────────────────────────────────────
interface ApiServices { anthropic: boolean; neo4j: boolean; airtable: boolean }

function ApiStatusBar() {
  const connected = useAegisStore(s => s.apiBridgeConnected)
  const [services, setServices] = useState<ApiServices | null>(null)

  useEffect(() => {
    const base = (import.meta as any).env?.VITE_API_BASE || ''
    fetch(`${base}/api/health`, { signal: AbortSignal.timeout(3000) })
      .then(r => r.json())
      .then(d => d.services && setServices(d.services))
      .catch(() => {})
  }, [connected])

  const dot = (on: boolean, label: string) => (
    <div key={label} style={{ display:'flex', alignItems:'center', gap:4 }}>
      <div style={{
        width:5, height:5, borderRadius:'50%',
        background: on ? C.teal : C.muted,
        boxShadow: on ? `0 0 6px ${C.teal}` : 'none',
      }}/>
      <span style={{ color: on ? C.muted : C.dim, fontSize:9, letterSpacing:.5 }}>{label}</span>
    </div>
  )

  return (
    <div style={{ display:'flex', alignItems:'center', gap:10 }}>
      {dot(connected, 'FIRM OS')}
      {services && <>
        {dot(services.anthropic, 'CLAUDE')}
        {dot(services.neo4j,    'GRAPH')}
        {dot(services.airtable, 'AIRTABLE')}
      </>}
    </div>
  )
}

// ─── Change Profile button ────────────────────────────────────────────────────
function ChangeProfileBtn({ sm }: { sm?: boolean }) {
  const { clearUserProfile, setFeedInitialized } = useAegisStore()
  return (
    <button
      onClick={() => { clearUserProfile(); setFeedInitialized(false) }}
      title="Switch profile / demo role"
      style={{
        background:'none',
        border:`1px solid ${C.border}`,
        borderRadius:6,
        color: C.muted,
        fontSize: sm ? 10 : 11,
        letterSpacing:.5,
        padding: sm ? '3px 8px' : '4px 10px',
        cursor:'pointer',
        transition:'color 0.15s',
        whiteSpace:'nowrap',
      }}
    >
      ⇄ {sm ? '' : 'Change Profile'}
    </button>
  )
}

// ─── Topbar ───────────────────────────────────────────────────────────────────
function TopBar() {
  const [notifOpen, setNotifOpen] = useState(false)
  const unread = useAegisStore(s => s.unreadCount)
  const activeModule = useAegisStore(s => s.activeModule)
  const mod = MODULES.find(m => m.id === activeModule)!

  return (
    <div style={{
      height:48, background: C.bg2, borderBottom:`1px solid ${C.border}`,
      display:'flex', alignItems:'center', padding:'0 20px',
      flexShrink:0, position:'relative', zIndex:100,
    }}>
      {/* Logo */}
      <div style={{ display:'flex', alignItems:'center', gap:10, minWidth:180 }}>
        <svg width={24} height={24} viewBox="0 0 24 24">
          <polygon points="12,2 22,8 22,16 12,22 2,16 2,8" fill="none" stroke={C.teal} strokeWidth={1.5}/>
          <polygon points="12,6 18,10 18,14 12,18 6,14 6,10" fill="none" stroke={C.teal} strokeWidth={1} opacity={0.5}/>
          <circle cx={12} cy={12} r={2} fill={C.teal}/>
        </svg>
        <div>
          <div style={{ color: C.teal, fontSize:15, fontWeight:700, letterSpacing:3 }}>AEGIS</div>
          <div style={{ color: C.dim, fontSize:9, letterSpacing:2, marginTop:-2 }}>INTELLIGENCE OS</div>
        </div>
      </div>

      {/* Active module breadcrumb */}
      <div style={{ flex:1, display:'flex', alignItems:'center', gap:8, paddingLeft:20 }}>
        <div style={{ width:1, height:20, background: C.border }}/>
        <span style={{ color: mod.color, fontSize:12, letterSpacing:2 }}>{mod.icon}</span>
        <span style={{ color: C.text, fontSize:13, letterSpacing:1 }}>{mod.label}</span>
        <span style={{ color: C.muted, fontSize:11 }}>— {mod.desc}</span>
      </div>

      {/* Right cluster */}
      <div style={{ display:'flex', alignItems:'center', gap:12 }}>
        <ApiStatusBar />
        <ChangeProfileBtn />

        {/* Notification bell */}
        <button
          onClick={() => setNotifOpen(v => !v)}
          style={{
            position:'relative', background:'none', border:'none',
            color: unread > 0 ? C.teal : C.muted,
            cursor:'pointer', fontSize:16, padding:4,
          }}
        >
          ◎
          {unread > 0 && (
            <div style={{
              position:'absolute', top:0, right:0,
              background: C.red, color:'#fff',
              fontSize:9, width:14, height:14, borderRadius:'50%',
              display:'flex', alignItems:'center', justifyContent:'center', fontWeight:700,
            }}>{unread}</div>
          )}
        </button>

        {/* Settings */}
        <button style={{
          background:'none', border:`1px solid ${C.border}`, borderRadius:4,
          color: C.muted, fontSize:11, letterSpacing:1, padding:'4px 10px',
          cursor:'pointer',
        }}>⚙ SETTINGS</button>
      </div>

      {notifOpen && <NotificationPanel onClose={() => setNotifOpen(false)} />}
    </div>
  )
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────
function Sidebar() {
  const { activeModule, setActiveModule, sidebarCollapsed, setSidebarCollapsed } = useAegisStore()
  const width = sidebarCollapsed ? 56 : 200

  return (
    <div style={{
      width, flexShrink:0, background: C.bg2,
      borderRight:`1px solid ${C.border}`,
      display:'flex', flexDirection:'column',
      transition:'width 0.2s ease', overflow:'hidden',
    }}>
      {/* Collapse toggle */}
      <button
        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        style={{
          background:'none', border:'none', borderBottom:`1px solid ${C.border}`,
          color: C.muted, cursor:'pointer', padding:'12px 16px',
          textAlign:'right', fontSize:14,
        }}
      >
        {sidebarCollapsed ? '›' : '‹'}
      </button>

      {/* Module nav */}
      <nav style={{ flex:1, padding:'8px 0' }}>
        {MODULES.map(m => {
          const active = activeModule === m.id
          return (
            <button
              key={m.id}
              onClick={() => setActiveModule(m.id)}
              title={m.label}
              style={{
                display:'flex', alignItems:'center', gap:12,
                width:'100%', padding:'10px 16px',
                background: active ? `${m.color}12` : 'none',
                border:'none', borderLeft:`3px solid ${active ? m.color : 'transparent'}`,
                cursor:'pointer', transition:'all 0.15s',
                textAlign:'left',
              }}
            >
              <span style={{
                fontSize:16, color: active ? m.color : C.muted,
                flexShrink:0,
                filter: active ? `drop-shadow(0 0 6px ${m.color})` : 'none',
              }}>{m.icon}</span>
              {!sidebarCollapsed && (
                <div>
                  <div style={{
                    color: active ? m.color : C.text, fontSize:11,
                    fontWeight:700, letterSpacing:1,
                  }}>{m.shortLabel}</div>
                  <div style={{ color: C.muted, fontSize:10, marginTop:1 }}>{m.desc}</div>
                </div>
              )}
            </button>
          )
        })}
      </nav>

      {/* Bottom info */}
      {!sidebarCollapsed && (
        <div style={{
          borderTop:`1px solid ${C.border}`, padding:12,
          color: C.dim, fontSize:9, letterSpacing:1,
        }}>
          <div>AEGIS v1.0</div>
          <div style={{ marginTop:2 }}>INTERNAL BUILD</div>
        </div>
      )}
    </div>
  )
}

// ─── Bottom Nav (mobile) ─────────────────────────────────────────────────────
function BottomNav() {
  const { activeView, setActiveView, setActiveModule } = useAegisStore()

  const items = [
    { id: 'FEED', icon: '⊡', label: 'Feed', color: C.teal },
    ...MODULES.map(m => ({ id: m.id, icon: m.icon, label: m.shortLabel, color: m.color })),
  ]

  return (
    <div style={{
      height: 60, background: C.bg2,
      borderTop: `1px solid ${C.border}`,
      display: 'flex', alignItems: 'stretch',
      flexShrink: 0,
    }}>
      {items.map(item => {
        const active = activeView === item.id
        return (
          <button
            key={item.id}
            onClick={() => {
              setActiveView(item.id as any)
              if (item.id !== 'FEED') setActiveModule(item.id as ActiveModule)
            }}
            style={{
              flex: 1, display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', gap: 3,
              background: 'none', border: 'none',
              borderTop: `2px solid ${active ? item.color : 'transparent'}`,
              cursor: 'pointer', transition: 'all 0.15s',
            }}
          >
            <span style={{
              fontSize: 18, color: active ? item.color : C.dim,
              filter: active ? `drop-shadow(0 0 6px ${item.color})` : 'none',
              transition: 'all 0.15s',
            }}>{item.icon}</span>
            <span style={{
              fontSize: 9, letterSpacing: 1, fontWeight: 700,
              color: active ? item.color : C.dim,
            }}>{item.label}</span>
          </button>
        )
      })}
    </div>
  )
}

// ─── Module Viewport ──────────────────────────────────────────────────────────
function ModuleViewport() {
  const { activeView, activeModule } = useAegisStore()
  const mod = MODULES.find(m => m.id === activeModule)!

  if (activeView === 'FEED') {
    return (
      <div style={{ flex: 1, overflow: 'auto', position: 'relative', display: 'flex', flexDirection: 'column' }}>
        <SignalFeed />
      </div>
    )
  }

  return (
    <div style={{ flex:1, overflow:'auto', position:'relative', display:'flex', flexDirection:'column' }}>
      <Suspense fallback={<ModuleLoader color={mod.color} />}>
        {activeModule === 'REGO' && (
          <ModuleErrorBoundary moduleName='MACRO RADAR' moduleColor={MODULES[0].color}>
            <MacroRadar />
          </ModuleErrorBoundary>
        )}
        {activeModule === 'VRIT' && (
          <ModuleErrorBoundary moduleName='LOCAL INTEL' moduleColor={MODULES[1].color}>
            <LocalIntel />
          </ModuleErrorBoundary>
        )}
        {activeModule === 'EIT1' && (
          <ModuleErrorBoundary moduleName='INTELLIGENCE NEWSFEED' moduleColor={MODULES[2].color}>
            <Newsfeed />
          </ModuleErrorBoundary>
        )}
        {activeModule === 'EIT2' && (
          <ModuleErrorBoundary moduleName='WAR ROOM' moduleColor={MODULES[3].color}>
            <WarRoom />
          </ModuleErrorBoundary>
        )}
      </Suspense>
    </div>
  )
}

// ─── EventBus wiring ──────────────────────────────────────────────────────────
function useEventBusWiring() {
  const { addToNewsfeedQueue, addToWarRoomQueue, addNotification, addTickerAlert, addSignal } = useAegisStore()

  useEffect(() => {
    // REGO CRITICAL → push to Signal Feed + Newsfeed queue + ticker + notification
    const onCritical = (e: Parameters<typeof aegisBus.on>[1] extends (e: infer E) => void ? E : never) => {
      const payload = e.payload as { title?: string; zone?: string; tag?: string } | undefined
      addToNewsfeedQueue(e.payload)
      // Push into the global Signal Feed
      addSignal({
        id: `rego_${Date.now()}`,
        title: payload?.title ?? 'Critical regulatory signal',
        summary: `Macro Radar flagged a critical signal${payload?.zone ? ` in ${payload.zone}` : ''}.`,
        confidence: 85,
        level: 'CRITICAL',
        sources: ['REGO Macro Radar'],
        sourceCount: 1,
        tags: ['REGO', payload?.zone ?? 'GLOBAL'],
        timestamp: Date.now(),
        jurisdiction: payload?.zone ?? 'GLOBAL',
        actions: [
          { label: 'Analyze Signal', module: 'REGO', icon: '⬡' },
          { label: 'Run Scenario', module: 'EIT2', icon: '★' },
        ],
      })
      addTickerAlert({
        id: `t_${Date.now()}`, level:'CRITICAL', source:'REGO',
        text: payload?.title ?? 'New critical regulatory signal',
      })
      addNotification({
        type:'CRITICAL', source:'REGO',
        title:'CRITICAL Signal — Macro Radar',
        body: payload?.title ?? 'A critical regulatory event requires your attention.',
      })
    }

    // VRIT push → Newsfeed
    const onVritPush = (e: Parameters<typeof aegisBus.on>[1] extends (e: infer E) => void ? E : never) => {
      addToNewsfeedQueue(e.payload)
      addNotification({
        type:'HIGH', source:'VRIT',
        title:'Local Intel — Document Pushed',
        body:'A VRIT document has been added to the Newsfeed pipeline.',
      })
    }

    // EIT1 escalation → War Room
    const onEscalate = (e: Parameters<typeof aegisBus.on>[1] extends (e: infer E) => void ? E : never) => {
      addToWarRoomQueue(e.payload)
      addNotification({
        type:'HIGH', source:'EIT1',
        title:'Card Escalated to War Room',
        body:'An intelligence card has been escalated as a War Room bear-case driver.',
      })
    }

    // EIT2 simulation complete → notification
    const onSimComplete = (e: Parameters<typeof aegisBus.on>[1] extends (e: infer E) => void ? E : never) => {
      addNotification({
        type:'SUCCESS', source:'EIT2',
        title:'War Room Simulation Complete',
        body:'Scenario analysis ready. Results available in the Intelligence Newsfeed.',
      })
    }

    aegisBus.on('CRITICAL_SIGNAL',    onCritical)
    aegisBus.on('PUSH_TO_NEWSFEED',   onVritPush)
    aegisBus.on('PUSH_TO_WARROOM',    onEscalate)
    aegisBus.on('SIMULATION_COMPLETE', onSimComplete)

    return () => {
      aegisBus.off('CRITICAL_SIGNAL',    onCritical)
      aegisBus.off('PUSH_TO_NEWSFEED',   onVritPush)
      aegisBus.off('PUSH_TO_WARROOM',    onEscalate)
      aegisBus.off('SIMULATION_COMPLETE', onSimComplete)
    }
  }, [])
}

// ─── API Bridge health check ──────────────────────────────────────────────────
function useApiBridgeCheck() {
  const setConnected = useAegisStore(s => s.setApiBridgeConnected)
  useEffect(() => {
    const check = async () => {
      try {
        const base = (import.meta as any).env?.VITE_API_BASE || ''
        const res = await fetch(`${base}/api/health`, { signal: AbortSignal.timeout(2000) })
        setConnected(res.ok)
      } catch {
        setConnected(false)
      }
    }
    check()
    const interval = setInterval(check, 30_000)
    return () => clearInterval(interval)
  }, [])
}

// ─── CSS Keyframes injector ───────────────────────────────────────────────────
function GlobalStyles() {
  return (
    <style>{`
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
      html, body, #root { height: 100%; background: ${C.bg}; font-family: 'Inter', system-ui, sans-serif; }
      @keyframes aegis-ticker {
        from { transform: translateX(0); }
        to   { transform: translateX(-100%); }
      }
      @keyframes aegis-spin {
        to { transform: rotate(360deg); }
      }
      @keyframes aegis-pulse {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0.4; }
      }
      ::-webkit-scrollbar { width: 4px; height: 4px; }
      ::-webkit-scrollbar-track { background: ${C.bg}; }
      ::-webkit-scrollbar-thumb { background: ${C.dim}; border-radius: 2px; }
      ::-webkit-scrollbar-thumb:hover { background: ${C.muted}; }
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    `}</style>
  )
}

// ─── useIsMobile ─────────────────────────────────────────────────────────────
function useIsMobile() {
  const [mobile, setMobile] = useState(() => window.innerWidth < 768)
  useEffect(() => {
    const handler = () => setMobile(window.innerWidth < 768)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])
  return mobile
}

// ─── Root ───────────────────────────────────────────────────────────────
export default function Aegis() {
  useEventBusWiring()
  useApiBridgeCheck()
  const isMobile = useIsMobile()
  const userProfile = useAegisStore(s => s.userProfile)
  const feedInitialized = useAegisStore(s => s.feedInitialized)
  const setFeedInitialized = useAegisStore(s => s.setFeedInitialized)

  // Not logged in → Login screen
  if (!userProfile) {
    return (
      <>
        <GlobalStyles />
        <LoginScreen />
      </>
    )
  }

  // Logged in but not onboarded → Onboarding flow
  if (!userProfile.onboardingComplete) {
    return (
      <>
        <GlobalStyles />
        <OnboardingFlow />
      </>
    )
  }

  // Just finished onboarding → mapping loader (once ever, persisted)
  if (!feedInitialized) {
    return (
      <>
        <GlobalStyles />
        <ProfileMappingLoader onDone={() => setFeedInitialized(true)} />
      </>
    )
  }

  // Mobile layout — bottom nav, no sidebar
  if (isMobile) {
    return (
      <>
        <GlobalStyles />
        <div style={{
          display: 'flex', flexDirection: 'column',
          height: '100dvh', overflow: 'hidden',
          background: C.bg, color: C.text,
        }}>
          {/* Compact top bar on mobile */}
          <div style={{
            height: 44, background: C.bg2,
            borderBottom: `1px solid ${C.border}`,
            display: 'flex', alignItems: 'center',
            padding: '0 16px', flexShrink: 0,
          }}>
            <svg width={20} height={20} viewBox="0 0 24 24">
              <polygon points="12,2 22,8 22,16 12,22 2,16 2,8"
                fill="none" stroke={C.teal} strokeWidth={1.5}/>
              <circle cx={12} cy={12} r={2} fill={C.teal}/>
            </svg>
            <span style={{ color: C.teal, fontSize: 13, fontWeight: 700, letterSpacing: 3, marginLeft: 8 }}>AEGIS</span>
            <div style={{ flex: 1 }}/>
            <ApiStatusBar />
            <div style={{ width: 8 }}/>
            <ChangeProfileBtn sm />
          </div>
          {/* Live ticker on mobile */}
          <GlobalTicker />

          <ModuleViewport />
          <BottomNav />
        </div>
      </>
    )
  }

  // Desktop layout — sidebar + topbar
  return (
    <>
      <GlobalStyles />
      <div style={{
        display:'flex', flexDirection:'column',
        height:'100vh', overflow:'hidden', background: C.bg,
        color: C.text,
      }}>
        <GlobalTicker />
        <div style={{ display:'flex', flex:1, overflow:'hidden' }}>
          <Sidebar />
          <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
            <TopBar />
            <ModuleViewport />
            <BoardStrip />

          </div>
        </div>
      </div>
    </>
  )
}
