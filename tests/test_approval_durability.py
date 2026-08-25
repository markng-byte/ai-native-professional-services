"""
Durable approval storage tests.

Approvals are audit records, not session state: `governance/GOVERNANCE.md` §5.1
requires human-override and compliance decisions to be retained for seven years
and to be immutable. An in-process dict satisfies neither. These tests cover the
four properties that make the SQLite backend fit for that purpose.

1. **Durability** — a decision survives losing the process.
2. **Backend parity** — swapping the backend changes nothing a caller observes,
   so the governance behaviour proven in earlier phases still holds.
3. **Append-only integrity** — the event trail cannot be rewritten, enforced by
   the database rather than by convention.
4. **Concurrency safety** — two reviewers deciding at once cannot both win.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import threading
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from hitl import STATE_APPROVED, STATE_PENDING_REVIEW, STATE_REJECTED  # noqa: E402
from hitl.approvals import ApprovalError, ApprovalStore, ROLE_RM       # noqa: E402
from hitl.storage import (                                             # noqa: E402
    DEFAULT_DB_ENV,
    InMemoryApprovalStorage,
    SqliteApprovalStorage,
    default_storage,
)
from rm import RM_WORKFLOWS                                            # noqa: E402
from validation import deliver                                         # noqa: E402

RM = {"rm_id": "RM-001"}
OWNED = "CLT-001234"


def draft():
    return RM_WORKFLOWS["rm-followup-draft"]({"actor": RM, "client_id": OWNED})


class TestDurability(unittest.TestCase):
    """The property this work exists for."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "approvals.db")

    def test_approval_survives_losing_the_process(self):
        # "Process 1" submits and approves.
        store = ApprovalStore(SqliteApprovalStorage(self.db))
        envelope = draft()
        record = store.submit(envelope, submitted_by="RM-001")
        store.decide(record.approval_id, decision=STATE_APPROVED,
                     reviewer_id="RM-001", reviewer_role=ROLE_RM)
        approval_id = record.approval_id
        del store                     # process ends

        # "Process 2" starts fresh against the same file.
        reopened = ApprovalStore(SqliteApprovalStorage(self.db))
        self.assertEqual(reopened.state_of(approval_id), STATE_APPROVED)
        loaded = reopened.get(approval_id)
        self.assertEqual([e["event"] for e in loaded.events],
                         ["SUBMITTED", STATE_APPROVED])
        self.assertEqual(loaded.decided_by, "RM-001")

    def test_delivery_gate_honours_a_restored_approval(self):
        """End-to-end: an approval granted before a restart still opens the gate."""
        envelope = draft()
        store = ApprovalStore(SqliteApprovalStorage(self.db))
        record = store.submit(envelope, submitted_by="RM-001")
        store.decide(record.approval_id, decision=STATE_APPROVED,
                     reviewer_id="RM-001", reviewer_role=ROLE_RM)
        del store

        reopened = ApprovalStore(SqliteApprovalStorage(self.db))
        decision = deliver(envelope, store=reopened, approval_id=record.approval_id)
        self.assertTrue(decision["delivered"])

    def test_pending_queue_survives_restart(self):
        store = ApprovalStore(SqliteApprovalStorage(self.db))
        store.submit(draft(), submitted_by="RM-001")
        store.submit(draft(), submitted_by="RM-001")
        del store

        reopened = ApprovalStore(SqliteApprovalStorage(self.db))
        self.assertEqual(len(reopened.pending()), 2)

    def test_rejection_and_justification_survive_restart(self):
        store = ApprovalStore(SqliteApprovalStorage(self.db))
        record = store.submit(draft(), submitted_by="RM-001")
        store.decide(record.approval_id, decision=STATE_REJECTED,
                     reviewer_id="RM-001", reviewer_role=ROLE_RM,
                     justification="Tone unsuitable for this client.")
        del store

        reopened = ApprovalStore(SqliteApprovalStorage(self.db))
        loaded = reopened.get(record.approval_id)
        self.assertEqual(loaded.state, STATE_REJECTED)
        self.assertEqual(loaded.decision_justification,
                         "Tone unsuitable for this client.")

    def test_in_memory_store_does_not_survive(self):
        """States the limitation explicitly so it cannot be assumed away."""
        store = ApprovalStore(InMemoryApprovalStorage())
        record = store.submit(draft(), submitted_by="RM-001")
        self.assertFalse(store.durable)
        fresh = ApprovalStore(InMemoryApprovalStorage())
        self.assertIsNone(fresh.get(record.approval_id))


class TestBackendParity(unittest.TestCase):
    """Swapping the backend must not change observable behaviour."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _stores(self):
        return [
            ("memory", ApprovalStore(InMemoryApprovalStorage())),
            ("sqlite", ApprovalStore(
                SqliteApprovalStorage(os.path.join(self.tmp, "parity.db")))),
        ]

    def test_happy_path_identical(self):
        for name, store in self._stores():
            with self.subTest(backend=name):
                rec = store.submit(draft(), submitted_by="RM-001")
                self.assertEqual(rec.state, STATE_PENDING_REVIEW)
                out = store.decide(rec.approval_id, decision=STATE_APPROVED,
                                   reviewer_id="RM-001", reviewer_role=ROLE_RM)
                self.assertEqual(out.state, STATE_APPROVED)
                self.assertEqual([e["event"] for e in out.events],
                                 ["SUBMITTED", STATE_APPROVED])

    def test_governance_rules_identical(self):
        for name, store in self._stores():
            with self.subTest(backend=name):
                rec = store.submit(draft(), submitted_by="RM-001")
                # wrong role
                with self.assertRaises(ApprovalError):
                    store.decide(rec.approval_id, decision=STATE_APPROVED,
                                 reviewer_id="X", reviewer_role="COMPLIANCE_OFFICER")
                # rejection without justification
                with self.assertRaises(ApprovalError):
                    store.decide(rec.approval_id, decision=STATE_REJECTED,
                                 reviewer_id="RM-001", reviewer_role=ROLE_RM)
                # terminal state is final
                store.decide(rec.approval_id, decision=STATE_APPROVED,
                             reviewer_id="RM-001", reviewer_role=ROLE_RM)
                with self.assertRaises(ApprovalError):
                    store.decide(rec.approval_id, decision=STATE_REJECTED,
                                 reviewer_id="RM-001", reviewer_role=ROLE_RM,
                                 justification="changed my mind")

    def test_unknown_id_identical(self):
        for name, store in self._stores():
            with self.subTest(backend=name):
                self.assertIsNone(store.get("nope"))
                self.assertIsNone(store.state_of("nope"))
                with self.assertRaises(ApprovalError):
                    store.decide("nope", decision=STATE_APPROVED,
                                 reviewer_id="RM-001", reviewer_role=ROLE_RM)

    def test_record_shape_identical(self):
        shapes = []
        for name, store in self._stores():
            rec = store.submit(draft(), submitted_by="RM-001")
            shapes.append(set(rec.as_dict()))
        self.assertEqual(shapes[0], shapes[1])


class TestAppendOnlyIntegrity(unittest.TestCase):
    """The audit trail is protected by the database, not by convention."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "audit.db")
        self.store = ApprovalStore(SqliteApprovalStorage(self.db))
        self.record = self.store.submit(draft(), submitted_by="RM-001")
        self.store.decide(self.record.approval_id, decision=STATE_APPROVED,
                          reviewer_id="RM-001", reviewer_role=ROLE_RM)

    def _conn(self):
        return sqlite3.connect(self.db)

    def test_events_cannot_be_updated(self):
        with self._conn() as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE approval_events SET actor = 'someone else'")

    def test_events_cannot_be_deleted(self):
        with self._conn() as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("DELETE FROM approval_events")

    def test_trail_records_both_transitions_with_actors(self):
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM approval_events ORDER BY seq").fetchall()
        self.assertEqual([r["event"] for r in rows], ["SUBMITTED", "APPROVED"])
        self.assertEqual(rows[1]["role"], ROLE_RM)
        self.assertEqual(rows[1]["from_state"], STATE_PENDING_REVIEW)
        self.assertEqual(rows[1]["to_state"], STATE_APPROVED)

    def test_state_projection_agrees_with_the_event_trail(self):
        """The approvals row is a projection; the events are the record."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            projected = conn.execute(
                "SELECT state FROM approvals WHERE approval_id = ?",
                (self.record.approval_id,)).fetchone()["state"]
            last = conn.execute(
                "SELECT to_state FROM approval_events WHERE approval_id = ? "
                "ORDER BY seq DESC LIMIT 1",
                (self.record.approval_id,)).fetchone()["to_state"]
        self.assertEqual(projected, last)

    def test_governance_record_still_holds_no_document_body(self):
        with self._conn() as conn:
            dump = " ".join(str(r) for r in conn.execute(
                "SELECT * FROM approvals").fetchall())
        self.assertNotIn("Dear [CONTACT NAME]", dump)


class TestConcurrentDecisions(unittest.TestCase):
    """Two reviewers acting at once must not both succeed."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "race.db")

    def test_second_decision_loses_cleanly(self):
        storage = SqliteApprovalStorage(self.db)
        record = ApprovalStore(storage).submit(draft(), submitted_by="RM-001")

        results = []
        barrier = threading.Barrier(2)

        def decide(decision, justification=None):
            store = ApprovalStore(SqliteApprovalStorage(self.db))
            barrier.wait()
            try:
                store.decide(record.approval_id, decision=decision,
                             reviewer_id="RM-001", reviewer_role=ROLE_RM,
                             justification=justification)
                results.append(("ok", decision))
            except ApprovalError as exc:
                results.append(("refused", str(exc)))

        threads = [
            threading.Thread(target=decide, args=(STATE_APPROVED,)),
            threading.Thread(target=decide, args=(STATE_REJECTED, "not suitable")),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        outcomes = [r[0] for r in results]
        self.assertEqual(len(results), 2)
        self.assertEqual(outcomes.count("ok"), 1,
                         f"exactly one decision must win, got {results}")
        self.assertEqual(outcomes.count("refused"), 1)

        # The winner's decision is what persisted, and the trail has one decision.
        final = ApprovalStore(SqliteApprovalStorage(self.db)).get(record.approval_id)
        self.assertIn(final.state, (STATE_APPROVED, STATE_REJECTED))
        self.assertEqual(len(final.events), 2)


class TestBackendSelection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._saved = os.environ.get(DEFAULT_DB_ENV)

    def tearDown(self):
        if self._saved is None:
            os.environ.pop(DEFAULT_DB_ENV, None)
        else:
            os.environ[DEFAULT_DB_ENV] = self._saved

    def test_env_var_selects_sqlite(self):
        os.environ[DEFAULT_DB_ENV] = os.path.join(self.tmp, "chosen.db")
        storage = default_storage()
        self.assertEqual(storage.backend_name, "sqlite")
        self.assertTrue(ApprovalStore(storage).durable)

    def test_default_is_in_memory(self):
        os.environ.pop(DEFAULT_DB_ENV, None)
        storage = default_storage()
        self.assertEqual(storage.backend_name, "memory")
        self.assertFalse(ApprovalStore(storage).durable)

    def test_sqlite_creates_missing_directories(self):
        nested = os.path.join(self.tmp, "a", "b", "approvals.db")
        SqliteApprovalStorage(nested)
        self.assertTrue(os.path.exists(nested))


if __name__ == "__main__":
    unittest.main(verbosity=2)
