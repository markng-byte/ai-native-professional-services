// aegisStore.ts — AEGIS Global State (Zustand)
// Shared state accessible by all 4 modules

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type RoleLevel = 'lv1' | 'lv2'
export type RiskAppetite = 'low' | 'medium' | 'high'
export type ActiveModule = 'REGO' | 'VRIT' | 'EIT1' | 'EIT2'

export interface OrgProfile {
  name: string
  sector: string
  geo: string
  risk_appetite: RiskAppetite
  role: string
  role_level: RoleLevel
  sectors: string[]
  assets: string[]
  priorities: string
}

export interface AegisNotification {
  id: string
  type: 'CRITICAL' | 'HIGH' | 'INFO' | 'SUCCESS'
  title: string
  body: string
  source: ActiveModule
  timestamp: number
  read: boolean
}

export interface TickerAlert {
  id: string
  text: string
  level: 'CRITICAL' | 'HIGH'
  source: 'REGO' | 'VRIT'
}

interface AegisState {
  // Navigation
  activeModule: ActiveModule
  setActiveModule: (m: ActiveModule) => void
  sidebarCollapsed: boolean
  setSidebarCollapsed: (v: boolean) => void

  // Org Profile
  orgProfile: OrgProfile | null
  setOrgProfile: (p: OrgProfile) => void
  profileComplete: boolean

  // Global Risk Score (aggregated from all modules)
  globalRiskScore: number
  setGlobalRiskScore: (score: number) => void

  // Ticker
  tickerAlerts: TickerAlert[]
  addTickerAlert: (a: TickerAlert) => void

  // Notifications
  notifications: AegisNotification[]
  addNotification: (n: Omit<AegisNotification, 'id' | 'timestamp' | 'read'>) => void
  markAllRead: () => void
  unreadCount: number

  // Cross-module signal queues
  newsfeedQueue: unknown[]          // signals pushed from REGO/VRIT
  addToNewsfeedQueue: (s: unknown) => void
  clearNewsfeedQueue: () => void

  warRoomQueue: unknown[]           // escalated cards from EIT1
  addToWarRoomQueue: (c: unknown) => void
  clearWarRoomQueue: () => void

  // API Bridge status
  apiBridgeConnected: boolean
  setApiBridgeConnected: (v: boolean) => void
}

export const useAegisStore = create<AegisState>()(
  persist(
    (set, get) => ({
      // Navigation
      activeModule: 'REGO',
      setActiveModule: (m) => set({ activeModule: m }),
      sidebarCollapsed: false,
      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),

      // Org Profile
      orgProfile: null,
      setOrgProfile: (p) => set({ orgProfile: p, profileComplete: true }),
      profileComplete: false,

      // Global Risk Score
      globalRiskScore: 0,
      setGlobalRiskScore: (score) => set({ globalRiskScore: score }),

      // Ticker
      tickerAlerts: [
        { id: '1', text: 'FATF Plenary: Travel Rule enforcement deadline — 30 days', level: 'CRITICAL', source: 'REGO' },
        { id: '2', text: 'SBV Draft Circular 02/2026 open for consultation — closes May 25', level: 'HIGH', source: 'VRIT' },
        { id: '3', text: 'MiCA Phase 2 stablecoin provisions effective June 30', level: 'CRITICAL', source: 'REGO' },
        { id: '4', text: 'SEC Vietnam digital asset framework — public hearing May 20', level: 'HIGH', source: 'VRIT' },
      ],
      addTickerAlert: (a) => set((s) => ({ tickerAlerts: [a, ...s.tickerAlerts].slice(0, 20) })),

      // Notifications
      notifications: [],
      addNotification: (n) => {
        const notif: AegisNotification = {
          ...n, id: `n_${Date.now()}`, timestamp: Date.now(), read: false
        }
        set((s) => ({
          notifications: [notif, ...s.notifications].slice(0, 50),
          unreadCount: s.unreadCount + 1,
        }))
      },
      markAllRead: () => set((s) => ({
        notifications: s.notifications.map(n => ({ ...n, read: true })),
        unreadCount: 0,
      })),
      unreadCount: 0,

      // Cross-module queues
      newsfeedQueue: [],
      addToNewsfeedQueue: (s) => set((st) => ({ newsfeedQueue: [...st.newsfeedQueue, s] })),
      clearNewsfeedQueue: () => set({ newsfeedQueue: [] }),

      warRoomQueue: [],
      addToWarRoomQueue: (c) => set((st) => ({ warRoomQueue: [...st.warRoomQueue, c] })),
      clearWarRoomQueue: () => set({ warRoomQueue: [] }),

      // API Bridge
      apiBridgeConnected: false,
      setApiBridgeConnected: (v) => set({ apiBridgeConnected: v }),
    }),
    {
      name: 'aegis-store',
      partialize: (s) => ({
        orgProfile: s.orgProfile,
        profileComplete: s.profileComplete,
        sidebarCollapsed: s.sidebarCollapsed,
        activeModule: s.activeModule,
      }),
    } as Parameters<typeof persist>[1]
  )
)
