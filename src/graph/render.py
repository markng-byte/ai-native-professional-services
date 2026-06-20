"""
Markdown renderers that turn GraphRAGEngine query results into the agent
output blocks shown in the UI. Each returns (markdown, is_graph_backed) so the
caller can label the source honestly (real graph traversal vs simulation).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .engine import GraphRAGEngine


def _source_footer(engine: GraphRAGEngine) -> str:
    info = engine.info()
    return (f"_Source: GraphRAG · {info['backend']} backend ({info['mode']}) · "
            f"{info['nodes']} nodes / {info['edges']} edges · live traversal_")


def jurisdiction_compare(engine: GraphRAGEngine, codes: List[str]) -> Optional[str]:
    res = engine.compare_jurisdictions(codes)
    found = res["found"]
    if len(found) < 2:
        return None  # not enough graph data → let caller fall back
    header = "| Dimension | " + " | ".join(j["full_name"] for j in found) + " |"
    sep = "|---" * (len(found) + 1) + "|"
    rows = []
    for key, label in res["dimensions"]:
        cells = [str(j.get(key, "n/a")) for j in found]
        rows.append(f"| {label} | " + " | ".join(cells) + " |")

    def cost_num(j):
        digits = "".join(c for c in str(j.get("formation_cost", "")) if c.isdigit())
        return int(digits) if digits else 10 ** 9
    best = min(found, key=cost_num)

    missing_note = ""
    if res["missing"]:
        missing_note = f"\n\n⚠️ Not in knowledge graph: {', '.join(res['missing'])}."
    return ("Queried the knowledge graph for "
            f"**{', '.join(j['jurisdiction_code'] for j in found)}** across 6 dimensions.\n\n"
            + "\n".join([header, sep] + rows)
            + f"\n\n**Recommendation:** **{best['full_name']}** offers the lowest formation "
            "cost for a plain holding company; choose Singapore if substance / banking "
            "depth is the priority." + missing_note
            + "\n\n" + _source_footer(engine))


def ubo_chain(engine: GraphRAGEngine, name: str) -> Optional[str]:
    target_id = engine.resolve_ubo_target(name)
    if not target_id:
        return None
    res = engine.get_ubo(target_id)
    if not res["ubos"]:
        return None
    tree = "\n".join(res["tree"])
    rows = []
    for slot in sorted(res["ubos"].values(), key=lambda s: -s["pct"]):
        flag = "⚠️ Concentration" if slot["pct"] >= 75 else "—"
        paths = slot["paths"]
        rows.append(f"| {slot['name']} | {slot['pct']:.0f}% | {paths} | {flag} |")
    multi = any(s["paths"] > 1 for s in res["ubos"].values())
    note = ("One or more UBOs are reachable via multiple ownership paths — "
            "flagged for review." if multi else "Single-path ownership; no concentration via splitting.")
    return (f"Traversed the ownership graph from **{res['target'].get('registered_name', name)}** "
            "(`MATCH (e)<-[:OWNS*1..6]-(owner)`):\n\n"
            "```\n" + tree + "\n```\n\n"
            "| UBO | Effective % | Paths | Flag |\n|---|---|---|---|\n"
            + "\n".join(rows)
            + f"\n\n> **{len(res['ubos'])} ultimate beneficial owner(s)** resolved. {note}\n\n"
            + _source_footer(engine))


def mandates(engine: GraphRAGEngine, within_days: int = 90) -> Optional[str]:
    due = engine.mandates_due(within_days)
    if not due:
        return None

    def badge(d):
        if d < 14:  return f"🔴 {d} days"
        if d < 30:  return f"🟠 {d} days"
        if d < 60:  return f"🟡 {d} days"
        return f"🟢 {d} days"

    rows = [f"| {r['client']} | {r['obligation']} | {r['jurisdiction']} | {r['due']} | {badge(r['days'])} |"
            for r in due]
    urgent = [r for r in due if r["days"] < 14]
    summary = (f"**{len(due)} obligation(s)** in the next {within_days} days"
               + (f" · **{len(urgent)} urgent**" if urgent else ""))
    rec = ""
    if urgent:
        rec = (" Recommend triggering the renewal workflow for "
               + ", ".join(r["client"] for r in urgent) + " today.")
    return ("Queried Service_Mandate nodes with renewal_date in window:\n\n"
            "| Client | Obligation | Jurisdiction | Due | Status |\n|---|---|---|---|---|\n"
            + "\n".join(rows)
            + f"\n\n> {summary}.{rec}\n\n" + _source_footer(engine))
