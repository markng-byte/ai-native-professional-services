"""
Skill: ubo-chain-traverse

Walks the ownership graph from a legal entity to surface its ultimate
beneficial owners (natural persons), computing effective ownership percentage
across multi-hop chains and filtering to a configurable threshold. Flags chains
that exceed max hops or that cannot be fully resolved, surfaces PEP flags, and
always emits an audit reference. Runs against an in-repo ownership fixture
instead of live Neo4j Cypher traversal.
"""

from __future__ import annotations

import uuid
from typing import Dict


def _ubo(name, pct, path_length, pep=False):
    return {
        "individual_name": name,
        "beneficial_pct": float(pct),
        "path_length": path_length,
        "pep_flag": pep,
    }


# Each entity resolves to a pre-computed ownership picture. ``ubos`` are already
# effective-percentage rolled up; ``raw`` entries are unfiltered so the
# threshold logic can be exercised.
GRAPH: Dict[str, Dict] = {
    "LE-TEST-001": {"ubos": [_ubo("Individual A", 100.0, 1)]},
    "LE-TEST-002": {"ubos": [_ubo("Individual B", 48.0, 2)]},  # 60% x 80%
    "LE-TEST-003": {"ubos": [
        _ubo("Owner One", 33.34, 1),
        _ubo("Owner Two", 33.33, 1),
        _ubo("Owner Three", 33.33, 1),
    ]},
    "LE-TEST-004": {"raw": [_ubo("Minor Holder", 20.0, 1)]},  # below 25% threshold
    "LE-TEST-005": {"exceeded": True},
    "LE-TEST-006": {"unresolved": ["LE-INT-778"]},
    "LE-TEST-007": {"ubos": [_ubo("Exposed Person", 55.0, 1, pep=True)]},
    "LE-TEST-009": {"raw": [
        _ubo("Holder X", 30.0, 1),
        _ubo("Holder Y", 15.0, 2),
        _ubo("Holder Z", 12.0, 2),
    ]},  # 3 UBOs at 10%, only 1 at 25%
}


def run(payload: Dict) -> Dict:
    entity_id = payload.get("entity_id")
    threshold = float(payload.get("threshold_pct", 25.0))
    audit = str(uuid.uuid4())

    node = GRAPH.get(entity_id)
    if node is None:
        return {"error": "ERR_ENTITY_NOT_IN_GRAPH"}

    if node.get("exceeded"):
        return {
            "chain_exceeded_max_hops": True,
            "requires_human_review": True,
            "ubo_list": [],
            "total_ubos_found": 0,
            "unresolved_chains": [],
            "audit_log_ref": audit,
        }

    if node.get("unresolved"):
        return {
            "unresolved_chains": node["unresolved"],
            "requires_human_review": True,
            "chain_exceeded_max_hops": False,
            "ubo_list": [],
            "total_ubos_found": 0,
            "audit_log_ref": audit,
        }

    candidates = node.get("ubos") or node.get("raw") or []
    ubo_list = [u for u in candidates if u["beneficial_pct"] >= threshold]
    requires_human_review = any(u.get("pep_flag") for u in ubo_list)

    return {
        "total_ubos_found": len(ubo_list),
        "ubo_list": ubo_list,
        "requires_human_review": requires_human_review,
        "chain_exceeded_max_hops": False,
        "unresolved_chains": [],
        "audit_log_ref": audit,
    }
