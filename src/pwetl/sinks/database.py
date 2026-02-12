"""Database data sink using SQLAlchemy DSN with dialect strategy."""

import json
import os
import tempfile
from typing import Any, Dict

import pathway as pw
from pwetl.sinks.base import BaseSink
from pwetl.sinks.dialect import get_dialect, parse_column_def
from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)


class DatabaseSink(BaseSink):
    """Database output via SQLAlchemy DSN with dialect-based strategy.

    Supports any SQLAlchemy-compatible database (PostgreSQL, MySQL, MSSQL, etc.).
    Dialect is auto-detected from DSN or manually specified.

    Table creation:
    - columns: simple CREATE TABLE (type + pk)
    - init_sql: advanced DDL from SQL file (CREATE TABLE + INDEX + TRIGGER)
    - columns and init_sql are mutually exclusive

    Write modes:
    - insert: bulk INSERT (default)
    - upsert: INSERT ON CONFLICT DO UPDATE (dialect-specific)

    Uses a temp JSONL strategy:
    - write()    → pw.io.jsonlines.write(table, temp_path)
    - pw.run()   → Pathway engine writes data to temp JSONL
    - teardown() → read JSONL → dialect insert/upsert → cleanup
    """

    required_config = ['dsn', 'table']
    optional_config = {
        'write_mode': 'insert',
        'primary_key': None,
        'columns': None,
        'init_sql': None,
        'dialect': None,
        'ssh_tunnel': None,
    }

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize DatabaseSink."""
        super().__init__(name, config)
        self._engine = None
        self._tunnel = None
        self._temp_path = None
        self._dialect = None

    def _validate_config(self) -> None:
        """Validate sink-specific configuration."""
        super()._validate_config()

        write_mode = self.config.get('write_mode', 'insert')
        if write_mode not in ('insert', 'upsert'):
            raise ValueError(
                f"Sink '{self.name}': write_mode must be 'insert' or 'upsert', "
                f"got '{write_mode}'"
            )

        if write_mode == 'upsert':
            pk = self._resolve_primary_key()
            if not pk:
                raise ValueError(
                    f"Sink '{self.name}': write_mode 'upsert' requires "
                    "'primary_key' config or 'pk' modifier in columns"
                )

        columns = self.config.get('columns')
        init_sql = self.config.get('init_sql')
        if columns and init_sql:
            raise ValueError(
                f"Sink '{self.name}': 'columns' and 'init_sql' are mutually exclusive"
            )

    def _resolve_primary_key(self) -> list[str] | None:
        """Resolve primary key from config or columns pk modifier."""
        if self.config.get('primary_key'):
            return self.config['primary_key']

        columns = self.config.get('columns')
        if columns:
            pks = [
                name for name, def_str in columns.items()
                if 'pk' in [p.strip().lower() for p in def_str.split(',')[1:]]
            ]
            return pks or None

        return None

    def setup(self) -> None:
        """Initialize SSH tunnel, engine, dialect, and table."""
        dsn = self.config['dsn']

        # Setup SSH tunnel if configured
        ssh_config = self.config.get('ssh_tunnel')
        if ssh_config:
            dsn = self._setup_ssh_tunnel(dsn, ssh_config)

        try:
            from sqlalchemy import create_engine
        except ImportError as exc:
            raise ImportError(
                "Database sink requires SQLAlchemy:\n"
                "pip install 'pwetl[database]' or pip install 'sqlalchemy>=2.0.0'"
            ) from exc

        self._engine = create_engine(dsn)

        # Detect dialect
        dialect_name = (
            self.config.get('dialect') or self._engine.dialect.name
        )
        dialect_cls = get_dialect(dialect_name)
        table_name = self.config['table']
        self._dialect = dialect_cls(self._engine, table_name)
        LOGGER.info(
            "Sink '%s': engine created (dialect: %s)",
            self.name, dialect_name,
        )

        # Table creation
        columns = self.config.get('columns')
        init_sql = self.config.get('init_sql')

        if columns:
            self._dialect.ensure_table(columns)
        elif init_sql:
            self._run_init_sql()
        elif not self._dialect.table_exists():
            raise ValueError(
                f"Sink '{self.name}': table '{table_name}' does not exist. "
                "Provide 'columns' or 'init_sql' to create it."
            )

    def _run_init_sql(self) -> None:
        """Execute init SQL file for table setup."""
        from sqlalchemy import text

        sql_path = self.config['init_sql']
        try:
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql = f.read()
        except FileNotFoundError as exc:
            raise ValueError(
                f"Sink '{self.name}': init_sql '{sql_path}' not found."
            ) from exc

        with self._engine.begin() as conn:
            conn.execute(text(sql))

        LOGGER.info(
            "Sink '%s': executed init SQL from '%s'", self.name, sql_path
        )

    def write(self, table: pw.Table) -> None:
        """Schedule Pathway output to a temporary JSONL file."""
        fd, temp_path = tempfile.mkstemp(suffix='.jsonl', text=True)
        os.close(fd)

        try:
            pw.io.jsonlines.write(table, temp_path)
            self._temp_path = temp_path
            LOGGER.info("Sink '%s': scheduled output to temp JSONL", self.name)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def teardown(self) -> None:
        """Read temp JSONL, execute write via dialect, then cleanup."""
        try:
            self._execute_write()
        finally:
            # Cleanup temp file
            if self._temp_path and os.path.exists(self._temp_path):
                os.remove(self._temp_path)

            # Dispose engine
            if self._engine is not None:
                self._engine.dispose()
                self._engine = None

            # Stop SSH tunnel
            if self._tunnel is not None:
                self._tunnel.stop()
                self._tunnel = None

    def _read_and_clean_records(self) -> list[dict]:
        """Read temp JSONL and clean records.

        1. Read all lines from temp JSONL
        2. Filter: only diff == 1 (Pathway INSERT)
        3. Remove Pathway metadata (diff, time)
        4. Restore _pw_ prefixed columns
        """
        if not self._temp_path or not os.path.exists(self._temp_path):
            return []

        records = []
        with open(self._temp_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)

                # Only keep diff == 1 (INSERT)
                diff = record.pop('diff', 1)
                record.pop('time', None)

                # Restore columns prefixed with _pw_ (Pathway collision avoidance)
                for key in list(record.keys()):
                    if key.startswith('_pw_'):
                        record[key[4:]] = record.pop(key)

                if diff == 1:
                    records.append(record)

        return records

    def _execute_write(self) -> None:
        """Read cleaned records and write via dialect."""
        if self._engine is None:
            LOGGER.warning("Sink '%s': no engine available", self.name)
            return

        records = self._read_and_clean_records()

        if not records:
            LOGGER.info("Sink '%s': no records to write", self.name)
            return

        write_mode = self.config.get('write_mode', 'insert')
        table_name = self.config['table']

        if write_mode == 'upsert':
            pk = self._resolve_primary_key()
            count = self._dialect.upsert(records, pk)
            LOGGER.info(
                "Sink '%s': upserted %d records into '%s'",
                self.name, count, table_name,
            )
        else:
            count = self._dialect.insert(records)
            LOGGER.info(
                "Sink '%s': inserted %d records into '%s'",
                self.name, count, table_name,
            )

    def _setup_ssh_tunnel(self, dsn: str, ssh_config: Dict[str, Any]) -> str:
        """Setup SSH tunnel and rewrite DSN to use local tunnel port."""
        try:
            from sshtunnel import SSHTunnelForwarder
        except ImportError as exc:
            raise ImportError(
                "SSH tunnel requires sshtunnel:\n"
                "pip install 'pwetl[ssh]' or pip install sshtunnel"
            ) from exc

        from sqlalchemy.engine import make_url

        # Parse DB host/port from DSN
        url = make_url(dsn)
        remote_host = url.host or 'localhost'
        remote_port = url.port or 3306

        # Build SSH tunnel kwargs
        tunnel_kwargs = {
            'ssh_address_or_host': (ssh_config['host'], ssh_config.get('port', 22)),
            'ssh_username': ssh_config.get('username'),
            'remote_bind_address': (remote_host, remote_port),
            'local_bind_address': ('127.0.0.1',),
        }

        if ssh_config.get('private_key'):
            tunnel_kwargs['ssh_pkey'] = ssh_config['private_key']
        elif ssh_config.get('password'):
            tunnel_kwargs['ssh_password'] = ssh_config['password']

        self._tunnel = SSHTunnelForwarder(**tunnel_kwargs)
        self._tunnel.start()

        local_port = self._tunnel.local_bind_port
        LOGGER.info(
            "SSH tunnel established: 127.0.0.1:%d -> %s:%d (via %s)",
            local_port, remote_host, remote_port, ssh_config['host'],
        )

        # Rewrite DSN to use tunnel
        rewritten_url = url.set(host='127.0.0.1', port=local_port)
        return str(rewritten_url)
