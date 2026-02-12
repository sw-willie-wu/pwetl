"""Database dialect strategy factory."""

from pwetl.sinks.dialect.base import BaseDialect, ColumnDef, parse_column_def
from pwetl.sinks.dialect.default import DefaultDialect
from pwetl.sinks.dialect.postgres import PostgresDialect

__all__ = [
    'BaseDialect',
    'ColumnDef',
    'DefaultDialect',
    'PostgresDialect',
    'get_dialect',
    'parse_column_def',
]

_DIALECT_MAP: dict[str, type[BaseDialect]] = {
    "postgresql": PostgresDialect,
}


def get_dialect(dialect_name: str) -> type[BaseDialect]:
    """Get dialect class by name.

    Falls back to DefaultDialect for unknown dialects.
    """
    return _DIALECT_MAP.get(dialect_name, DefaultDialect)
