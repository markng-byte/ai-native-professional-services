"""
Skill: doc-expiry-scan

Scans the document register for KYC / statutory documents expiring within a
window (and those already expired), with optional filters by document type and
jurisdiction. Results are sorted most-urgent-first, exclude documents with no
expiry date, and always carry the assigned officer for follow-up.

Runs against an in-repo document-register fixture. ``days_until_expiry`` is
stored directly on each fixture record so the scan is deterministic regardless
of the wall-clock date it runs on.
"""

from __future__ import annotations

from typing import Dict, List


def _doc(doc_id, doc_type, jurisdiction, days, expiry_date, officer):
    return {
        "doc_id": doc_id,
        "doc_type": doc_type,
        "jurisdiction": jurisdiction,
        "days_until_expiry": days,
        "expiry_date": expiry_date,
        "assigned_officer": officer,
    }


REGISTER: List[Dict] = [
    _doc("DOC-001", "PASSPORT", "VG", 12, "2026-08-19", "S. Chen"),
    _doc("DOC-002", "PASSPORT", "KY", 45, "2026-09-21", "R. Patel"),
    _doc("DOC-003", "CERT_OF_INCORP", "VG", 400, "2027-09-11", "S. Chen"),
    _doc("DOC-004", "PASSPORT", "SG", -5, "2026-08-02", "L. Ono"),
    _doc("DOC-005", "UBO_DECLARATION", "VG", None, None, "S. Chen"),  # no expiry
    _doc("DOC-006", "PASSPORT", "HK", 70, "2026-10-16", "M. Diaz"),
    _doc("DOC-007", "ECONOMIC_SUBSTANCE", "VG", 20, "2026-08-27", "A. Khan"),
]


def run(payload: Dict) -> Dict:
    threshold = payload.get("date_threshold_days", 30)
    doc_types = payload.get("doc_types")
    jurisdiction_filter = payload.get("jurisdiction_filter")

    # Documents with no expiry date are never eligible.
    pool = [d for d in REGISTER if d["days_until_expiry"] is not None]
    if doc_types:
        pool = [d for d in pool if d["doc_type"] in doc_types]
    if jurisdiction_filter:
        pool = [d for d in pool if d["jurisdiction"] == jurisdiction_filter]

    expiring = [d for d in pool if 0 <= d["days_until_expiry"] <= threshold]
    already_expired = [d for d in pool if d["days_until_expiry"] < 0]

    results = sorted(expiring + already_expired, key=lambda d: d["days_until_expiry"])

    return {
        "results": results,
        "total_expiring": len(expiring),
        "already_expired": len(already_expired),
        "scan_window_days": threshold,
    }
