"""
GraphRAGEngine — the single read interface agents use to query the knowledge
graph (Tool #1 in TOOL_REGISTRY.md).

Backend selection:
  - NEO4J_URI set  → Neo4jBackend (production)
  - otherwise      → NetworkXBackend seeded from src/graph/seed/seed_data.json

A process-wide singleton is exposed via get_engine().
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from . import queries
from .backends.base import GraphBackend
from .backends.networkx_backend import NetworkXBackend

_SEED_PATH = Path(__file__).parent / "seed" / "seed_data.json"


def _load_seed(backend: GraphBackend) -> None:
    if _SEED_PATH.exists():
        with open(_SEED_PATH, "r", encoding="utf-8") as f:
            backend.load_dict(json.load(f))


class GraphRAGEngine:
    def __init__(self, backend: Optional[GraphBackend] = None):
        self.backend = backend or self._auto_backend()

    @staticmethod
    def _auto_backend() -> GraphBackend:
        if os.getenv("NEO4J_URI"):
            try:
                from .backends.neo4j_backend import Neo4jBackend
                return Neo4jBackend()
            except Exception as e:  # unreachable / driver missing → dev fallback
                print(f"[GraphRAG] Neo4j unavailable ({e}); using NetworkX seed backend.")
        b = NetworkXBackend()
        _load_seed(b)
        return b

    # ---- facade over canonical queries -----------------------------------
    def info(self) -> Dict:
        s = self.backend.stats()
        s["mode"] = "production" if s["backend"] == "neo4j" else "dev (seed data)"
        return s

    def compare_jurisdictions(self, codes: List[str]) -> Dict:
        return queries.compare_jurisdictions(self.backend, codes)

    def resolve_ubo_target(self, name: str) -> Optional[str]:
        return queries.resolve_ubo_target(self.backend, name)

    def get_ubo(self, entity_id: str) -> Dict:
        return queries.get_ubo(self.backend, entity_id)

    def mandates_due(self, within_days: int = 90) -> List[Dict]:
        return queries.mandates_due(self.backend, within_days)

    def has_jurisdiction_data(self) -> bool:
        return bool(self.backend.nodes_by_label("Jurisdiction"))


@lru_cache(maxsize=1)
def get_engine() -> GraphRAGEngine:
    """Process-wide singleton."""
    return GraphRAGEngine()
