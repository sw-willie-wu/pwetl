"""Data sources for pwetl."""
from pwetl.sources.base import BaseSource
from pwetl.sources.file import FileSource
from pwetl.sources.api import APISource
from pwetl.sources.database import DatabaseSource

__all__ = [
    'BaseSource',
    'FileSource',
    'APISource',
    'DatabaseSource',
]

# Registration function to avoid circular imports
def _register_sources():
    """Register built-in Sources to Registry."""
    from pwetl.core.registry import SOURCE_REGISTRY

    SOURCE_REGISTRY.update({
        'file': FileSource,
        'csv': FileSource,
        'json': FileSource,
        'jsonl': FileSource,
        'api': APISource,
        'database': DatabaseSource,
    })
