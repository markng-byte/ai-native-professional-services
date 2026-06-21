// aegisStore.ts — AEGIS Global State (Zustand)
// Shared state accessible by all 4 modules

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type RoleLevel = 'lv1' | 'lv2'
export type RiskAppetite = 'low' | 'medium' | 'high'
export type ActiveModule = 'REGO' | 'VRIT' | 'EIT1' | 'EIT2'
export type ActiveView = 'FEED' | ActiveModule

export type UserRole = 'entrepreneur' | 'counsel' | 'pe_partner'

export interface OrgData {
  name: string
  country: string
  sector: string
  registrationId: string
  verified: boolean
  raw: Record<string, unknown>
}

export interface UserProfile {
  role: UserRole
  name: string
  jurisdictions: string[]
  sectors: string[]
  onboardingComplete: boolean
  orgData: OrgData | null
}

export interface Signal {
  id: string
  title: string
  summary: string
  confidence: number          // 0–100
  level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  sources: string[]
  sourceCount: number
  tags: string[]
  timestamp: number
  jurisdiction: string
  actions: SignalAction[]
}

export interface SignalAction {
  label: string
  module: ActiveModule
  icon: string
}

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
  activeView: ActiveView
  setActiveView: (v: ActiveView) => void
  sidebarCollapsed: boolean
  setSidebarCollapsed: (v: boolean) => void

  // User Profile (login / onboarding)
  userProfile: UserProfile | null
  setUserProfile: (p: UserProfile) => void
  clearUserProfile: () => void
  feedInitialized: boolean
  setFeedInitialized: (v: boolean) => void

  // Signal Feed
  signals: Signal[]
  setSignals: (s: Signal[]) => void
  addSignal: (s: Signal) => void

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
      setActiveModule: (m) => set({ activeModule: m, activeView: m }),
      activeView: 'FEED',
      setActiveView: (v) => set({ activeView: v }),
      sidebarCollapsed: false,
      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),

      // User Profile
      userProfile: null,
      setUserProfile: (p) => set({ userProfile: p }),
      clearUserProfile: () => set({ userProfile: null, signals: [], feedInitialized: false }),
      feedInitialized: false,
      setFeedInitialized: (v: boolean) => set({ feedInitialized: v }),

      // Signal Feed
      signals: [],
      setSignals: (s) => set({ signals: s }),
      addSignal: (s) => set((st) => ({ signals: [s, ...st.signals].slice(0, 100) })),

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
      name: 'aegis-store-v2',   // bumped: clears old persisted state
      partialize: (s) => ({
        userProfile: s.userProfile,
        orgProfile: s.orgProfile,
        profileComplete: s.profileComplete,
        sidebarCollapsed: s.sidebarCollapsed,
        activeModule: s.activeModule,
        feedInitialized: s.feedInitialized,
      }),
    } as Parameters<typeof persist>[1]
  )
)
