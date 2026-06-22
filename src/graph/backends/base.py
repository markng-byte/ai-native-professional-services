"""
Backend abstraction for the GraphRAG engine.

Two implementations satisfy this interface:
  - NetworkXBackend : in-memory, dev/test, zero external services
  - Neo4jBackend    : production, via the official neo4j driver

The interface is intentionally minimal — just enough graph primitives for the
7 canonical query patterns in GRAPH_SCHEMA.md to be expressed once (in
queries.py) and run unchanged on either backend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Edge:
    src: str
    dst: str
    type: str
    props: Dict = field(default_factory=dict)


class GraphBackend(ABC):
    """Minimal graph store: labelled nodes + typed, directed, property edges."""

    name: str = "abstract"

    # ---- mutation ---------------------------------------------------------
    @abstractmethod
    def add_node(self, node_id: str, label: str, props: Optional[Dict] = None) -> None:
        ...

    @abstractmethod
    def add_edge(self, src: str, dst: str, rel_type: str, props: Optional[Dict] = None) -> None:
        ...

    @abstractmethod
    def clear(self) -> None:
        ...

    # ---- reads ------------------------------------------------------------
    @abstractmethod
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Return node props (including _id and _label) or None."""
        ...

    @abstractmethod
    def nodes_by_label(self, label: str) -> List[Dict]:
        """Return all nodes with the given label (each dict has _id/_label)."""
        ...

    @abstractmethod
    def in_edges(self, node_id: str, rel_type: Optional[str] = None) -> List[Edge]:
        ...

    @abstractmethod
    def out_edges(self, node_id: str, rel_type: Optional[str] = None) -> List[Edge]:
        ...

    # ---- convenience ------------------------------------------------------
    def find_nodes(self, label: str, **prop_filter) -> List[Dict]:
        """Return nodes of `label` whose props match all key/value pairs."""
        out = []
        for n in self.nodes_by_label(label):
            if all(str(n.get(k, "")).lower() == str(v).lower() for k, v in prop_filter.items()):
                out.append(n)
        return out

    def search_nodes(self, label: str, field_name: str, needle: str) -> List[Dict]:
        """Case-insensitive substring search on a single property."""
        needle = needle.lower().strip()
        return [n for n in self.nodes_by_label(label)
                if needle and needle in str(n.get(field_name, "")).lower()]

    @abstractmethod
    def stats(self) -> Dict:
        ...

    def load_dict(self, data: Dict) -> None:
        """Bulk-load a {nodes:[...], edges:[...]} dict (used by the seed loader)."""
        for n in data.get("nodes", []):
            props = {k: v for k, v in n.items() if k not in ("id", "label")}
            self.add_node(n["id"], n["label"], props)
        for e in data.get("edges", []):
            props = {k: v for k, v in e.items() if k not in ("from", "to", "type")}
            self.add_edge(e["from"], e["to"], e["type"], props)
