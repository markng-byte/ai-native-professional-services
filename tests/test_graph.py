"""Tests for the GraphRAG foundation (NetworkX dev backend + seed data)."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from graph.engine import GraphRAGEngine          # noqa: E402
from graph.backends.networkx_backend import NetworkXBackend  # noqa: E402
from graph import queries, render                # noqa: E402


def _engine():
    # force the NetworkX seed backend regardless of NEO4J_URI
    os.environ.pop("NEO4J_URI", None)
    return GraphRAGEngine()


def test_seed_loads():
    eng = _engine()
    info = eng.info()
    assert info["backend"] == "networkx"
    assert info["nodes"] > 10 and info["edges"] > 5


def test_jurisdiction_compare():
    eng = _engine()
    res = eng.compare_jurisdictions(["VG", "KY", "SG"])
    assert len(res["found"]) == 3
    codes = {j["jurisdiction_code"] for j in res["found"]}
    assert codes == {"VG", "KY", "SG"}


def test_jurisdiction_missing_flagged():
    eng = _engine()
    res = eng.compare_jurisdictions(["VG", "ZZ"])
    assert "ZZ" in res["missing"]


def test_ubo_resolves_to_100_via_two_paths():
    """John Doe owns 60% directly + 40% via Meridian Trust = 100% across 2 paths."""
    eng = _engine()
    target = eng.resolve_ubo_target("Atlas")
    assert target == "LE-ATLASHLDG"
    res = eng.get_ubo(target)
    assert "IND-JDOE" in res["ubos"]
    jdoe = res["ubos"]["IND-JDOE"]
    assert round(jdoe["pct"]) == 100
    assert jdoe["paths"] == 2


def test_resolve_ubo_from_client_name():
    eng = _engine()
    # "Project Atlas Group" is a Client → should hop to its holding entity
    assert eng.resolve_ubo_target("Project Atlas Group") == "LE-ATLASHLDG"


def test_mandates_due_window():
    eng = _engine()
    # reference date matches the seed horizon
    due = queries.mandates_due(eng.backend, within_days=90, today=date(2026, 6, 20))
    clients = {r["client"] for r in due}
    assert {"Orion Capital", "Nova Trust", "Vertex Pte", "Helios Group"} <= clients
    # Nova Trust KYC refresh (2026-06-28) is the most urgent
    assert due[0]["client"] == "Nova Trust"
    assert due[0]["days"] == 8


def test_render_outputs_are_graph_backed():
    eng = _engine()
    assert "GraphRAG" in render.jurisdiction_compare(eng, ["VG", "KY"])
    assert "GraphRAG" in render.ubo_chain(eng, "Atlas")
    md = render.mandates(eng, 90)
    # mandates render uses today(); just assert it returns a table when in-window
    if md:
        assert "GraphRAG" in md


def test_networkx_backend_directly():
    b = NetworkXBackend()
    b.add_node("A", "Legal_Entity", {"registered_name": "A Ltd"})
    b.add_node("P", "Individual", {"full_name": "Person"})
    b.add_edge("P", "A", "OWNS", {"ownership_pct": 100})
    assert b.get_node("A")["registered_name"] == "A Ltd"
    ins = b.in_edges("A", "OWNS")
    assert len(ins) == 1 and ins[0].src == "P"
    assert b.stats()["nodes"] == 2


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn(); print(f"  ✅ {fn.__name__}"); passed += 1
        except Exception:
            print(f"  ❌ {fn.__name__}"); traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
