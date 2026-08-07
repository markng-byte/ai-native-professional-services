"""
Skill: jurisdiction-compare

Compares two or more jurisdictions across the standard dimensions (cost,
timeline, tax, substance, FATF, banking, compliance), returning a comparison
table, per-datapoint source citations, a confidence level, and — when a client
profile is supplied — a ranked recommendation.

Validation:
  * Fewer than 2 jurisdictions          -> ERR_INSUFFICIENT_JURISDICTIONS
  * A non-ISO-3166 code                  -> ERR_INVALID_JURISDICTION_CODE
  * A valid code not covered by the corpus lowers confidence to LOW.

Runs against the same knowledge-graph fixture used by the Command Center engine.
"""

from __future__ import annotations

import re
from typing import Dict, List

_ALL_DIMENSIONS = ["cost", "timeline", "tax", "substance", "FATF", "banking", "compliance"]

# Jurisdictions the firm corpus fully covers.
_CORPUS = {
    "VG": {"cost": "$2,500", "timeline": "3-5 days", "tax": "0% corporate",
           "substance": "Light (ESA)", "FATF": "Compliant", "banking": "Moderate",
           "compliance": "Registered agent + ESA filing"},
    "KY": {"cost": "$4,500", "timeline": "5-7 days", "tax": "0% corporate",
           "substance": "Light (ESA)", "FATF": "Compliant", "banking": "Strong",
           "compliance": "Registered office + ES return"},
    "SG": {"cost": "$3,000", "timeline": "1-2 days", "tax": "17% corporate",
           "substance": "High", "FATF": "Compliant", "banking": "Excellent",
           "compliance": "ACRA annual filing + director residency"},
    "HK": {"cost": "$2,800", "timeline": "2-4 days", "tax": "16.5% corporate",
           "substance": "Medium", "FATF": "Compliant", "banking": "Strong",
           "compliance": "Annual return + audited accounts"},
    "US-DE": {"cost": "$1,200", "timeline": "1-3 days", "tax": "Pass-through / 21%",
              "substance": "Low", "FATF": "Compliant", "banking": "Excellent",
              "compliance": "Franchise tax + registered agent"},
    "AE": {"cost": "$5,500", "timeline": "5-10 days", "tax": "9% corporate",
           "substance": "Medium", "FATF": "Monitored", "banking": "Moderate",
           "compliance": "ESR + UBO register"},
}

_ISO_CODE = re.compile(r"^[A-Z]{2}(-[A-Z0-9]{1,3})?$")


def _valid_iso(code: str) -> bool:
    return bool(_ISO_CODE.match(code or ""))


def run(payload: Dict) -> Dict:
    jurisdictions: List[str] = payload.get("jurisdictions", []) or []
    dimensions: List[str] = payload.get("comparison_dimensions") or _ALL_DIMENSIONS
    client_profile = payload.get("client_profile")

    if len(jurisdictions) < 2:
        return {"error": "ERR_INSUFFICIENT_JURISDICTIONS"}

    for code in jurisdictions:
        if not _valid_iso(code):
            return {"error": "ERR_INVALID_JURISDICTION_CODE"}

    fully_covered = all(code in _CORPUS for code in jurisdictions)
    confidence_level = "HIGH" if fully_covered else "LOW"

    comparison_data = {}
    source_citations = []
    for code in jurisdictions:
        row = _CORPUS.get(code, {})
        comparison_data[code] = {d: row.get(d, "n/a — not in corpus") for d in dimensions}
        if code in _CORPUS:
            source_citations.append(f"Firm KnowledgeGraph :: {code} jurisdiction profile (2026-04-29)")
        else:
            source_citations.append(f"Incomplete corpus coverage for {code} — flagged LOW confidence")

    recommendation = None
    if client_profile:
        # Cheapest fully-covered jurisdiction as a naive ranked suggestion.
        covered = [c for c in jurisdictions if c in _CORPUS]
        ranked = sorted(
            covered,
            key=lambda c: int(re.sub(r"[^\d]", "", _CORPUS[c]["cost"]) or "999999"),
        )
        if ranked:
            recommendation = (
                f"Recommend {ranked[0]} for a {client_profile.get('entity_type', 'entity')}"
                f" — lowest formation cost among the covered set."
            )

    return {
        "comparison_table_rows": len(dimensions),
        "comparison_dimensions": dimensions,
        "comparison_data": comparison_data,
        "confidence_level": confidence_level,
        "source_citations": source_citations,
        "recommendation": recommendation,
    }
