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

# 註冊函數，避免循環引用
def _register_sources():
    """註冊內建 Sources 到 Registry。"""
    from pwetl.core.registry import SOURCE_REGISTRY

    SOURCE_REGISTRY.update({
        'file': FileSource,
        'csv': FileSource,
        'json': FileSource,
        'jsonl': FileSource,
        'parquet': FileSource,
        'api': APISource,
        'postgresql': DatabaseSource,
        'mysql': DatabaseSource,
    })
