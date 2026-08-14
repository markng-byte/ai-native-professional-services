"""
In-memory graph backend (dev / test / demo).

Uses networkx.MultiDiGraph so the same node pair can hold multiple typed
edges (e.g. OWNS and IS_DIRECTOR_OF). Zero external services — this is the
default backend when NEO4J_URI is not configured.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import networkx as nx

from .base import Edge, GraphBackend


class NetworkXBackend(GraphBackend):
    name = "networkx"

    def __init__(self):
        self.g = nx.MultiDiGraph()

    # ---- mutation ---------------------------------------------------------
    def add_node(self, node_id: str, label: str, props: Optional[Dict] = None) -> None:
        self.g.add_node(node_id, _label=label, **(props or {}))

    def add_edge(self, src: str, dst: str, rel_type: str, props: Optional[Dict] = None) -> None:
        # key=rel_type keeps one edge per (src, dst, type) — idempotent like MERGE
        self.g.add_edge(src, dst, key=rel_type, _type=rel_type, **(props or {}))

    def clear(self) -> None:
        self.g.clear()

    # ---- reads ------------------------------------------------------------
    def _node_dict(self, node_id: str) -> Dict:
        data = self.g.nodes[node_id]
        out = {k: v for k, v in data.items() if k != "_label"}
        out["_id"] = node_id
        out["_label"] = data.get("_label")
        return out

    def get_node(self, node_id: str) -> Optional[Dict]:
        return self._node_dict(node_id) if node_id in self.g.nodes else None

    def nodes_by_label(self, label: str) -> List[Dict]:
        return [self._node_dict(n) for n, d in self.g.nodes(data=True)
                if d.get("_label") == label]

    def out_edges(self, node_id: str, rel_type: Optional[str] = None) -> List[Edge]:
        if node_id not in self.g.nodes:
            return []
        out = []
        for _, dst, key, data in self.g.out_edges(node_id, keys=True, data=True):
            if rel_type is None or key == rel_type:
                props = {k: v for k, v in data.items() if k != "_type"}
                out.append(Edge(node_id, dst, key, props))
        return out

    def in_edges(self, node_id: str, rel_type: Optional[str] = None) -> List[Edge]:
        if node_id not in self.g.nodes:
            return []
        out = []
        for src, _, key, data in self.g.in_edges(node_id, keys=True, data=True):
            if rel_type is None or key == rel_type:
                props = {k: v for k, v in data.items() if k != "_type"}
                out.append(Edge(src, node_id, key, props))
        return out

    def stats(self) -> Dict:
        return {"backend": self.name,
                "nodes": self.g.number_of_nodes(),
                "edges": self.g.number_of_edges()}
