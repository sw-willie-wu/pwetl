"""Database data sink using SQLAlchemy DSN."""

import json
import os
import tempfile
from typing import Any, Dict

import pathway as pw
from pwetl.sinks.base import BaseSink
from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)


class DatabaseSink(BaseSink):
    """Database output via SQLAlchemy DSN.

    Supports any SQLAlchemy-compatible database (PostgreSQL, MySQL, MSSQL, etc.).

    Uses a temp JSONL strategy:
    - write()    → pw.io.jsonlines.write(table, temp_path)
    - pw.run()   → Pathway engine writes data to temp JSONL
    - teardown() → read JSONL → SQLAlchemy bulk INSERT → cleanup
    """

    required_config = ['dsn', 'table']
    optional_config = {
        'ssh_tunnel': None,
        'if_not_exists': 'error',  # 'error' or 'create'
    }

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize DatabaseSink."""
        super().__init__(name, config)
        self._engine = None
        self._tunnel = None
        self._temp_path = None

    def setup(self) -> None:
        """Initialize SSH tunnel (if configured) and SQLAlchemy engine."""
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

        # Check table existence
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(self._engine)
        table_name = self.config['table']
        if_not_exists = self.config.get('if_not_exists', 'error')

        if not inspector.has_table(table_name):
            if if_not_exists == 'create':
                LOGGER.info(
                    "Sink '%s': table '%s' does not exist, "
                    "will be auto-created on first INSERT.",
                    self.name, table_name,
                )
            else:
                raise ValueError(
                    f"Sink '{self.name}': table '{table_name}' does not exist. "
                    f"Set if_not_exists: create to auto-create."
                )

    def write(self, table: pw.Table) -> None:
        """Schedule Pathway output to a temporary JSONL file.

        Args:
            table: Pathway Table to write
        """
        fd, temp_path = tempfile.mkstemp(suffix='.jsonl', text=True)
        os.close(fd)

        try:
            pw.io.jsonlines.write(table, temp_path)
            self._temp_path = temp_path
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def teardown(self) -> None:
        """Read temp JSONL, bulk INSERT via SQLAlchemy, then cleanup."""
        try:
            self._insert_from_temp()
        finally:
            # Cleanup temp file
            if self._temp_path and os.path.exists(self._temp_path):
                os.remove(self._temp_path)
                LOGGER.info("Sink '%s': cleaned up temp file.", self.name)

            # Dispose engine
            if self._engine is not None:
                self._engine.dispose()
                self._engine = None

            # Stop SSH tunnel
            if self._tunnel is not None:
                self._tunnel.stop()
                self._tunnel = None

    def _insert_from_temp(self) -> None:
        """Read temp JSONL and bulk INSERT into the database."""
        if not self._temp_path or not os.path.exists(self._temp_path):
            LOGGER.warning("Sink '%s': no temp file to read.", self.name)
            return

        if self._engine is None:
            LOGGER.warning("Sink '%s': no engine available.", self.name)
            return

        # Read JSONL records
        records = []
        with open(self._temp_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        LOGGER.info(
            "Sink '%s': read %d records from temp file.",
            self.name, len(records),
        )

        # Filter: only diff == 1 (Pathway INSERT)
        insert_records = [r for r in records if r.get('diff') == 1]

        # Remove Pathway metadata columns
        cleaned = []
        for record in insert_records:
            row = {k: v for k, v in record.items() if k not in ('diff', 'time')}
            cleaned.append(row)

        if not cleaned:
            LOGGER.info("Sink '%s': no records to insert.", self.name)
            return

        LOGGER.info(
            "Sink '%s': inserting %d records into '%s'.",
            self.name, len(cleaned), self.config['table'],
        )

        # Bulk INSERT
        from sqlalchemy import text

        table_name = self.config['table']
        columns = list(cleaned[0].keys())
        col_str = ', '.join(columns)
        param_str = ', '.join(f':{c}' for c in columns)
        insert_sql = text(f"INSERT INTO {table_name} ({col_str}) VALUES ({param_str})")

        with self._engine.connect() as conn:
            conn.execute(insert_sql, cleaned)
            conn.commit()

        LOGGER.info("Sink '%s': INSERT complete.", self.name)

    def _setup_ssh_tunnel(self, dsn: str, ssh_config: Dict[str, Any]) -> str:
        """Setup SSH tunnel and rewrite DSN to use local tunnel port.

        Args:
            dsn: Original DSN with real DB host/port
            ssh_config: SSH tunnel configuration

        Returns:
            Rewritten DSN pointing to localhost:local_port
        """
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
