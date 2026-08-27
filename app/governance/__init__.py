"""Governance package for Project Prometheus.

Policy engine, budget + kill switch, approvals and audit trail.
Cross-slice dependencies (``app.db``, ``app.cost``, ``app.observability``,
``app.cache``) are imported lazily so this package imports standalone.
"""

from app.governance.audit import AuditEvent, append, query
from app.governance.kill_switch import apply_to_decision, get_mode, set_mode

__all__ = [
    "AuditEvent",
    "append",
    "query",
    "get_mode",
    "set_mode",
    "apply_to_decision",
]
