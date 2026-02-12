"""Tests for database dialect module."""

import pytest
from unittest.mock import MagicMock, patch


class TestParseColumnDef:
    """Test parse_column_def function."""

    def test_simple_type(self):
        from pwetl.sinks.dialect.base import parse_column_def

        result = parse_column_def('int')
        assert result.type_str == 'int'
        assert result.pk is False
        assert result.nullable is False

    def test_with_pk(self):
        from pwetl.sinks.dialect.base import parse_column_def

        result = parse_column_def('uuid, pk')
        assert result.type_str == 'uuid'
        assert result.pk is True
        assert result.nullable is False

    def test_nullable(self):
        from pwetl.sinks.dialect.base import parse_column_def

        result = parse_column_def('float?')
        assert result.type_str == 'float'
        assert result.pk is False
        assert result.nullable is True

    def test_nullable_with_pk(self):
        from pwetl.sinks.dialect.base import parse_column_def

        result = parse_column_def('text?, pk')
        assert result.type_str == 'text'
        assert result.pk is True
        assert result.nullable is True

    def test_varchar_with_length(self):
        from pwetl.sinks.dialect.base import parse_column_def

        result = parse_column_def('varchar(100)')
        assert result.type_str == 'varchar(100)'
        assert result.pk is False
        assert result.nullable is False

    def test_varchar_with_pk(self):
        from pwetl.sinks.dialect.base import parse_column_def

        result = parse_column_def('varchar(50), pk')
        assert result.type_str == 'varchar(50)'
        assert result.pk is True
        assert result.nullable is False


class TestGetDialect:
    """Test get_dialect factory."""

    def test_postgresql(self):
        from pwetl.sinks.dialect import get_dialect
        from pwetl.sinks.dialect.postgres import PostgresDialect

        assert get_dialect('postgresql') is PostgresDialect

    def test_unknown_returns_default(self):
        from pwetl.sinks.dialect import get_dialect
        from pwetl.sinks.dialect.default import DefaultDialect

        assert get_dialect('sqlite') is DefaultDialect
        assert get_dialect('mysql') is DefaultDialect
        assert get_dialect('mssql') is DefaultDialect

    def test_empty_string_returns_default(self):
        from pwetl.sinks.dialect import get_dialect
        from pwetl.sinks.dialect.default import DefaultDialect

        assert get_dialect('') is DefaultDialect


class TestColumnDef:
    """Test ColumnDef dataclass."""

    def test_create(self):
        from pwetl.sinks.dialect.base import ColumnDef

        col = ColumnDef(type_str='uuid', pk=True, nullable=False)
        assert col.type_str == 'uuid'
        assert col.pk is True
        assert col.nullable is False


class TestBaseDialect:
    """Test BaseDialect abstract class."""

    def test_table_exists(self):
        from pwetl.sinks.dialect.base import BaseDialect

        mock_engine = MagicMock()

        # Can't instantiate BaseDialect directly, but can test via subclass
        from pwetl.sinks.dialect.default import DefaultDialect

        dialect = DefaultDialect(mock_engine, 'test_table')

        with patch('sqlalchemy.inspect') as mock_inspect:
            mock_inspector = MagicMock()
            mock_inspector.has_table.return_value = True
            mock_inspect.return_value = mock_inspector

            assert dialect.table_exists() is True
            mock_inspector.has_table.assert_called_once_with('test_table')


class TestDefaultDialect:
    """Test DefaultDialect."""

    def test_insert_empty_records(self):
        from pwetl.sinks.dialect.default import DefaultDialect

        dialect = DefaultDialect(MagicMock(), 'test_table')
        assert dialect.insert([]) == 0

    def test_insert_calls_execute(self):
        from pwetl.sinks.dialect.default import DefaultDialect

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(
            return_value=False
        )

        dialect = DefaultDialect(mock_engine, 'test_table')
        records = [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]

        result = dialect.insert(records)

        assert result == 2
        mock_conn.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_upsert_empty_records(self):
        from pwetl.sinks.dialect.default import DefaultDialect

        dialect = DefaultDialect(MagicMock(), 'test_table')
        assert dialect.upsert([], ['id']) == 0

    def test_upsert_calls_delete_and_insert(self):
        from pwetl.sinks.dialect.default import DefaultDialect

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(
            return_value=False
        )

        dialect = DefaultDialect(mock_engine, 'test_table')
        records = [{'id': 1, 'name': 'Alice'}]

        result = dialect.upsert(records, ['id'])

        assert result == 1
        # DELETE + INSERT = at least 2 execute calls
        assert mock_conn.execute.call_count >= 2
        mock_conn.commit.assert_called_once()


class TestPostgresDialectParseColumnType:
    """Test _parse_column_type function."""

    def test_uuid(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.dialects.postgresql import UUID

        result = _parse_column_type('uuid')
        assert isinstance(result, UUID)

    def test_text(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.types import Text

        result = _parse_column_type('text')
        assert isinstance(result, Text)

    def test_str_maps_to_text(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.types import Text

        result = _parse_column_type('str')
        assert isinstance(result, Text)

    def test_integer(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.types import Integer

        result = _parse_column_type('integer')
        assert isinstance(result, Integer)

    def test_int_shorthand(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.types import Integer

        result = _parse_column_type('int')
        assert isinstance(result, Integer)

    def test_bigint(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.types import BigInteger

        result = _parse_column_type('bigint')
        assert isinstance(result, BigInteger)

    def test_smallint(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.types import SmallInteger

        result = _parse_column_type('smallint')
        assert isinstance(result, SmallInteger)

    def test_float(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.types import Float

        result = _parse_column_type('float')
        assert isinstance(result, Float)

    def test_boolean(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.types import Boolean

        result = _parse_column_type('boolean')
        assert isinstance(result, Boolean)

    def test_bool_shorthand(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.types import Boolean

        result = _parse_column_type('bool')
        assert isinstance(result, Boolean)

    def test_datetime(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.types import DateTime

        result = _parse_column_type('datetime')
        assert isinstance(result, DateTime)

    def test_timestamptz(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.types import DateTime

        result = _parse_column_type('timestamptz')
        assert isinstance(result, DateTime)

    def test_varchar_with_length(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.types import String

        result = _parse_column_type('varchar(255)')
        assert isinstance(result, String)
        assert result.length == 255

    def test_geometry_returns_none(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type

        result = _parse_column_type('geometry')
        assert result is None

    def test_unknown_type_raises(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type

        with pytest.raises(ValueError, match="Unknown column type"):
            _parse_column_type('unknown_type')

    def test_case_insensitive(self):
        from pwetl.sinks.dialect.postgres import _parse_column_type
        from sqlalchemy.types import Integer

        result = _parse_column_type('INTEGER')
        assert isinstance(result, Integer)


class TestPostgresDialect:
    """Test PostgresDialect insert/upsert."""

    def test_insert_empty_records(self):
        from pwetl.sinks.dialect.postgres import PostgresDialect

        dialect = PostgresDialect(MagicMock(), 'test_table')
        assert dialect.insert([]) == 0

    def test_upsert_empty_records(self):
        from pwetl.sinks.dialect.postgres import PostgresDialect

        dialect = PostgresDialect(MagicMock(), 'test_table')
        assert dialect.upsert([], ['id']) == 0
