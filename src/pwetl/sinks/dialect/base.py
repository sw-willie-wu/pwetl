"""Base dialect interface for database sinks."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)


@dataclass
class ColumnDef:
    """Parsed column definition."""

    type_str: str  # e.g. 'uuid', 'varchar(100)', 'float'
    pk: bool
    nullable: bool


def parse_column_def(col_def: str) -> ColumnDef:
    """Parse column definition string into ColumnDef.

    Syntax: <type>[?] [, pk]
      - '?' suffix marks nullable
      - 'pk' modifier marks primary key

    Examples:
        >>> parse_column_def('uuid, pk')
        ColumnDef(type_str='uuid', pk=True, nullable=False)
        >>> parse_column_def('float?')
        ColumnDef(type_str='float', pk=False, nullable=True)
        >>> parse_column_def('varchar(100)')
        ColumnDef(type_str='varchar(100)', pk=False, nullable=False)
    """
    parts = [p.strip() for p in col_def.split(',')]
    type_str = parts[0]
    modifiers = {p.lower() for p in parts[1:]}

    nullable = type_str.endswith('?')
    if nullable:
        type_str = type_str[:-1]

    return ColumnDef(
        type_str=type_str,
        pk='pk' in modifiers,
        nullable=nullable,
    )


class BaseDialect(ABC):
    """Abstract base class for database dialect strategies."""

    def __init__(self, engine, table_name: str):
        self._engine = engine
        self._table_name = table_name

    @abstractmethod
    def insert(self, records: list[dict]) -> int:
        """Insert records into the table.

        Returns:
            Number of records inserted.
        """

    @abstractmethod
    def upsert(self, records: list[dict], primary_key: list[str]) -> int:
        """Upsert records into the table.

        Returns:
            Number of records upserted.
        """

    def ensure_table(self, columns_config: dict[str, str]) -> None:
        """Create table from columns config if it doesn't exist.

        Override in dialect subclass to support dialect-specific types.
        Default implementation does nothing.
        """

    def table_exists(self) -> bool:
        """Check if table exists using SQLAlchemy inspect."""
        from sqlalchemy import inspect

        inspector = inspect(self._engine)
        return inspector.has_table(self._table_name)
