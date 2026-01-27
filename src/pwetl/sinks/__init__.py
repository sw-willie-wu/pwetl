"""Data sinks for pwetl."""
from pwetl.sinks.base import BaseSink
from pwetl.sinks.file import FileSink
from pwetl.sinks.database import DatabaseSink
from pwetl.sinks.api import APISink

__all__ = [
    'BaseSink',
    'FileSink',
    'DatabaseSink',
    'APISink',
]

# 註冊函數，避免循環引用
def _register_sinks():
    """註冊內建 Sinks 到 Registry。"""
    from pwetl.core.registry import SINK_REGISTRY

    SINK_REGISTRY.update({
        'file': FileSink,
        'csv': FileSink,
        'json': FileSink,
        'jsonl': FileSink,
        'parquet': FileSink,
        'postgresql': DatabaseSink,
        'mysql': DatabaseSink,
        'api': APISink,
    })
