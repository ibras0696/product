"""Framework-free application contracts exposed by audit."""

from modules.audit.repository import SqlAuditRepository

__all__ = ["SqlAuditRepository"]
