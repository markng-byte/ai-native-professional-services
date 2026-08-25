"""
Actor-based authorization for capability tools.

Master prompt §21: *design authorization around the actor, not merely the tool.*
A tool being technically able to retrieve a record is **not** authorization to
expose it. The same `get_client_history` capability must answer differently for
an RM, a future client-portal user, and a future channel agent.

v1 policy (decision D2 — provisional)
-------------------------------------
* Actor type ``RM``: may read a client **only if that RM is the assigned RM**
  for the client. Denial is explicit (``ERR_NOT_AUTHORIZED``), never a silent
  empty result — a silent empty would read as "no data" and could mislead the
  RM into a wrong conclusion.
* An unknown ``rm_id`` is rejected with ``ERR_UNKNOWN_ACTOR``.
* Client-portal / channel actor types are **deliberately unimplemented**: they
  are a different authorization scope (§21) and are out of v1 scope. Requesting
  one raises rather than silently falling back to RM scope.

Every decision returns a structured record so it can be written to the audit
trail (``authorization_result`` in `governance/GOVERNANCE.md` §5.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from capabilities.errors import ERR_NOT_AUTHORIZED, ERR_UNKNOWN_ACTOR

ACTOR_RM = "RM"


@dataclass(frozen=True)
class Actor:
    actor_type: str
    actor_id: str

    @property
    def is_rm(self) -> bool:
        return self.actor_type == ACTOR_RM


@dataclass(frozen=True)
class AuthzDecision:
    allowed: bool
    reason: str
    error_code: Optional[str] = None

    def as_audit(self) -> Dict:
        return {"allowed": self.allowed, "reason": self.reason}


def parse_actor(payload: Dict) -> Optional[Actor]:
    """Extract the actor from a request payload, or ``None`` if malformed."""
    raw = payload.get("actor")
    if not isinstance(raw, dict):
        return None
    actor_type = raw.get("actor_type", ACTOR_RM)
    actor_id = raw.get("rm_id") or raw.get("actor_id")
    if not actor_id or not isinstance(actor_id, str):
        return None
    if actor_type != ACTOR_RM:
        # Non-RM scopes are a different authorization model (§21). Refuse
        # rather than silently treating them as an RM.
        raise NotImplementedError(
            f"Actor type {actor_type!r} is not supported in v1; only 'RM' is "
            "implemented. Client-portal and channel scopes are deferred."
        )
    return Actor(actor_type, actor_id)


def authorize_client_access(actor: Actor, client, adapter) -> AuthzDecision:
    """Decide whether ``actor`` may read ``client``."""
    if adapter.get_rm(actor.actor_id) is None:
        return AuthzDecision(
            False, f"Unknown actor {actor.actor_id!r}.", ERR_UNKNOWN_ACTOR
        )
    if client.assigned_rm_id != actor.actor_id:
        return AuthzDecision(
            False,
            f"Client {client.client_id} is assigned to {client.assigned_rm_id}, "
            f"not to requesting RM {actor.actor_id}.",
            ERR_NOT_AUTHORIZED,
        )
    return AuthzDecision(True, f"RM {actor.actor_id} is the assigned RM for {client.client_id}.")


def authorize_actor_known(actor: Actor, adapter) -> AuthzDecision:
    """Validate the actor exists, without reference to a specific client."""
    if adapter.get_rm(actor.actor_id) is None:
        return AuthzDecision(
            False, f"Unknown actor {actor.actor_id!r}.", ERR_UNKNOWN_ACTOR
        )
    return AuthzDecision(True, f"Actor {actor.actor_id} recognised.")
