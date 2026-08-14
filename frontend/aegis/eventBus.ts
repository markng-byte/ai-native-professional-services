// eventBus.ts — AEGIS Cross-Module Event System
// Emits signals between modules without tight coupling

export type AegisEventType =
  | 'CRITICAL_SIGNAL'       // REGO → Newsfeed
  | 'PUSH_TO_NEWSFEED'      // VRIT → Newsfeed
  | 'PUSH_TO_WARROOM'       // EIT1 → War Room (escalated card)
  | 'SIMULATION_COMPLETE'   // EIT2 → Newsfeed (report card)
  | 'PROFILE_UPDATED'       // Shell → all modules
  | 'NOTIFICATION'          // any → notification center

export interface AegisEvent {
  type: AegisEventType
  source: 'REGO' | 'VRIT' | 'EIT1' | 'EIT2' | 'SHELL'
  payload: unknown
  timestamp: number
}

type Listener = (event: AegisEvent) => void

class EventBus {
  private listeners: Map<AegisEventType, Listener[]> = new Map()

  on(type: AegisEventType, listener: Listener) {
    if (!this.listeners.has(type)) this.listeners.set(type, [])
    this.listeners.get(type)!.push(listener)
  }

  off(type: AegisEventType, listener: Listener) {
    const list = this.listeners.get(type) ?? []
    this.listeners.set(type, list.filter(l => l !== listener))
  }

  emit(type: AegisEventType, source: AegisEvent['source'], payload: unknown) {
    const event: AegisEvent = { type, source, payload, timestamp: Date.now() }
    const list = this.listeners.get(type) ?? []
    list.forEach(l => l(event))
  }
}

export const aegisBus = new EventBus()
