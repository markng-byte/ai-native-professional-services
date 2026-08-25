"""
Approval storage backends.

Approvals are **audit records**, not session state. `governance/GOVERNANCE.md`
§5.1 requires human-override and compliance decisions to be retained for seven
years and to be immutable; an in-process dict satisfies neither. This module
adds durability behind the existing :class:`~hitl.approvals.ApprovalStore`
interface, so callers are unchanged.

Two backends:

* :class:`InMemoryApprovalStorage` — the previous behaviour, still the default
  for tests and ephemeral use.
* :class:`SqliteApprovalStorage` — durable, append-only, safe under concurrent
  reviewers.

Integrity model
---------------
The ``approval_events`` table **is** the audit trail: it is insert-only, and
``UPDATE``/``DELETE`` are refused by database triggers rather than by
convention, so an application bug (or a careless operator with a SQL prompt)
cannot quietly rewrite a decision history. The ``approvals`` table is a
*projection* of current state kept for cheap lookup; it is derivable from the
events and is asserted against them in the tests.

Concurrency
-----------
Two reviewers acting on the same item at once must not both succeed. State
changes go through :meth:`transition`, which performs a **compare-and-set**
inside an ``IMMEDIATE`` transaction: the update only applies if the row is still
in the state the caller validated against. The loser gets a conflict rather
than silently overwriting the winner's decision.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Dict, List, Optional, Protocol

DEFAULT_DB_ENV = "FIRMOS_APPROVAL_DB"


class ApprovalStorageError(RuntimeError):
    """Raised on a storage-level failure, including a lost-update conflict."""


class ApprovalStorage(Protocol):
    """Persistence contract for approval records and their event trail."""

    def insert(self, record: Dict, event: Dict) -> None: ...
    def get(self, approval_id: str) -> Optional[Dict]: ...
    def list_by_state(self, state: str) -> List[Dict]: ...
    def transition(self, approval_id: str, *, expected_state: str, new_state: str,
                   event: Dict, decided_by: Optional[str],
                   justification: Optional[str]) -> Dict: ...


# ---------------------------------------------------------------------------
# In-memory
# ---------------------------------------------------------------------------

class InMemoryApprovalStorage:
    """Process-local storage. Fast, and lost on restart — tests and demos only."""

    backend_name = "memory"
    durable = False

    def __init__(self) -> None:
        self._records: Dict[str, Dict] = {}

    def insert(self, record: Dict, event: Dict) -> None:
        stored = dict(record)
        stored["events"] = [dict(event)]
        self._records[record["approval_id"]] = stored

    def get(self, approval_id: str) -> Optional[Dict]:
        found = self._records.get(approval_id)
        return json.loads(json.dumps(found)) if found else None

    def list_by_state(self, state: str) -> List[Dict]:
        return [json.loads(json.dumps(r)) for r in self._records.values()
                if r["state"] == state]

    def transition(self, approval_id: str, *, expected_state: str, new_state: str,
                   event: Dict, decided_by: Optional[str],
                   justification: Optional[str]) -> Dict:
        record = self._records.get(approval_id)
        if record is None:
            raise ApprovalStorageError(f"Unknown approval_id {approval_id!r}.")
        if record["state"] != expected_state:
            raise ApprovalStorageError(
                f"Approval {approval_id} changed underneath this decision: expected "
                f"{expected_state}, found {record['state']}."
            )
        record["events"].append(dict(event))
        record["state"] = new_state
        record["decided_by"] = decided_by
        record["decision_justification"] = justification
        return json.loads(json.dumps(record))


# ---------------------------------------------------------------------------
# SQLite
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS approvals (
    approval_id            TEXT PRIMARY KEY,
    action_type            TEXT NOT NULL,
    state                  TEXT NOT NULL,
    correlation_id         TEXT,
    capability             TEXT,
    client_id              TEXT,
    submitted_by           TEXT,
    required_role          TEXT NOT NULL,
    payload_ref            TEXT NOT NULL,
    decided_by             TEXT,
    decision_justification TEXT,
    created_at             TEXT NOT NULL,
    updated_at             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approval_events (
    event_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    approval_id   TEXT NOT NULL REFERENCES approvals(approval_id),
    seq           INTEGER NOT NULL,
    event         TEXT NOT NULL,
    from_state    TEXT,
    to_state      TEXT,
    actor         TEXT,
    role          TEXT,
    justification TEXT,
    timestamp     TEXT NOT NULL,
    UNIQUE (approval_id, seq)
);

CREATE INDEX IF NOT EXISTS idx_approvals_state ON approvals(state);
CREATE INDEX IF NOT EXISTS idx_events_approval ON approval_events(approval_id, seq);

-- The event trail is the audit record. Enforce append-only in the database, so
-- an application bug cannot rewrite decision history (GOVERNANCE.md §5.2).
CREATE TRIGGER IF NOT EXISTS approval_events_no_update
BEFORE UPDATE ON approval_events
BEGIN
    SELECT RAISE(ABORT, 'approval_events is append-only: updates are not permitted');
END;

CREATE TRIGGER IF NOT EXISTS approval_events_no_delete
BEFORE DELETE ON approval_events
BEGIN
    SELECT RAISE(ABORT, 'approval_events is append-only: deletes are not permitted');
END;
"""

_RECORD_COLUMNS = (
    "approval_id", "action_type", "state", "correlation_id", "capability",
    "client_id", "submitted_by", "required_role", "payload_ref", "decided_by",
    "decision_justification",
)


class SqliteApprovalStorage:
    """Durable approval storage.

    A connection is opened per operation rather than held open, so the store is
    safe to use from Streamlit's worker threads and from separate processes
    without sharing handles.
    """

    backend_name = "sqlite"
    durable = True

    def __init__(self, path: str) -> None:
        self.path = path
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        # Durability over speed: this is an audit store.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = FULL")
        return conn

    # -- serialization -----------------------------------------------------

    @staticmethod
    def _row_to_record(row: sqlite3.Row, events: List[Dict]) -> Dict:
        record = {k: row[k] for k in _RECORD_COLUMNS}
        record["payload_ref"] = json.loads(row["payload_ref"] or "{}")
        record["events"] = events
        return record

    @staticmethod
    def _event_to_row(event: Dict) -> Dict:
        return {
            "event": event.get("event"),
            "from_state": event.get("from"),
            "to_state": event.get("to"),
            "actor": event.get("actor"),
            "role": event.get("role"),
            "justification": event.get("justification"),
            "timestamp": event.get("timestamp"),
        }

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Dict:
        event = {
            "event": row["event"],
            "from": row["from_state"],
            "to": row["to_state"],
            "actor": row["actor"],
            "timestamp": row["timestamp"],
        }
        # Only present on decisions; keep the shape identical to in-memory.
        if row["role"] is not None:
            event["role"] = row["role"]
        if row["justification"] is not None or row["event"] in ("APPROVED", "REJECTED"):
            event["justification"] = row["justification"]
        return event

    def _load_events(self, conn: sqlite3.Connection, approval_id: str) -> List[Dict]:
        rows = conn.execute(
            "SELECT * FROM approval_events WHERE approval_id = ? ORDER BY seq",
            (approval_id,),
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    # -- operations --------------------------------------------------------

    def insert(self, record: Dict, event: Dict) -> None:
        now = event.get("timestamp")
        ev = self._event_to_row(event)
        with self._connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "INSERT INTO approvals (approval_id, action_type, state, "
                    "correlation_id, capability, client_id, submitted_by, "
                    "required_role, payload_ref, decided_by, decision_justification, "
                    "created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        record["approval_id"], record["action_type"], record["state"],
                        record.get("correlation_id"), record.get("capability"),
                        record.get("client_id"), record.get("submitted_by"),
                        record["required_role"],
                        json.dumps(record.get("payload_ref") or {}),
                        record.get("decided_by"), record.get("decision_justification"),
                        now, now,
                    ),
                )
                conn.execute(
                    "INSERT INTO approval_events (approval_id, seq, event, from_state, "
                    "to_state, actor, role, justification, timestamp) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (record["approval_id"], 1, ev["event"], ev["from_state"],
                     ev["to_state"], ev["actor"], ev["role"], ev["justification"],
                     ev["timestamp"]),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def get(self, approval_id: str) -> Optional[Dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_record(row, self._load_events(conn, approval_id))

    def list_by_state(self, state: str) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM approvals WHERE state = ? ORDER BY created_at",
                (state,),
            ).fetchall()
            return [self._row_to_record(r, self._load_events(conn, r["approval_id"]))
                    for r in rows]

    def transition(self, approval_id: str, *, expected_state: str, new_state: str,
                   event: Dict, decided_by: Optional[str],
                   justification: Optional[str]) -> Dict:
        ev = self._event_to_row(event)
        with self._connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")

                row = conn.execute(
                    "SELECT state FROM approvals WHERE approval_id = ?", (approval_id,)
                ).fetchone()
                if row is None:
                    raise ApprovalStorageError(f"Unknown approval_id {approval_id!r}.")

                # Compare-and-set: refuse if another reviewer moved it first.
                updated = conn.execute(
                    "UPDATE approvals SET state = ?, decided_by = ?, "
                    "decision_justification = ?, updated_at = ? "
                    "WHERE approval_id = ? AND state = ?",
                    (new_state, decided_by, justification, ev["timestamp"],
                     approval_id, expected_state),
                ).rowcount
                if updated != 1:
                    raise ApprovalStorageError(
                        f"Approval {approval_id} changed underneath this decision: "
                        f"expected {expected_state}, found {row['state']}."
                    )

                seq = conn.execute(
                    "SELECT COALESCE(MAX(seq), 0) + 1 AS next FROM approval_events "
                    "WHERE approval_id = ?", (approval_id,)
                ).fetchone()["next"]
                conn.execute(
                    "INSERT INTO approval_events (approval_id, seq, event, from_state, "
                    "to_state, actor, role, justification, timestamp) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (approval_id, seq, ev["event"], ev["from_state"], ev["to_state"],
                     ev["actor"], ev["role"], ev["justification"], ev["timestamp"]),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        return self.get(approval_id)


def default_storage() -> ApprovalStorage:
    """Choose a backend from the environment.

    ``FIRMOS_APPROVAL_DB`` selects durable SQLite storage at that path. Without
    it the store stays in-memory, which is correct for tests and demos but must
    not be used where approvals are audit records.
    """
    path = os.environ.get(DEFAULT_DB_ENV)
    if path:
        return SqliteApprovalStorage(path)
    return InMemoryApprovalStorage()
