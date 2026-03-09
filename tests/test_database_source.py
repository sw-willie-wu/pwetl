"""Tests for DatabaseSource."""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock, mock_open

from pwetl.sources.connector import HashDiffConnectorMixin


class TestDatabaseSourceConfig:
    """Test configuration validation."""

    def test_missing_dsn_raises(self):
        """Test that missing dsn raises ValueError."""
        from pwetl.sources.database import DatabaseSource

        with pytest.raises(ValueError, match="dsn"):
            DatabaseSource('test', {'table': 'my_table'})

    def test_missing_query_sql_and_table_raises(self):
        """Test that missing both query_sql and table raises ValueError."""
        from pwetl.sources.database import DatabaseSource

        with pytest.raises(ValueError, match="query_sql.*table"):
            DatabaseSource('test', {'dsn': 'sqlite://'})

    def test_query_sql_config(self):
        """Test valid config with query_sql."""
        from pwetl.sources.database import DatabaseSource

        source = DatabaseSource('test', {
            'dsn': 'sqlite://',
            'query_sql': 'query.sql',
        })
        assert source.config['dsn'] == 'sqlite://'
        assert source.config['query_sql'] == 'query.sql'

    def test_table_config(self):
        """Test valid config with table."""
        from pwetl.sources.database import DatabaseSource

        source = DatabaseSource('test', {
            'dsn': 'sqlite://',
            'table': 'my_table',
        })
        assert source.config['table'] == 'my_table'

    def test_default_values(self):
        """Test that optional config gets default values."""
        from pwetl.sources.database import DatabaseSource

        source = DatabaseSource('test', {
            'dsn': 'sqlite://',
            'table': 'my_table',
        })
        assert source.config['mode'] == 'static'
        assert source.config['refresh_interval'] == 60
        assert source.config['validation_mode'] == 'sample'
        assert source.config['ssh_tunnel'] is None
        assert source.config['schema'] is None

    def test_query_file_backwards_compat(self, caplog):
        """Test that query_file is accepted with deprecation warning."""
        import logging
        from pwetl.sources.database import DatabaseSource

        with caplog.at_level(logging.WARNING):
            source = DatabaseSource('test', {
                'dsn': 'sqlite://',
                'query_file': 'legacy.sql',
            })

        # query_file should be migrated to query_sql
        assert source.config['query_sql'] == 'legacy.sql'
        assert 'query_file' not in source.config
        # Should have logged a deprecation warning
        assert any('deprecated' in r.message.lower() for r in caplog.records)

    def test_query_file_does_not_override_query_sql(self):
        """Test that query_file does not override existing query_sql."""
        from pwetl.sources.database import DatabaseSource

        source = DatabaseSource('test', {
            'dsn': 'sqlite://',
            'query_sql': 'new.sql',
            'query_file': 'legacy.sql',
        })
        # query_sql takes precedence, query_file is ignored
        assert source.config['query_sql'] == 'new.sql'


class TestDatabaseSourceRegistry:
    """Test registry integration."""

    def test_database_in_registry(self):
        """Test that 'database' is registered in SOURCE_REGISTRY."""
        from pwetl.core.registry import SOURCE_REGISTRY
        from pwetl.sources.database import DatabaseSource

        assert 'database' in SOURCE_REGISTRY
        assert SOURCE_REGISTRY['database'] is DatabaseSource

    def test_old_types_removed(self):
        """Test that old postgresql/mysql types are removed."""
        from pwetl.core.registry import SOURCE_REGISTRY

        assert 'postgresql' not in SOURCE_REGISTRY
        assert 'mysql' not in SOURCE_REGISTRY

    def test_import_from_pwetl(self):
        """Test that DatabaseSource can be imported from pwetl."""
        from pwetl import DatabaseSource
        assert DatabaseSource is not None


class TestDatabaseSourceGetQuery:
    """Test _get_query logic."""

    def test_query_from_file(self, tmp_path):
        """Test reading query from a .sql file."""
        from pwetl.sources.database import DatabaseSource

        sql_file = tmp_path / 'test.sql'
        sql_file.write_text('SELECT id, name FROM users WHERE active = 1')

        source = DatabaseSource('test', {
            'dsn': 'sqlite://',
            'query_sql': str(sql_file),
        })
        assert source._get_query() == 'SELECT id, name FROM users WHERE active = 1'

    def test_query_sql_not_found(self):
        """Test that missing query_sql raises ValueError."""
        from pwetl.sources.database import DatabaseSource

        source = DatabaseSource('test', {
            'dsn': 'sqlite://',
            'query_sql': '/nonexistent/query.sql',
        })
        with pytest.raises(ValueError, match="not found"):
            source._get_query()

    def test_query_sql_precedence_over_table(self, tmp_path):
        """Test that query_sql takes precedence over table."""
        from pwetl.sources.database import DatabaseSource

        sql_file = tmp_path / 'test.sql'
        sql_file.write_text('SELECT custom FROM custom_query')

        source = DatabaseSource('test', {
            'dsn': 'sqlite://',
            'query_sql': str(sql_file),
            'table': 'ignored_table',
        })
        assert source._get_query() == 'SELECT custom FROM custom_query'

    def test_table_with_schema_generates_select(self):
        """Test that table + schema generates SELECT with column names."""
        from pwetl.sources.database import DatabaseSource

        source = DatabaseSource('test', {
            'dsn': 'sqlite://',
            'table': 'users',
            'schema': {'id': 'int', 'name': 'str', 'email': 'str'},
        })
        query = source._get_query()
        assert query == 'SELECT id, name, email FROM users'

    def test_table_without_schema_generates_select_star(self):
        """Test that table without schema generates SELECT *."""
        from pwetl.sources.database import DatabaseSource

        source = DatabaseSource('test', {
            'dsn': 'sqlite://',
            'table': 'users',
        })
        assert source._get_query() == 'SELECT * FROM users'


class TestDatabaseSourceSetupTeardown:
    """Test setup and teardown."""

    @patch('pwetl.sources.database.DatabaseSource._get_query', return_value='SELECT 1')
    def test_setup_creates_engine(self, mock_query):
        """Test that setup creates SQLAlchemy engine."""
        from pwetl.sources.database import DatabaseSource

        source = DatabaseSource('test', {
            'dsn': 'sqlite://',
            'table': 'my_table',
        })

        with patch('sqlalchemy.create_engine') as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            source.setup()

            mock_create.assert_called_once_with('sqlite://')
            assert source._engine is mock_engine

    def test_teardown_disposes_engine(self):
        """Test that teardown disposes engine."""
        from pwetl.sources.database import DatabaseSource

        source = DatabaseSource('test', {
            'dsn': 'sqlite://',
            'table': 'my_table',
        })
        mock_engine = MagicMock()
        source._engine = mock_engine

        source.teardown()

        mock_engine.dispose.assert_called_once()
        assert source._engine is None

    def test_teardown_stops_tunnel(self):
        """Test that teardown stops SSH tunnel."""
        from pwetl.sources.database import DatabaseSource

        source = DatabaseSource('test', {
            'dsn': 'sqlite://',
            'table': 'my_table',
        })
        mock_tunnel = MagicMock()
        source._tunnel = mock_tunnel

        source.teardown()

        mock_tunnel.stop.assert_called_once()
        assert source._tunnel is None

    def test_read_without_setup_raises(self):
        """Test that read() without setup() raises RuntimeError."""
        from pwetl.sources.database import DatabaseSource

        source = DatabaseSource('test', {
            'dsn': 'sqlite://',
            'table': 'my_table',
        })
        with pytest.raises(RuntimeError, match="setup"):
            source.read()


class TestDatabaseSourceSSHTunnel:
    """Test SSH tunnel setup."""

    def test_setup_ssh_tunnel_rewrites_dsn(self):
        """Test that SSH tunnel rewrites DSN to localhost."""
        import sys
        from pwetl.sources.database import DatabaseSource

        # Create a fake sshtunnel module so the import inside _setup_ssh_tunnel works
        mock_sshtunnel = MagicMock()
        mock_tunnel_instance = MagicMock()
        mock_tunnel_instance.local_bind_port = 12345
        mock_sshtunnel.SSHTunnelForwarder.return_value = mock_tunnel_instance
        sys.modules['sshtunnel'] = mock_sshtunnel

        try:
            source = DatabaseSource('test', {
                'dsn': 'mssql+pyodbc://user:pass@db-host:1433/mydb',
                'table': 'my_table',
            })

            rewritten = source._setup_ssh_tunnel(
                'mssql+pyodbc://user:pass@db-host:1433/mydb',
                {
                    'host': 'jump-server',
                    'username': 'ssh_user',
                    'password': 'ssh_pass',
                },
            )

            assert '127.0.0.1' in rewritten
            assert '12345' in rewritten
            mock_tunnel_instance.start.assert_called_once()
        finally:
            del sys.modules['sshtunnel']


class TestDatabaseConnectorSubject:
    """Test DatabaseConnectorSubject."""

    def test_static_mode_runs_once(self):
        """Test that static mode executes query once and stops."""
        from pwetl.sources.connector import DatabaseConnectorSubject

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ['id', 'name']
        mock_result.fetchall.return_value = [(1, 'Alice')]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        records = []

        connector = DatabaseConnectorSubject(
            engine=mock_engine,
            query='SELECT id, name FROM users',
            refresh_interval=10,
            mode='static',
        )
        # Override next to capture records
        connector.next = lambda **kwargs: records.append(kwargs)

        connector.run()

        assert len(records) == 1
        assert records[0] == {'id': 1, 'name': 'Alice'}


class _FakeConnector(HashDiffConnectorMixin):
    """Minimal fake connector for testing the mixin without Pathway."""

    def __init__(self, diff_ignore_fields=None):
        self.__init_hash_diff__(diff_ignore_fields=diff_ignore_fields)
        self.emitted = []

    def next(self, **kwargs):
        self.emitted.append(kwargs)


class TestHashDiffDeduplication:
    """Test HashDiffConnectorMixin deduplication logic."""

    def test_first_poll_emits_all(self):
        """First poll should emit every record."""
        conn = _FakeConnector()
        data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

        emitted = conn._emit_diff(data, None)

        assert emitted == 2
        assert len(conn.emitted) == 2

    def test_duplicate_records_not_re_emitted(self):
        """Second poll with identical data should emit nothing."""
        conn = _FakeConnector()
        data = [{"id": 1, "name": "Alice"}]

        conn._emit_diff(data, None)
        conn.emitted.clear()

        emitted = conn._emit_diff(data, None)

        assert emitted == 0
        assert len(conn.emitted) == 0

    def test_new_record_emitted_on_change(self):
        """Adding a new record should emit only the new one."""
        conn = _FakeConnector()
        data1 = [{"id": 1, "name": "Alice"}]
        data2 = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

        conn._emit_diff(data1, None)
        conn.emitted.clear()

        emitted = conn._emit_diff(data2, None)

        assert emitted == 1
        assert conn.emitted == [{"id": 2, "name": "Bob"}]

    def test_changed_record_emitted(self):
        """A record with changed content should be re-emitted."""
        conn = _FakeConnector()
        data1 = [{"id": 1, "name": "Alice"}]
        data2 = [{"id": 1, "name": "Alice Updated"}]

        conn._emit_diff(data1, None)
        conn.emitted.clear()

        emitted = conn._emit_diff(data2, None)

        assert emitted == 1
        assert conn.emitted == [{"id": 1, "name": "Alice Updated"}]

    def test_disappeared_then_reappeared_record(self):
        """A record that disappears and reappears should be re-emitted."""
        conn = _FakeConnector()
        data_full = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        data_partial = [{"id": 1, "name": "Alice"}]

        conn._emit_diff(data_full, None)
        conn.emitted.clear()

        # Bob disappears
        conn._emit_diff(data_partial, None)
        conn.emitted.clear()

        # Bob reappears
        emitted = conn._emit_diff(data_full, None)

        assert emitted == 1
        assert conn.emitted == [{"id": 2, "name": "Bob"}]

    def test_validation_fn_applied(self):
        """validate_fn should transform records before emitting."""
        conn = _FakeConnector()
        data = [{"id": 1, "name": "alice"}]

        def upper_name(record):
            return {**record, "name": record["name"].upper()}

        emitted = conn._emit_diff(data, upper_name)

        assert emitted == 1
        assert conn.emitted == [{"id": 1, "name": "ALICE"}]

    def test_validation_fn_returning_none_skips(self):
        """validate_fn returning None should skip that record."""
        conn = _FakeConnector()
        data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "skip"}]

        def filter_fn(record):
            if record["name"] == "skip":
                return None
            return record

        emitted = conn._emit_diff(data, filter_fn)

        assert emitted == 1
        assert conn.emitted == [{"id": 1, "name": "Alice"}]

    def test_record_hash_deterministic(self):
        """Same record should always produce the same hash."""
        conn = _FakeConnector()
        record = {"id": 1, "name": "Alice", "age": 30}

        h1 = conn._record_hash(record)
        h2 = conn._record_hash(record)

        assert h1 == h2

    def test_record_hash_key_order_independent(self):
        """Dict key order should not affect the hash."""
        conn = _FakeConnector()
        r1 = {"name": "Alice", "id": 1}
        r2 = {"id": 1, "name": "Alice"}

        assert conn._record_hash(r1) == conn._record_hash(r2)

    def test_record_hash_handles_non_json_types(self):
        """datetime and Decimal values should be handled via default=str."""
        conn = _FakeConnector()
        record = {
            "ts": datetime(2024, 1, 15, 10, 30, 0),
            "amount": Decimal("123.45"),
        }

        h = conn._record_hash(record)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest length

    def test_diff_ignore_fields_excludes_volatile_fields(self):
        """Records differing only in ignored fields should not be re-emitted."""
        conn = _FakeConnector(diff_ignore_fields=["mday", "srcUpdateTime"])
        data1 = [{"sno": "001", "sbi": 5, "mday": "2026-02-10 14:00:00", "srcUpdateTime": "t1"}]
        data2 = [{"sno": "001", "sbi": 5, "mday": "2026-02-10 14:01:00", "srcUpdateTime": "t2"}]

        conn._emit_diff(data1, None)
        conn.emitted.clear()

        emitted = conn._emit_diff(data2, None)

        assert emitted == 0
        assert len(conn.emitted) == 0

    def test_diff_ignore_fields_still_detects_real_changes(self):
        """Changes in non-ignored fields should still trigger re-emit."""
        conn = _FakeConnector(diff_ignore_fields=["mday"])
        data1 = [{"sno": "001", "sbi": 5, "mday": "2026-02-10 14:00:00"}]
        data2 = [{"sno": "001", "sbi": 3, "mday": "2026-02-10 14:01:00"}]

        conn._emit_diff(data1, None)
        conn.emitted.clear()

        emitted = conn._emit_diff(data2, None)

        assert emitted == 1
        assert conn.emitted[0]["sbi"] == 3

    def test_diff_ignore_fields_emits_full_record(self):
        """Even with ignore_fields, self.next() receives the FULL record."""
        conn = _FakeConnector(diff_ignore_fields=["mday"])
        data = [{"sno": "001", "sbi": 5, "mday": "2026-02-10 14:00:00"}]

        conn._emit_diff(data, None)

        assert "mday" in conn.emitted[0]
        assert conn.emitted[0]["mday"] == "2026-02-10 14:00:00"
