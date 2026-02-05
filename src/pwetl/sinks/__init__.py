"""Data sinks for pwetl."""

from pwetl.sinks.base import BaseSink
from pwetl.sinks.file import FileSink
from pwetl.sinks.database import DatabaseSink
from pwetl.sinks.api import APISink

__all__ = [
    "BaseSink",
    "FileSink",
    "DatabaseSink",
    "APISink",
]


# Registration function to avoid circular imports
def _register_sinks():
    """Register built-in Sinks to Registry."""
    from pwetl.core.registry import SINK_REGISTRY

    SINK_REGISTRY.update(
        {
            "file": FileSink,
            "csv": FileSink,
            "json": FileSink,
            "jsonl": FileSink,
            "postgresql": DatabaseSink,
            "mysql": DatabaseSink,
            "api": APISink,
        }
    )
