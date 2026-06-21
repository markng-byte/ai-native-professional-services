// aegisApi.ts — single shared client between the AEGIS React shell (L6) and
// the Firm OS API Bridge (src/api_bridge.py). All AI calls go through here so
// provider keys stay server-side and every request hits a Firm OS agent.
//
// Drop this file next to the AEGIS module files (sibling of eventBus.ts /
// aegisStore.ts) and import as `./aegisApi`.

const BASE =
  (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_BASE) ||
  "http://localhost:8000";

// Standard envelope returned by every bridge endpoint.
export interface AegisMeta {
  agent: string;
  simulation: boolean;
  requires_human_review: boolean;
  sources: Array<{ node_id?: string; label?: string } | string>;
  model: string;
  run_id: string;
  timestamp: string;
}
export interface AegisEnvelope<T = any> {
  data: T;
  meta: AegisMeta;
}

// Keep the meta around for callers that want the simulation/review badges,
// while returning `data` directly for ergonomic use.
export class AegisApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "AegisApiError";
  }
}

async function post<T = any>(path: string, body: unknown): Promise<AegisEnvelope<T>> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!r.ok) throw new AegisApiError(r.status, `${path} → ${r.status}`);
  return (await r.json()) as AegisEnvelope<T>;
}

async function get<T = any>(path: string): Promise<AegisEnvelope<T>> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new AegisApiError(r.status, `${path} → ${r.status}`);
  return (await r.json()) as AegisEnvelope<T>;
}

// ── SSE helper (EIT1 ingestion pipeline) ────────────────────────────────────
export type SseEvent =
  | { type: "stage"; stage: string; log: string; progress: number }
  | { type: "log"; log: string }
  | { type: "result"; data: any; meta: AegisMeta }
  | { type: "done"; log: string; progress: number };

// Streams POST SSE responses (EventSource is GET-only, so we read the body).
async function postStream(
  path: string,
  body: unknown,
  onEvent: (e: SseEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
    signal,
  });
  if (!r.ok || !r.body) throw new AegisApiError(r.status, `${path} → ${r.status}`);
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() || "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      try {
        onEvent(JSON.parse(line.slice(5).trim()) as SseEvent);
      } catch {
        /* ignore malformed chunk */
      }
    }
  }
}

// ── Typed endpoint methods ──────────────────────────────────────────────────
export const aegisApi = {
  health: () => get("/api/health"),

  // ── REGO (Macro Radar) → Research / Drafting
  signalImpact: (b: { signal: string; jurisdictions?: string[]; org_context?: string }) =>
    post("/api/research/signal-impact", b).then((r) => r.data),
  whatIf: (b: { signal: string; levers?: Record<string, any>; org_context?: string }) =>
    post("/api/research/what-if", b).then((r) => r.data),
  riskProjection: (b: { domain: string; jurisdictions?: string[] }) =>
    post("/api/research/risk-projection", b).then((r) => r.data),
  stakeholderMap: (b: { regulation: string; org: string }) =>
    post("/api/research/stakeholder-map", b).then((r) => r.data),
  advocacyBrief: (b: {
    org: string;
    regulation: string;
    stakeholder_name: string;
    stakeholder_role: string;
    why: string;
  }) => post("/api/drafting/advocacy-brief", b).then((r) => r.data),

  // ── Executive brief (shared: REGO board brief, cross-module synthesis)
  brief: (b: { topic: string; prior_outputs?: string }) =>
    post("/api/executive/brief", b).then((r) => r.data),

  // ── VRIT (Local Intel) → Compliance
  localIntel: (b: {
    entity: string;
    jurisdiction?: string;
    topics?: string[];
    org_context?: string;
  }) => post("/api/compliance/local-intel", b).then((r) => r.data),

  // ── EIT1 (Newsfeed) → Operations / EA / Research
  verifyOrg: (b: { name: string }) =>
    post("/api/research/verify-org", b).then((r) => r.data),
  ingest: (b: {
    mode: string;
    input: string;
    org_profile?: any;
    decision_mode?: string;
  }) => post("/api/operations/ingest", b).then((r) => r.data),
  ingestStream: (
    b: { mode: string; input: string; org_profile?: any; decision_mode?: string },
    onEvent: (e: SseEvent) => void,
    signal?: AbortSignal,
  ) => postStream("/api/operations/ingest/stream", b, onEvent, signal),
  reportGenerate: (b: {
    report_type: string;
    signal?: any;
    card_title?: string;
    org_profile?: any;
  }) => post("/api/operations/report-generate", b).then((r) => r.data),

  // ── EIT2 (War Room) → Executive Assistant
  scenarios: (b: { business_plan: string; org_profile?: any }) =>
    post("/api/executive/scenarios", b).then((r) => r.data),
  nextSteps: (b: { business_plan: string; org_profile?: any }) =>
    post("/api/executive/next-steps", b).then((r) => r.data),
  simulate: (b: {
    business_plan: string;
    selected_scenario: string;
    scenario_data: any;
    selected_actions: any[];
    org_profile?: any;
  }) => post("/api/executive/simulate", b).then((r) => r.data),
  improvements: (b: {
    business_plan: string;
    selected_scenario: string;
    sim_result: any;
    target_variance: number;
    conditions: Record<string, string>;
    selected_steps: string[];
    org_profile?: any;
  }) => post("/api/executive/improvements", b).then((r) => r.data),
};

// ── Formatters: structured bridge JSON → display strings ─────────────────────
// REGO panels render plain text, so flatten the structured responses for them.
export const fmt = {
  signalImpact(d: any): string {
    if (!d || d._parse_error) return "No response.";
    const risk = d.risk_level ? `[${d.risk_level}] ` : "";
    const action = d.recommended_action ? `\n\n▸ Action: ${d.recommended_action}` : "";
    return `${risk}${d.impact_summary || ""}${action}`;
  },
  whatIf(d: any): string {
    if (!d || d._parse_error) return "Error.";
    const areas = (d.impact_areas || [])
      .map((a: any) => `• [${a.impact}] ${a.area}: ${a.note}`)
      .join("\n");
    return [
      d.scenario_name ? `▌ ${d.scenario_name}` : "",
      d.headline || "",
      d.probability != null ? `Probability: ${d.probability}%  ·  Timeline: ${d.timeline || "—"}` : "",
      areas,
      d.recommended_posture ? `▸ Posture: ${d.recommended_posture} (${d.confidence || "—"} confidence)` : "",
    ]
      .filter(Boolean)
      .join("\n\n");
  },
  localIntel(d: any): string {
    if (!d || d._parse_error) return "⚠ Không phân tích được.";
    const risk = d.risk_level ? `[${d.risk_level}] ` : "";
    const instruments = (d.key_instruments || [])
      .map((k: any) => `• ${k.name} (${k.status}, ${k.impact}) — ${k.note}`)
      .join("\n");
    const flags = (d.compliance_flags || [])
      .map((f: any) => `⚠ [${f.severity}] ${f.flag}`)
      .join("\n");
    const actions = (d.recommended_actions || []).map((a: string) => `▸ ${a}`).join("\n");
    return [
      `${risk}${d.regulatory_summary || ""}`,
      instruments && `Văn bản chính:\n${instruments}`,
      flags && `Cờ tuân thủ:\n${flags}`,
      actions && `Khuyến nghị:\n${actions}`,
    ]
      .filter(Boolean)
      .join("\n\n");
  },
  advocacyBrief(d: any): string {
    if (!d || d._parse_error) return "Error.";
    const tp = (d.talking_points || []).map((p: string) => `• ${p}`).join("\n");
    return [
      `TALKING POINTS:\n${tp}`,
      d.framing ? `FRAMING: ${d.framing}` : "",
      d.red_lines ? `RED LINES: ${d.red_lines}` : "",
      d.follow_up ? `FOLLOW-UP: ${d.follow_up}` : "",
    ]
      .filter(Boolean)
      .join("\n\n");
  },
};
