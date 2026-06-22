"""
Neo4j graph backend (production).

Activated when NEO4J_URI is set. Translates the GraphBackend primitives to
Cypher using the official `neo4j` driver. The driver is imported lazily so
the package has no hard dependency on it for dev/test use.

Env vars:
  NEO4J_URI       e.g. neo4j+s://xxxx.databases.neo4j.io
  NEO4J_USER      default "neo4j"
  NEO4J_PASSWORD  required
  NEO4J_DATABASE  default "neo4j"
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from .base import Edge, GraphBackend


class Neo4jBackend(GraphBackend):
    name = "neo4j"

    def __init__(self, uri: str = "", user: str = "", password: str = "",
                 database: str = ""):
        from neo4j import GraphDatabase  # lazy — optional dependency

        self.uri = uri or os.getenv("NEO4J_URI", "")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "")
        self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")
        if not self.uri:
            raise ValueError("NEO4J_URI is not set")
        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        # fail fast if unreachable
        self._driver.verify_connectivity()

    def _run(self, cypher: str, **params):
        with self._driver.session(database=self.database) as s:
            return list(s.run(cypher, **params))

    # ---- mutation ---------------------------------------------------------
    def add_node(self, node_id: str, label: str, props: Optional[Dict] = None) -> None:
        # label is interpolated (validated as identifier) — never user input here
        safe = "".join(c for c in label if c.isalnum() or c == "_")
        self._run(
            f"MERGE (n:`{safe}` {{_id:$id}}) SET n += $props, n._label=$label",
            id=node_id, props=(props or {}), label=label,
        )

    def add_edge(self, src: str, dst: str, rel_type: str, props: Optional[Dict] = None) -> None:
        safe = "".join(c for c in rel_type if c.isalnum() or c == "_")
        self._run(
            f"MATCH (a {{_id:$src}}), (b {{_id:$dst}}) "
            f"MERGE (a)-[r:`{safe}`]->(b) SET r += $props",
            src=src, dst=dst, props=(props or {}),
        )

    def clear(self) -> None:
        self._run("MATCH (n) DETACH DELETE n")

    # ---- reads ------------------------------------------------------------
    @staticmethod
    def _to_dict(node) -> Dict:
        d = dict(node)
        d["_id"] = d.get("_id")
        d["_label"] = d.get("_label") or (list(node.labels)[0] if node.labels else None)
        return d

    def get_node(self, node_id: str) -> Optional[Dict]:
        rows = self._run("MATCH (n {_id:$id}) RETURN n LIMIT 1", id=node_id)
        return self._to_dict(rows[0]["n"]) if rows else None

    def nodes_by_label(self, label: str) -> List[Dict]:
        safe = "".join(c for c in label if c.isalnum() or c == "_")
        rows = self._run(f"MATCH (n:`{safe}`) RETURN n")
        return [self._to_dict(r["n"]) for r in rows]

    def out_edges(self, node_id: str, rel_type: Optional[str] = None) -> List[Edge]:
        filt = "" if rel_type is None else f":`{rel_type}`"
        rows = self._run(
            f"MATCH (a {{_id:$id}})-[r{filt}]->(b) RETURN type(r) AS t, b._id AS dst, properties(r) AS p",
            id=node_id)
        return [Edge(node_id, r["dst"], r["t"], dict(r["p"])) for r in rows]

    def in_edges(self, node_id: str, rel_type: Optional[str] = None) -> List[Edge]:
        filt = "" if rel_type is None else f":`{rel_type}`"
        rows = self._run(
            f"MATCH (a)-[r{filt}]->(b {{_id:$id}}) RETURN type(r) AS t, a._id AS src, properties(r) AS p",
            id=node_id)
        return [Edge(r["src"], node_id, r["t"], dict(r["p"])) for r in rows]

    def stats(self) -> Dict:
        n = self._run("MATCH (n) RETURN count(n) AS c")[0]["c"]
        e = self._run("MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
        return {"backend": self.name, "nodes": n, "edges": e}

    def close(self):
        self._driver.close()
