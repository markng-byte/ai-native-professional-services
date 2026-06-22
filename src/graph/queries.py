"""
Canonical GraphRAG query patterns (from GRAPH_SCHEMA.md §3).

Each function takes a GraphBackend and returns plain Python data structures —
backend-agnostic, so they run unchanged on NetworkX (dev) or Neo4j (prod).
These are the queries that "vanilla RAG cannot answer" because they require
walking the graph (ownership chains, conflict paths, date-filtered mandates).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional

from .backends.base import GraphBackend


# ---------------------------------------------------------------------------
# Pattern 4 & 6 — Jurisdiction rules / comparison  (Research Agent)
# ---------------------------------------------------------------------------

_JURIS_DISPLAY = [
    ("formation_cost",        "💵 Formation cost"),
    ("timeline",              "⏱️ Timeline"),
    ("corporate_tax",         "🏦 Corporate tax"),
    ("substance_requirements","🏗️ Substance"),
    ("FATF_status",           "🌐 FATF status"),
    ("banking_access",        "💳 Banking access"),
]


def get_jurisdiction(backend: GraphBackend, code: str) -> Optional[Dict]:
    matches = backend.find_nodes("Jurisdiction", jurisdiction_code=code)
    return matches[0] if matches else None


def compare_jurisdictions(backend: GraphBackend, codes: List[str]) -> Dict:
    """Return {found:[node...], missing:[code...], dimensions:[(key,label)...]}."""
    found, missing = [], []
    for c in codes:
        j = get_jurisdiction(backend, c)
        (found if j else missing).append(j if j else c)
    return {"found": found, "missing": missing, "dimensions": _JURIS_DISPLAY}


# ---------------------------------------------------------------------------
# Pattern 1 & 7 — UBO chain traversal  (Compliance Agent)
# ---------------------------------------------------------------------------

def get_ubo(backend: GraphBackend, entity_id: str, max_depth: int = 6) -> Dict:
    """Walk incoming OWNS edges to resolve ultimate beneficial owners.

    Effective ownership is the product of percentages along each path; a UBO
    reachable via multiple paths has its effective shares summed.
    Returns {ubos:{ind_id:{name,pct,paths}}, tree:[...], target:node}.
    """
    target = backend.get_node(entity_id)
    ubos: Dict[str, Dict] = {}
    tree_lines: List[str] = []

    def walk(node_id: str, fraction: float, depth: int, prefix: str, visited: set):
        if depth > max_depth or node_id in visited:
            return
        visited = visited | {node_id}
        owners = backend.in_edges(node_id, "OWNS")
        for i, e in enumerate(owners):
            owner = backend.get_node(e.src)
            if owner is None:
                continue
            pct = float(e.props.get("ownership_pct", 0) or 0)
            eff = fraction * (pct / 100.0)
            branch = "└─" if i == len(owners) - 1 else "├─"
            name = owner.get("full_name") or owner.get("registered_name") or owner.get("full_legal_name") or e.src
            label = owner.get("_label")
            if label == "Individual":
                tag = "  ◀ UBO (natural person)"
                slot = ubos.setdefault(e.src, {"name": name, "pct": 0.0, "paths": 0})
                slot["pct"] += eff * 100.0
                slot["paths"] += 1
            else:
                tag = ""
            tree_lines.append(f"{prefix}{branch} {pct:.0f}% → {name}{tag}")
            if label != "Individual":
                walk(e.src, eff, depth + 1, prefix + ("   " if i == len(owners) - 1 else "│  "), visited)

    if target is not None:
        root_name = (target.get("registered_name") or target.get("full_legal_name")
                     or target.get("full_name") or entity_id)
        tree_lines.append(root_name)
        walk(entity_id, 1.0, 0, "", set())

    return {"target": target, "ubos": ubos, "tree": tree_lines}


def find_entity_by_name(backend: GraphBackend, name: str) -> Optional[Dict]:
    """Fuzzy-find a Client or Legal_Entity whose name contains `name`."""
    name = (name or "").strip()
    if len(name) < 3:
        return None
    # try the most specific token (e.g. "Atlas" from "Project Atlas Group")
    candidates = [name] + [w for w in name.split() if len(w) > 3]
    for needle in candidates:
        for label, field in (("Legal_Entity", "registered_name"),
                             ("Client", "full_legal_name")):
            hits = backend.search_nodes(label, field, needle)
            if hits:
                return hits[0]
    return None


def resolve_ubo_target(backend: GraphBackend, name: str) -> Optional[str]:
    """Map a name to the Legal_Entity node id to start UBO traversal from.

    If the match is a Client, hop to the entity it OWNS (its holding company).
    """
    node = find_entity_by_name(backend, name)
    if node is None:
        return None
    if node["_label"] == "Legal_Entity":
        return node["_id"]
    # Client → follow any edge to its primary Legal_Entity (PRIMARY_ENTITY, OWNS…)
    for e in backend.out_edges(node["_id"]):
        dst = backend.get_node(e.dst)
        if dst and dst.get("_label") == "Legal_Entity":
            return e.dst
    return node["_id"]


# ---------------------------------------------------------------------------
# Pattern 3 — Mandates due for renewal  (Operations Agent)
# ---------------------------------------------------------------------------

def mandates_due(backend: GraphBackend, within_days: int = 90,
                 today: Optional[date] = None) -> List[Dict]:
    """Return active Service_Mandates whose renewal_date falls within window."""
    ref = today or date.today()
    out = []
    for m in backend.nodes_by_label("Service_Mandate"):
        if str(m.get("status", "")).lower() != "active":
            continue
        rd = m.get("renewal_date")
        if not rd:
            continue
        try:
            due = datetime.strptime(rd, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        delta = (due - ref).days
        if -7 <= delta <= within_days:      # include slightly overdue
            out.append({
                "client": m.get("client_name", "—"),
                "obligation": m.get("service_type", "—"),
                "jurisdiction": m.get("jurisdiction_code", "—"),
                "due": rd,
                "days": delta,
                "officer": m.get("assigned_officer", "—"),
            })
    return sorted(out, key=lambda r: r["days"])


# ---------------------------------------------------------------------------
# Pattern 2 — Conflict / prior-structure check  (Compliance Agent)
# ---------------------------------------------------------------------------

def individual_connections(backend: GraphBackend, individual_id: str) -> List[Dict]:
    """Find entities an individual is connected to (OWNS / IS_DIRECTOR_OF)."""
    out = []
    for rel in ("OWNS", "IS_DIRECTOR_OF"):
        for e in backend.out_edges(individual_id, rel):
            ent = backend.get_node(e.dst)
            if ent:
                out.append({"entity": ent.get("registered_name", e.dst),
                            "relation": rel, "props": e.props})
    return out
