"""Structured error codes for the capability layer.

Errors are *data*, not exceptions crossing the boundary: every capability
returns an envelope, so a caller (and the Layer-2 contract eval) can assert on
``error.code`` deterministically.
"""

from __future__ import annotations

ERR_VALIDATION = "ERR_VALIDATION"
ERR_NOT_AUTHORIZED = "ERR_NOT_AUTHORIZED"
ERR_UNKNOWN_ACTOR = "ERR_UNKNOWN_ACTOR"
ERR_CLIENT_NOT_FOUND = "ERR_CLIENT_NOT_FOUND"
ERR_OPPORTUNITY_NOT_FOUND = "ERR_OPPORTUNITY_NOT_FOUND"
ERR_UNKNOWN_CAPABILITY = "ERR_UNKNOWN_CAPABILITY"
ERR_INTERNAL = "ERR_INTERNAL"

ALL_ERROR_CODES = (
    ERR_VALIDATION,
    ERR_NOT_AUTHORIZED,
    ERR_UNKNOWN_ACTOR,
    ERR_CLIENT_NOT_FOUND,
    ERR_OPPORTUNITY_NOT_FOUND,
    ERR_UNKNOWN_CAPABILITY,
    ERR_INTERNAL,
)
