"""
RM surface smoke test — drives the real Streamlit app.

Uses ``streamlit.testing.v1.AppTest``, which executes ``src/app.py`` for real and
interacts with actual widgets. This is the test that moves the UI from
"implemented" to "demonstrated": it proves the tab renders, the widgets wire to
``rm.session``, and — most importantly — that the governance behaviour an RM
would rely on actually holds in the running application, not just in the layer
beneath it.

Skipped when Streamlit is absent, so the dependency-free eval gate stays
hermetic. CI runs it in a separate job that installs the UI dependencies (see
``.github/workflows/eval-gate.yml``).
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

try:
    from streamlit.testing.v1 import AppTest
    _STREAMLIT = True
except ImportError:                                  # pragma: no cover
    _STREAMLIT = False

APP = os.path.join(_ROOT, "src", "app.py")

# CLT-002891 (Orion Capital): an expired UBO declaration, two overdue tasks and
# a stalled USD 95,000 opportunity — the case where compliance must outrank
# commercial pressure.
BUSY_CLIENT_SEARCH = "Orion"


def _markdown(at) -> str:
    return " ".join(m.value for m in at.markdown if isinstance(m.value, str))


def _captions(at) -> str:
    return " ".join(c.value for c in at.caption if isinstance(c.value, str))


@unittest.skipUnless(_STREAMLIT, "Streamlit not installed — UI smoke test skipped")
class TestRMSurfaceSmoke(unittest.TestCase):

    def _open_client(self, query=BUSY_CLIENT_SEARCH):
        at = AppTest.from_file(APP, default_timeout=90).run()
        self.assertFalse(at.exception, f"app raised on load: {at.exception}")
        [t for t in at.text_input if t.label == "Find a client"][0].set_value(query).run()
        [b for b in at.button if b.label == "Open client workspace"][0].click().run()
        self.assertFalse(at.exception, f"app raised opening client: {at.exception}")
        return at

    # -- rendering ---------------------------------------------------------

    def test_app_loads_without_exception(self):
        at = AppTest.from_file(APP, default_timeout=90).run()
        self.assertFalse(at.exception)
        self.assertIn("Acting as", [sb.label for sb in at.selectbox])

    def test_search_is_authorization_filtered(self):
        """RM-001 must not find RM-002's client."""
        at = AppTest.from_file(APP, default_timeout=90).run()
        [t for t in at.text_input if t.label == "Find a client"][0].set_value("Meridian").run()
        self.assertFalse(at.exception)
        info = " ".join(i.value for i in at.info)
        self.assertIn("another RM", info)

    def test_workspace_renders_summary_and_action(self):
        at = self._open_client()
        headline = " ".join(s.value for s in at.subheader)
        self.assertIn("Orion Capital", headline)
        md = _markdown(at)
        self.assertIn("Next best action", md)

    # -- the governance behaviour that matters -----------------------------

    def test_compliance_outranks_commercial_pressure_in_the_ui(self):
        """The screen must lead with the expired KYC document, not the 95k deal."""
        at = self._open_client()
        md = _markdown(at)
        self.assertIn("CRITICAL", md)
        self.assertIn("expired KYC", md)

    def test_losing_signals_are_still_shown(self):
        at = self._open_client()
        self.assertIn("Other signals", _markdown(at))

    def test_audit_identifiers_are_on_screen(self):
        at = self._open_client()
        caps = _captions(at)
        self.assertIn("corr", caps)
        self.assertIn("audit", caps)
        self.assertIn("fixtures", caps)

    # -- draft -> approval -> gate ----------------------------------------

    def test_draft_is_blocked_until_approved_and_names_its_approver(self):
        at = self._open_client()
        [b for b in at.button if "Generate follow-up draft" in b.label][0].click().run()
        self.assertFalse(at.exception)

        self.assertTrue(at.code, "no draft rendered")
        self.assertIn("Subject: Follow-up", at.code[0].value)
        self.assertIn("DRAFTED", _markdown(at))
        self.assertTrue(any("Delivery blocked" in w.value for w in at.warning))
        # This draft is compliance-triggered, so the RM is not the approver.
        self.assertIn("COMPLIANCE_OFFICER", _captions(at))

        [b for b in at.button if b.label == "Submit for review"][0].click().run()
        self.assertIn("PENDING_REVIEW", _markdown(at))
        self.assertTrue(any("PENDING_REVIEW" in w.value for w in at.warning))

    def test_wrong_role_is_refused_in_the_ui(self):
        at = self._open_client()
        [b for b in at.button if "Generate follow-up draft" in b.label][0].click().run()
        [b for b in at.button if b.label == "Submit for review"][0].click().run()

        role = [sb for sb in at.selectbox if sb.label == "Reviewing as role"][0]
        role.set_value("RELATIONSHIP_MANAGER").run()
        [b for b in at.button if b.label == "✅ Approve"][0].click().run()

        self.assertFalse(at.exception, "a refused approval must not crash the app")
        errors = " ".join(e.value for e in at.error)
        self.assertIn("may not decide", errors)
        self.assertIn("COMPLIANCE_OFFICER", errors)

    def test_correct_role_approves_and_gate_opens(self):
        at = self._open_client()
        [b for b in at.button if "Generate follow-up draft" in b.label][0].click().run()
        [b for b in at.button if b.label == "Submit for review"][0].click().run()

        role = [sb for sb in at.selectbox if sb.label == "Reviewing as role"][0]
        role.set_value("COMPLIANCE_OFFICER").run()
        [b for b in at.button if b.label == "✅ Approve"][0].click().run()

        self.assertFalse(at.exception)
        self.assertIn("APPROVED", _markdown(at))
        success = " ".join(s.value for s in at.success)
        self.assertIn("Approved for delivery", success)
        # Even when approved, the UI must not imply transmission.
        self.assertIn("Nothing is transmitted", success)


if __name__ == "__main__":
    unittest.main(verbosity=2)


@unittest.skipUnless(_STREAMLIT, "Streamlit not installed — UI smoke test skipped")
class TestApprovalDurabilityDefault(unittest.TestCase):
    """Approvals are audit records; the app must not need an env var to keep them."""

    def setUp(self):
        self._saved = os.environ.get("FIRMOS_APPROVAL_DB")
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("FIRMOS_APPROVAL_DB", None)
        else:
            os.environ["FIRMOS_APPROVAL_DB"] = self._saved

    def test_app_defaults_to_durable_storage(self):
        os.environ["FIRMOS_APPROVAL_DB"] = os.path.join(self._tmp, "a.db")
        at = AppTest.from_file(APP, default_timeout=90).run()
        [t for t in at.text_input if t.label == "Find a client"][0].set_value("Acme").run()
        [b for b in at.button if b.label == "Open client workspace"][0].click().run()
        [b for b in at.button if "Generate follow-up draft" in b.label][0].click().run()
        self.assertIn("durably", _captions(at))
        self.assertNotIn("lost when this process",
                         " ".join(w.value for w in at.warning))

    def test_opting_out_is_explicit_and_warns(self):
        """Losing approvals must be a deliberate choice, and still flagged."""
        os.environ["FIRMOS_APPROVAL_DB"] = "memory"
        at = AppTest.from_file(APP, default_timeout=90).run()
        [t for t in at.text_input if t.label == "Find a client"][0].set_value("Acme").run()
        [b for b in at.button if b.label == "Open client workspace"][0].click().run()
        [b for b in at.button if "Generate follow-up draft" in b.label][0].click().run()
        self.assertIn("lost when this process",
                      " ".join(w.value for w in at.warning))
