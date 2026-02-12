"""PostgreSQL dialect with native upsert and type support."""

import re

from sqlalchemy import (
    Column,
    MetaData,
    Table,
    inspect,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, insert
from sqlalchemy.types import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Integer,
    SmallInteger,
    String,
    Text,
)

from pwetl.sinks.dialect.base import BaseDialect, parse_column_def
from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)

_VARCHAR_RE = re.compile(r"^varchar\((\d+)\)$", re.IGNORECASE)


def _parse_column_type(type_str: str):
    """Parse a column type string into a SQLAlchemy type.

    Supported: uuid, text, varchar(N), integer, bigint, smallint, float,
               boolean, datetime, timestamptz, geometry.
    """
    type_str_lower = type_str.lower().strip()

    m = _VARCHAR_RE.match(type_str_lower)
    if m:
        return String(int(m.group(1)))

    # geometry is handled via raw SQL, skip SQLAlchemy type mapping
    if type_str_lower == "geometry":
        return None

    type_map = {
        "uuid": UUID(as_uuid=False),
        "text": Text(),
        "str": Text(),
        "string": Text(),
        "integer": Integer(),
        "int": Integer(),
        "bigint": BigInteger(),
        "smallint": SmallInteger(),
        "float": Float(),
        "double": Float(),
        "boolean": Boolean(),
        "bool": Boolean(),
        "datetime": DateTime(timezone=True),
        "timestamptz": DateTime(timezone=True),
    }

    if type_str_lower in type_map:
        return type_map[type_str_lower]

    raise ValueError(f"Unknown column type: {type_str}")


class PostgresDialect(BaseDialect):
    """PostgreSQL dialect with ON CONFLICT DO UPDATE upsert."""

    def __init__(self, engine, table_name: str):
        super().__init__(engine, table_name)
        self._sa_table = None

    def insert(self, records: list[dict]) -> int:
        """Insert using sqlalchemy.dialects.postgresql.insert."""
        if not records:
            return 0

        sa_table = self._get_sa_table()
        stmt = insert(sa_table).values(records)

        with self._engine.begin() as conn:
            conn.execute(stmt)

        return len(records)

    def upsert(self, records: list[dict], primary_key: list[str]) -> int:
        """Upsert using INSERT ON CONFLICT DO UPDATE."""
        if not records:
            return 0

        sa_table = self._get_sa_table()

        update_cols = [c for c in records[0].keys() if c not in primary_key]
        stmt = insert(sa_table).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=primary_key,
            set_={col: stmt.excluded[col] for col in update_cols},
        )

        with self._engine.begin() as conn:
            conn.execute(stmt)

        return len(records)

    def ensure_table(self, columns_config: dict[str, str]) -> None:
        """Create table with PostgreSQL-specific types."""
        inspector = inspect(self._engine)
        if inspector.has_table(self._table_name):
            LOGGER.info(
                "Sink: table '%s' already exists, using existing schema",
                self._table_name,
            )
            metadata = MetaData()
            self._sa_table = Table(
                self._table_name, metadata, autoload_with=self._engine
            )
            return

        metadata = MetaData()
        geom_columns = []
        sa_columns = []

        for col_name, col_def_str in columns_config.items():
            col_def = parse_column_def(col_def_str)
            sa_type = _parse_column_type(col_def.type_str)

            if sa_type is None:
                # geometry — will be added via raw SQL after table creation
                geom_columns.append(col_name)
                continue

            sa_columns.append(
                Column(
                    col_name,
                    sa_type,
                    primary_key=col_def.pk,
                    nullable=col_def.nullable,
                )
            )

        self._sa_table = Table(self._table_name, metadata, *sa_columns)
        metadata.create_all(self._engine)
        LOGGER.info("Sink: created table '%s'", self._table_name)

        if geom_columns:
            self._add_geometry_columns(geom_columns)

    def _add_geometry_columns(self, geom_columns: list[str]) -> None:
        """Add PostGIS geometry columns and spatial indexes via raw SQL."""
        with self._engine.begin() as conn:
            for col in geom_columns:
                conn.execute(text(
                    f"ALTER TABLE {self._table_name} "
                    f"ADD COLUMN IF NOT EXISTS {col} geometry(Point, 4326)"
                ))
                conn.execute(text(
                    f"CREATE INDEX IF NOT EXISTS idx_{self._table_name}_{col} "
                    f"ON {self._table_name} USING GIST({col})"
                ))
        LOGGER.info(
            "Sink: added geometry columns %s on '%s'",
            geom_columns, self._table_name,
        )

    def _get_sa_table(self) -> Table:
        """Get or load SQLAlchemy Table object."""
        if self._sa_table is not None:
            return self._sa_table

        metadata = MetaData()
        self._sa_table = Table(
            self._table_name, metadata, autoload_with=self._engine
        )
        return self._sa_table
