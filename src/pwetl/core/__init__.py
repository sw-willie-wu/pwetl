"""Core modules for pwetl."""
from pwetl.core.registry import (
    SOURCE_REGISTRY,
    SINK_REGISTRY,
    SourceFactory,
    SinkFactory,
)

__all__ = [
    'SOURCE_REGISTRY',
    'SINK_REGISTRY',
    'SourceFactory',
    'SinkFactory',
]
