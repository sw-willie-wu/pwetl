"""Database data sources."""
from typing import Any, Dict, Optional, Type
import pathway as pw
from pwetl.sources.base import BaseSource
from pwetl.utils.schema import SchemaParser


class DatabaseSource(BaseSource):
    """Database data source.

    Supports PostgreSQL and MySQL.
    """

    required_config = ['db_type', 'host', 'database', 'table']
    optional_config = {
        'port': None,       # Default port determined by db_type
        'user': None,       # Username
        'password': None,   # Password
        'query': None,      # Custom SQL query (takes precedence over table)
        'schema': None,     # Optional schema
    }

    # Supported database types and their default ports
    DB_DEFAULTS = {
        'postgresql': 5432,
        'mysql': 3306,
    }

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize database Source."""
        super().__init__(name, config)

        # Set default port
        if self.config.get('port') is None:
            db_type = self.config['db_type']
            if db_type in self.DB_DEFAULTS:
                self.config['port'] = self.DB_DEFAULTS[db_type]
            else:
                raise ValueError(
                    f"Unsupported database type: '{db_type}'\n"
                    f"Supported types: {', '.join(self.DB_DEFAULTS.keys())}"
                )

    def read(self) -> pw.Table:
        """Read data from database.

        Returns:
            pw.Table: Pathway Table containing the data

        Raises:
            ValueError: When database type is not supported
        """
        db_type = self.config['db_type']

        if db_type == 'postgresql':
            return self._read_postgresql()
        if db_type == 'mysql':
            return self._read_mysql()
        raise ValueError(
            f"Unsupported database type: '{db_type}'\n"
            f"Supported types: {', '.join(self.DB_DEFAULTS.keys())}"
        )

    def _read_postgresql(self) -> pw.Table:
        """Read data from PostgreSQL."""
        # Build connection string
        conn_str = self._build_postgres_conn_str()

        # Get query
        query = self._get_query()

        # Parse schema
        schema = self._get_schema()

        # Read data
        if schema:
            return pw.io.postgres.read(
                conn_str,
                query=query,
                schema=schema,
            )
        return pw.io.postgres.read(
            conn_str,
            query=query,
        )

    def _read_mysql(self) -> pw.Table:
        """Read data from MySQL."""
        # MySQL requires connector
        try:
            import mysql.connector  # pylint: disable=unused-import
        except ImportError as exc:
            raise ImportError(
                "MySQL support requires additional package:\n"
                "pip install 'pwetl[mysql]' or pip install mysql-connector-python"
            ) from exc

        # Build connection configuration
        conn_config = {
            'host': self.config['host'],
            'port': self.config['port'],
            'database': self.config['database'],
            'user': self.config.get('user'),
            'password': self.config.get('password'),
        }

        # Get query
        query = self._get_query()

        # Create connection
        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor(dictionary=True)

        try:
            # Execute query
            cursor.execute(query)
            data = cursor.fetchall()

            # Apply validation automatically (framework handles it)
            validated_data = self._validate_batch(data)

            # Convert to Pathway Table (via JSONL)
            return self._data_to_table(validated_data)

        finally:
            cursor.close()
            conn.close()

    def _build_postgres_conn_str(self) -> str:
        """Build PostgreSQL connection string."""
        user = self.config.get('user', 'postgres')
        password = self.config.get('password', '')
        host = self.config['host']
        port = self.config['port']
        database = self.config['database']

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    def _get_query(self) -> str:
        """Get SQL query.

        Returns:
            SQL query string
        """
        # Prioritize custom query
        query = self.config.get('query')
        if query:
            return query

        # Otherwise use simple SELECT * FROM table
        table = self.config['table']
        return f"SELECT * FROM {table}"

    def _get_schema(self) -> Optional[Type[pw.Schema]]:
        """Get schema.

        Returns:
            Pathway Schema class, or None if not specified
        """
        schema_config = self.config.get('schema')
        if schema_config:
            return SchemaParser.parse(schema_config)
        return None

    def _data_to_table(self, data: list) -> pw.Table:
        """Convert data to Pathway Table."""
        import tempfile
        import json
        import os

        # Create temporary file
        fd, temp_path = tempfile.mkstemp(suffix='.jsonl', text=True)

        try:
            # Write data
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')

            # Parse schema
            schema = self._get_schema()

            # Read as Pathway Table
            if schema:
                table = pw.io.jsonlines.read(temp_path, schema=schema, mode='static')
            else:
                table = pw.io.jsonlines.read(temp_path, mode='static')

            return table

        finally:
            pass
