"""Database data source using SQLAlchemy + DSN."""

from typing import Any, Dict, List, Optional, Type
import pathway as pw
from pwetl.sources.base import BaseSource
from pwetl.sources.connector.database import DatabaseConnectorSubject
from pwetl.utils.schema import SchemaParser
from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)


class DatabaseSource(BaseSource):
    """Database data source via SQLAlchemy DSN.

    Supports any SQLAlchemy-compatible database (MSSQL, PostgreSQL, MySQL, Sybase, etc.).

    Query source (pick one):
    - query_file: path to a .sql file
    - table: table name (SELECT columns from schema keys, or SELECT * if no schema)

    Modes:
    - static: execute once and exit (default)
    - streaming: poll periodically
    """

    required_config = ['dsn']
    optional_config = {
        'query_file': None,
        'table': None,
        'ssh_tunnel': None,
        'schema': None,
        'mode': 'static',
        'refresh_interval': 60,
        'validation_mode': 'sample',
        'diff_ignore_fields': None,  # Fields to exclude from dedup hash (e.g. timestamps)
    }

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize DatabaseSource."""
        super().__init__(name, config)
        self._engine = None
        self._tunnel = None
        self._connector = None

        # Validate: query_file or table must be provided
        if not self.config.get('query_file') and not self.config.get('table'):
            raise ValueError(
                f"Source '{self.name}' requires either 'query_file' or 'table' "
                "in configuration."
            )

    def setup(self) -> None:
        """Initialize SSH tunnel (if configured) and SQLAlchemy engine."""
        dsn = self.config['dsn']

        # Setup SSH tunnel if configured
        ssh_config = self.config.get('ssh_tunnel')
        if ssh_config:
            dsn = self._setup_ssh_tunnel(dsn, ssh_config)

        # Lazy import sqlalchemy
        try:
            from sqlalchemy import create_engine
        except ImportError as exc:
            raise ImportError(
                "Database source requires SQLAlchemy:\n"
                "pip install 'pwetl[database]' or pip install 'sqlalchemy>=2.0.0'"
            ) from exc

        self._engine = create_engine(dsn)

        # For streaming mode, create connector
        if self.config['mode'] == 'streaming':
            query = self._get_query()
            self._connector = DatabaseConnectorSubject(
                engine=self._engine,
                query=query,
                refresh_interval=self.config['refresh_interval'],
                mode=self.config['mode'],
                validate_fn=self._validate_record,
                diff_ignore_fields=self.config.get('diff_ignore_fields'),
            )

    def read(self) -> pw.Table:
        """Read data from database.

        Returns:
            pw.Table: Pathway Table containing the data
        """
        if self._engine is None:
            raise RuntimeError(
                f"Source '{self.name}' not initialized. "
                "setup() must be called before read()."
            )

        if self.config['mode'] == 'streaming':
            return self._read_streaming()
        return self._read_static()

    def teardown(self) -> None:
        """Clean up engine and SSH tunnel."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

        if self._tunnel is not None:
            self._tunnel.stop()
            self._tunnel = None

    def _read_static(self) -> pw.Table:
        """Read data in static mode (single execution)."""
        query = self._get_query()
        data = self._execute_query(query)

        validated_data = self._validate_batch(data)

        return self._data_to_table(validated_data)

    def _read_streaming(self) -> pw.Table:
        """Read data in streaming mode (periodic polling)."""
        if self._connector is None:
            raise RuntimeError(
                f"Source '{self.name}' connector not initialized."
            )

        schema = self._get_schema()

        return pw.io.python.read(
            self._connector,
            schema=schema,
            autocommit_duration_ms=1000,
        )

    def _execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return list of dicts."""
        from sqlalchemy import text

        with self._engine.connect() as conn:
            result = conn.execute(text(query))
            columns = list(result.keys())
            return [dict(zip(columns, row)) for row in result.fetchall()]

    def _get_query(self) -> str:
        """Get SQL query from query_file or table config.

        Returns:
            SQL query string

        Raises:
            ValueError: When query_file cannot be read
        """
        # query_file takes precedence
        query_file = self.config.get('query_file')
        if query_file:
            try:
                with open(query_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except FileNotFoundError as exc:
                raise ValueError(
                    f"Source '{self.name}': query_file '{query_file}' not found."
                ) from exc

        # Build SELECT from table (+ schema keys if available)
        table = self.config['table']
        schema_config = self.config.get('schema')
        if schema_config and isinstance(schema_config, dict):
            columns = ', '.join(schema_config.keys())
            return f"SELECT {columns} FROM {table}"
        return f"SELECT * FROM {table}"

    def _get_schema(self) -> Optional[Type[pw.Schema]]:
        """Get Pathway Schema from config."""
        schema_config = self.config.get('schema')
        if schema_config:
            return SchemaParser.parse(schema_config)
        return None

    def _data_to_table(self, data: list) -> pw.Table:
        """Convert data list to Pathway Table via temp JSONL file."""
        import tempfile
        import json
        import os

        fd, temp_path = tempfile.mkstemp(suffix='.jsonl', text=True)

        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False, default=str) + '\n')

            schema = self._get_schema()

            if schema:
                return pw.io.jsonlines.read(temp_path, schema=schema, mode='static')
            return pw.io.jsonlines.read(temp_path, mode='static')

        finally:
            pass

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
