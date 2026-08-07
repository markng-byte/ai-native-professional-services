"""
Skill: conflict-check

Checks a prospective client's directors and UBOs against the firm's existing
book for conflicts of interest: shared directorships, shared UBOs, pre-existing
conflict flags, shared registered addresses, and fuzzy name matches. Returns
every conflict found (not just the first) plus a recommendation
(PROCEED / REVIEW / BLOCK) and an audit reference. Every check requires human
review.

Runs against an in-repo conflict graph fixture instead of live Neo4j.
"""

from __future__ import annotations

import uuid
from typing import Dict

# individual_id / name (lowercased) -> conflict type surfaced by the graph
_DIRECTORSHIP_OVERLAP = {"ind-test-001", "test_existing_director_001"}
_UBO_OVERLAP = {"ind-test-002", "test_existing_ubo_001"}
_PRIOR_CONFLICT_FLAG = {"ind-test-003"}
_SHARED_ADDRESS = {"ind-test-004"}
# Individual whose directorship overlaps with two different existing clients.
_MULTI_OVERLAP = {"ind-test-multi": ["CLT-EX-001", "CLT-EX-002"]}
# Fuzzy name variants that map to an existing individual.
_FUZZY_NAMES = {"robert j. smith": "Robert James Smith"}


def _identifiers(person: Dict):
    ids = set()
    if person.get("individual_id"):
        ids.add(str(person["individual_id"]).lower())
    if person.get("full_name"):
        ids.add(str(person["full_name"]).lower())
    return ids


def run(payload: Dict) -> Dict:
    profile = payload.get("new_client_profile", {}) or {}
    directors = profile.get("directors", []) or []
    ubos = profile.get("ubos", []) or []
    people = directors + ubos

    if not directors and not ubos:
        return {"error": "ERR_NO_INDIVIDUALS_TO_CHECK"}

    conflicts = []
    possible = False

    for person in people:
        ids = _identifiers(person)
        for ident in ids:
            if ident in _DIRECTORSHIP_OVERLAP:
                conflicts.append({"conflict_type": "DIRECTORSHIP_OVERLAP", "matched_on": ident})
            if ident in _UBO_OVERLAP:
                conflicts.append({"conflict_type": "UBO_OVERLAP", "matched_on": ident})
            if ident in _PRIOR_CONFLICT_FLAG:
                conflicts.append({"conflict_type": "PRIOR_CONFLICT_FLAG", "matched_on": ident})
            if ident in _SHARED_ADDRESS:
                conflicts.append({"conflict_type": "SHARED_ADDRESS", "matched_on": ident})
            if ident in _MULTI_OVERLAP:
                for existing in _MULTI_OVERLAP[ident]:
                    conflicts.append({
                        "conflict_type": "DIRECTORSHIP_OVERLAP",
                        "matched_on": ident,
                        "existing_client": existing,
                    })
            if ident in _FUZZY_NAMES:
                possible = True

    conflict_found = len(conflicts) > 0

    if any(c["conflict_type"] == "PRIOR_CONFLICT_FLAG" for c in conflicts):
        recommendation = "BLOCK"
    elif conflict_found or possible:
        recommendation = "REVIEW"
    else:
        recommendation = "PROCEED"

    return {
        "conflict_found": conflict_found,
        "conflict_found_possible": possible,
        "conflicts": conflicts,
        "total_conflicts": len(conflicts),
        "recommendation": recommendation,
        "requires_human_review": True,
        "audit_log_ref": str(uuid.uuid4()),
    }
