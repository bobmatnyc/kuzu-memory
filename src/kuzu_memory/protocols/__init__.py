"""
Service protocol interfaces for dependency injection.

This module defines Protocol interfaces for all major services in the system,
enabling clean dependency injection and improved testability.
"""

from kuzu_memory.protocols.services import (
    IConfigService,
    IDiagnosticService,
    IGitSyncService,
    IInstallerService,
    IMemoryService,
    ISetupService,
)

__all__ = [
    "IConfigService",
    "IDiagnosticService",
    "IGitSyncService",
    "IInstallerService",
    "IMemoryService",
    "ISetupService",
]
