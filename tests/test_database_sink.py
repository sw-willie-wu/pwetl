"""Tests for DatabaseSink."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock


class TestDatabaseSinkConfig:
    """Test configuration validation."""

    def test_missing_dsn_raises(self):
        """Test that missing dsn raises ValueError."""
        from pwetl.sinks.database import DatabaseSink

        with pytest.raises(ValueError, match="dsn"):
            DatabaseSink('test', {'table': 'my_table'})

    def test_missing_table_raises(self):
        """Test that missing table raises ValueError."""
        from pwetl.sinks.database import DatabaseSink

        with pytest.raises(ValueError, match="table"):
            DatabaseSink('test', {'dsn': 'sqlite://'})

    def test_valid_config(self):
        """Test that valid config does not raise."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })
        assert sink.config['dsn'] == 'sqlite://'
        assert sink.config['table'] == 'output_table'

    def test_default_values(self):
        """Test default values for optional config."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })
        assert sink.config['write_mode'] == 'insert'
        assert sink.config['primary_key'] is None
        assert sink.config['columns'] is None
        assert sink.config['init_sql'] is None
        assert sink.config['dialect'] is None
        assert sink.config['ssh_tunnel'] is None

    def test_invalid_write_mode_raises(self):
        """Test that invalid write_mode raises ValueError."""
        from pwetl.sinks.database import DatabaseSink

        with pytest.raises(ValueError, match="write_mode"):
            DatabaseSink('test', {
                'dsn': 'sqlite://',
                'table': 'output_table',
                'write_mode': 'merge',
            })

    def test_upsert_requires_primary_key(self):
        """Test that upsert without primary_key raises ValueError."""
        from pwetl.sinks.database import DatabaseSink

        with pytest.raises(ValueError, match="primary_key"):
            DatabaseSink('test', {
                'dsn': 'sqlite://',
                'table': 'output_table',
                'write_mode': 'upsert',
            })

    def test_upsert_with_primary_key_ok(self):
        """Test that upsert with primary_key does not raise."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
            'write_mode': 'upsert',
            'primary_key': ['id'],
        })
        assert sink.config['write_mode'] == 'upsert'

    def test_upsert_with_columns_pk_ok(self):
        """Test that upsert with pk in columns does not raise."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
            'write_mode': 'upsert',
            'columns': {'id': 'uuid, pk', 'name': 'text'},
        })
        assert sink.config['write_mode'] == 'upsert'

    def test_columns_and_init_sql_conflict(self):
        """Test that columns and init_sql together raises ValueError."""
        from pwetl.sinks.database import DatabaseSink

        with pytest.raises(ValueError, match="mutually exclusive"):
            DatabaseSink('test', {
                'dsn': 'sqlite://',
                'table': 'output_table',
                'columns': {'id': 'int, pk'},
                'init_sql': 'setup.sql',
            })


class TestResolvePrimaryKey:
    """Test _resolve_primary_key logic."""

    def test_from_config(self):
        """Test PK from primary_key config."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 't',
            'write_mode': 'upsert',
            'primary_key': ['id', 'code'],
        })
        assert sink._resolve_primary_key() == ['id', 'code']

    def test_from_columns_pk(self):
        """Test PK extracted from columns pk modifier."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 't',
            'write_mode': 'upsert',
            'columns': {
                'id': 'uuid, pk',
                'name': 'text',
                'code': 'varchar(10), pk',
            },
        })
        assert sink._resolve_primary_key() == ['id', 'code']

    def test_config_overrides_columns(self):
        """Test that primary_key config takes precedence over columns pk."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 't',
            'write_mode': 'upsert',
            'primary_key': ['custom_pk'],
            'columns': {'id': 'uuid, pk', 'name': 'text'},
        })
        assert sink._resolve_primary_key() == ['custom_pk']

    def test_none_when_no_pk(self):
        """Test None when no PK is available."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 't',
        })
        assert sink._resolve_primary_key() is None


class TestDatabaseSinkRegistry:
    """Test registry integration."""

    def test_database_in_registry(self):
        """Test that 'database' is registered in SINK_REGISTRY."""
        from pwetl.core.registry import SINK_REGISTRY
        from pwetl.sinks.database import DatabaseSink

        assert 'database' in SINK_REGISTRY
        assert SINK_REGISTRY['database'] is DatabaseSink

    def test_old_types_removed(self):
        """Test that 'postgresql' and 'mysql' are no longer in SINK_REGISTRY."""
        from pwetl.core.registry import SINK_REGISTRY

        assert 'postgresql' not in SINK_REGISTRY
        assert 'mysql' not in SINK_REGISTRY


class TestDatabaseSinkSetupTeardown:
    """Test setup and teardown lifecycle."""

    def test_setup_creates_engine_and_dialect(self):
        """Test that setup creates engine and initializes dialect."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })

        with patch('sqlalchemy.create_engine') as mock_create:
            mock_engine = MagicMock()
            mock_engine.dialect.name = 'sqlite'
            mock_create.return_value = mock_engine

            # Mock table_exists to return True (table already exists)
            with patch.object(
                type(sink), '_resolve_primary_key', return_value=None
            ):
                with patch(
                    'pwetl.sinks.dialect.DefaultDialect.table_exists',
                    return_value=True,
                ):
                    sink.setup()

            mock_create.assert_called_once_with('sqlite://')
            assert sink._engine is mock_engine
            assert sink._dialect is not None

    def test_teardown_disposes_engine(self):
        """Test that teardown disposes engine."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })
        mock_engine = MagicMock()
        sink._engine = mock_engine
        sink._dialect = MagicMock()

        sink.teardown()

        mock_engine.dispose.assert_called_once()
        assert sink._engine is None

    def test_teardown_stops_tunnel(self):
        """Test that teardown stops SSH tunnel."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })
        mock_tunnel = MagicMock()
        sink._tunnel = mock_tunnel
        sink._dialect = MagicMock()

        sink.teardown()

        mock_tunnel.stop.assert_called_once()
        assert sink._tunnel is None

    def test_setup_runs_init_sql(self, tmp_path):
        """Test that setup executes init_sql file."""
        from pwetl.sinks.database import DatabaseSink

        sql_file = tmp_path / 'init.sql'
        sql_file.write_text('CREATE TABLE test_table (id INT PRIMARY KEY);')

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'test_table',
            'init_sql': str(sql_file),
        })

        with patch('sqlalchemy.create_engine') as mock_create:
            mock_engine = MagicMock()
            mock_engine.dialect.name = 'sqlite'
            mock_conn = MagicMock()
            mock_engine.begin.return_value.__enter__ = lambda s: mock_conn
            mock_engine.begin.return_value.__exit__ = MagicMock(
                return_value=False
            )
            mock_create.return_value = mock_engine

            sink.setup()

            # Verify SQL was executed
            mock_conn.execute.assert_called_once()

    def test_setup_init_sql_not_found_raises(self):
        """Test that missing init_sql file raises ValueError."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'test_table',
            'init_sql': '/nonexistent/init.sql',
        })

        with patch('sqlalchemy.create_engine') as mock_create:
            mock_engine = MagicMock()
            mock_engine.dialect.name = 'sqlite'
            mock_create.return_value = mock_engine

            with pytest.raises(ValueError, match="init_sql"):
                sink.setup()


class TestDatabaseSinkWrite:
    """Test write and teardown data flow."""

    def test_write_creates_temp_file(self):
        """Test that write() creates a temp file path."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })

        mock_table = MagicMock()

        with patch('pathway.io.jsonlines.write') as mock_write:
            sink.write(mock_table)

            assert sink._temp_path is not None
            assert sink._temp_path.endswith('.jsonl')
            mock_write.assert_called_once_with(mock_table, sink._temp_path)

        # Cleanup
        if sink._temp_path and os.path.exists(sink._temp_path):
            os.remove(sink._temp_path)

    def test_teardown_calls_dialect_insert(self, tmp_path):
        """Test that teardown calls dialect.insert() with cleaned records."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })

        # Create a temp JSONL file with Pathway-style records
        temp_file = tmp_path / 'output.jsonl'
        records = [
            {'id': 1, 'name': 'Alice', 'diff': 1, 'time': 1000},
            {'id': 2, 'name': 'Bob', 'diff': 1, 'time': 1000},
        ]
        with open(temp_file, 'w') as f:
            for r in records:
                f.write(json.dumps(r) + '\n')

        sink._temp_path = str(temp_file)
        sink._engine = MagicMock()
        mock_dialect = MagicMock()
        mock_dialect.insert.return_value = 2
        sink._dialect = mock_dialect

        sink.teardown()

        # Verify dialect.insert was called with cleaned records
        mock_dialect.insert.assert_called_once()
        inserted = mock_dialect.insert.call_args[0][0]
        assert len(inserted) == 2
        assert inserted[0] == {'id': 1, 'name': 'Alice'}
        assert inserted[1] == {'id': 2, 'name': 'Bob'}

    def test_teardown_filters_pathway_metadata(self, tmp_path):
        """Test that diff and time columns are removed from records."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })

        temp_file = tmp_path / 'output.jsonl'
        records = [
            {'id': 1, 'value': 'x', 'diff': 1, 'time': 9999},
        ]
        with open(temp_file, 'w') as f:
            for r in records:
                f.write(json.dumps(r) + '\n')

        sink._temp_path = str(temp_file)
        sink._engine = MagicMock()
        mock_dialect = MagicMock()
        mock_dialect.insert.return_value = 1
        sink._dialect = mock_dialect

        sink.teardown()

        inserted = mock_dialect.insert.call_args[0][0]
        assert 'diff' not in inserted[0]
        assert 'time' not in inserted[0]
        assert inserted[0] == {'id': 1, 'value': 'x'}

    def test_teardown_only_inserts_diff_1(self, tmp_path):
        """Test that only records with diff==1 are inserted."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })

        temp_file = tmp_path / 'output.jsonl'
        records = [
            {'id': 1, 'name': 'Alice', 'diff': 1, 'time': 1000},
            {'id': 2, 'name': 'Bob', 'diff': -1, 'time': 1000},  # DELETE
            {'id': 3, 'name': 'Charlie', 'diff': 1, 'time': 1000},
        ]
        with open(temp_file, 'w') as f:
            for r in records:
                f.write(json.dumps(r) + '\n')

        sink._temp_path = str(temp_file)
        sink._engine = MagicMock()
        mock_dialect = MagicMock()
        mock_dialect.insert.return_value = 2
        sink._dialect = mock_dialect

        sink.teardown()

        inserted = mock_dialect.insert.call_args[0][0]
        assert len(inserted) == 2
        assert inserted[0] == {'id': 1, 'name': 'Alice'}
        assert inserted[1] == {'id': 3, 'name': 'Charlie'}

    def test_teardown_restores_pw_prefix(self, tmp_path):
        """Test that _pw_ prefixed columns are restored."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })

        temp_file = tmp_path / 'output.jsonl'
        records = [
            {'_pw_id': 1, '_pw_time': '2024-01-01', 'name': 'Alice',
             'diff': 1, 'time': 1000},
        ]
        with open(temp_file, 'w') as f:
            for r in records:
                f.write(json.dumps(r) + '\n')

        sink._temp_path = str(temp_file)
        sink._engine = MagicMock()
        mock_dialect = MagicMock()
        mock_dialect.insert.return_value = 1
        sink._dialect = mock_dialect

        sink.teardown()

        inserted = mock_dialect.insert.call_args[0][0]
        assert 'id' in inserted[0]
        assert inserted[0]['id'] == 1
        assert 'time' in inserted[0]
        assert inserted[0]['time'] == '2024-01-01'
        assert inserted[0]['name'] == 'Alice'
        assert '_pw_id' not in inserted[0]
        assert '_pw_time' not in inserted[0]

    def test_teardown_upsert_calls_dialect_upsert(self, tmp_path):
        """Test that upsert write_mode calls dialect.upsert()."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
            'write_mode': 'upsert',
            'primary_key': ['id'],
        })

        temp_file = tmp_path / 'output.jsonl'
        records = [
            {'id': 1, 'name': 'Alice', 'diff': 1, 'time': 1000},
        ]
        with open(temp_file, 'w') as f:
            for r in records:
                f.write(json.dumps(r) + '\n')

        sink._temp_path = str(temp_file)
        sink._engine = MagicMock()
        mock_dialect = MagicMock()
        mock_dialect.upsert.return_value = 1
        sink._dialect = mock_dialect

        sink.teardown()

        mock_dialect.upsert.assert_called_once()
        args = mock_dialect.upsert.call_args[0]
        assert args[0] == [{'id': 1, 'name': 'Alice'}]
        assert args[1] == ['id']

    def test_teardown_no_records_skips_write(self, tmp_path):
        """Test that empty JSONL skips dialect calls."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })

        temp_file = tmp_path / 'output.jsonl'
        temp_file.write_text('')

        sink._temp_path = str(temp_file)
        sink._engine = MagicMock()
        mock_dialect = MagicMock()
        sink._dialect = mock_dialect

        sink.teardown()

        mock_dialect.insert.assert_not_called()
        mock_dialect.upsert.assert_not_called()
