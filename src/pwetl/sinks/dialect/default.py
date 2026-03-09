"""Default dialect using raw SQL INSERT."""

from sqlalchemy import text

from pwetl.sinks.dialect.base import BaseDialect
from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)


class DefaultDialect(BaseDialect):
    """Fallback dialect using raw SQL.

    Works with any SQLAlchemy-compatible database.
    Upsert falls back to DELETE + INSERT (non-atomic).
    """

    def insert(self, records: list[dict]) -> int:
        """Bulk INSERT using raw SQL."""
        if not records:
            return 0

        columns = list(records[0].keys())
        col_str = ', '.join(columns)
        param_str = ', '.join(f':{c}' for c in columns)
        insert_sql = text(
            f"INSERT INTO {self._table_name} ({col_str}) VALUES ({param_str})"
        )

        with self._engine.connect() as conn:
            conn.execute(insert_sql, records)
            conn.commit()

        return len(records)

    def upsert(self, records: list[dict], primary_key: list[str]) -> int:
        """Fallback upsert: DELETE by PK + INSERT (non-atomic)."""
        if not records:
            return 0

        LOGGER.warning(
            "Sink: default dialect upsert is non-atomic (DELETE + INSERT)"
        )

        # Build DELETE by PK
        pk_conditions = ' AND '.join(f'{pk} = :{pk}' for pk in primary_key)
        delete_sql = text(
            f"DELETE FROM {self._table_name} WHERE {pk_conditions}"
        )

        # Build INSERT
        columns = list(records[0].keys())
        col_str = ', '.join(columns)
        param_str = ', '.join(f':{c}' for c in columns)
        insert_sql = text(
            f"INSERT INTO {self._table_name} ({col_str}) VALUES ({param_str})"
        )

        with self._engine.connect() as conn:
            for record in records:
                pk_vals = {pk: record[pk] for pk in primary_key}
                conn.execute(delete_sql, pk_vals)
            conn.execute(insert_sql, records)
            conn.commit()

        return len(records)
