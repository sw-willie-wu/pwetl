"""Tests for DatabaseSink."""

import json
import os
import sys
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
        """Test that if_not_exists defaults to 'error'."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })
        assert sink.config['if_not_exists'] == 'error'
        assert sink.config['ssh_tunnel'] is None


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

    def test_setup_creates_engine(self):
        """Test that setup creates a SQLAlchemy engine."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })

        with patch('sqlalchemy.create_engine') as mock_create, \
             patch('sqlalchemy.inspect') as mock_inspect:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine
            mock_inspector = MagicMock()
            mock_inspector.has_table.return_value = True
            mock_inspect.return_value = mock_inspector

            sink.setup()

            mock_create.assert_called_once_with('sqlite://')
            assert sink._engine is mock_engine

    def test_teardown_disposes_engine(self):
        """Test that teardown disposes engine."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink('test', {
            'dsn': 'sqlite://',
            'table': 'output_table',
        })
        mock_engine = MagicMock()
        sink._engine = mock_engine

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

        sink.teardown()

        mock_tunnel.stop.assert_called_once()
        assert sink._tunnel is None


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

    def test_teardown_inserts_data(self, tmp_path):
        """Test that teardown reads JSONL and executes INSERT."""
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

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        sink._engine = mock_engine

        sink.teardown()

        # Verify INSERT was called
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        # Second arg is the list of cleaned records
        inserted_data = call_args[0][1]
        assert len(inserted_data) == 2
        assert inserted_data[0] == {'id': 1, 'name': 'Alice'}
        assert inserted_data[1] == {'id': 2, 'name': 'Bob'}
        mock_conn.commit.assert_called_once()

    def test_teardown_filters_pathway_metadata(self, tmp_path):
        """Test that diff and time columns are removed from inserted data."""
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

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        sink._engine = mock_engine

        sink.teardown()

        call_args = mock_conn.execute.call_args
        inserted_data = call_args[0][1]
        assert 'diff' not in inserted_data[0]
        assert 'time' not in inserted_data[0]
        assert inserted_data[0] == {'id': 1, 'value': 'x'}

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

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        sink._engine = mock_engine

        sink.teardown()

        call_args = mock_conn.execute.call_args
        inserted_data = call_args[0][1]
        assert len(inserted_data) == 2
        assert inserted_data[0] == {'id': 1, 'name': 'Alice'}
        assert inserted_data[1] == {'id': 3, 'name': 'Charlie'}
