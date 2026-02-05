"""Database data sinks."""

from typing import Any, Dict
import pathway as pw
from pwetl.sinks.base import BaseSink


class DatabaseSink(BaseSink):
    """Database output.

    Supports PostgreSQL and MySQL.
    """

    required_config = ["db_type", "host", "database", "table"]
    optional_config = {
        "port": None,  # Default port determined by db_type
        "user": None,  # Username
        "password": None,  # Password
    }

    # Supported database types and their default ports
    DB_DEFAULTS = {
        "postgresql": 5432,
        "mysql": 3306,
    }

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize database Sink."""
        super().__init__(name, config)

        # Set default port
        if self.config.get("port") is None:
            db_type = self.config["db_type"]
            if db_type in self.DB_DEFAULTS:
                self.config["port"] = self.DB_DEFAULTS[db_type]
            else:
                raise ValueError(
                    f"Unsupported database type: '{db_type}'\n"
                    f"Supported types: {', '.join(self.DB_DEFAULTS.keys())}"
                )

    def write(self, table: pw.Table) -> None:
        """Write to database.

        Args:
            table: Pathway Table to write

        Raises:
            ValueError: When database type is not supported
        """
        db_type = self.config["db_type"]

        if db_type == "postgresql":
            self._write_postgresql(table)
        elif db_type == "mysql":
            self._write_mysql(table)
        else:
            raise ValueError(
                f"Unsupported database type: '{db_type}'\n"
                f"Supported types: {', '.join(self.DB_DEFAULTS.keys())}"
            )

    def _write_postgresql(self, table: pw.Table) -> None:
        """Write to PostgreSQL."""
        # Build connection string
        conn_str = self._build_postgres_conn_str()
        table_name = self.config["table"]

        # Write data
        pw.io.postgres.write(table, conn_str, table_name)

    def _write_mysql(self, _table: pw.Table) -> None:
        """Write to MySQL."""
        # MySQL requires special handling (Pathway may not support it directly)
        try:
            import mysql.connector  # pylint: disable=unused-import
        except ImportError as exc:
            raise ImportError(
                "MySQL support requires additional package:\n"
                "pip install 'pwetl[mysql]' or pip install mysql-connector-python"
            ) from exc

        # Note: Pathway may not directly support MySQL writes
        # This provides a basic implementation and may need adjustments
        raise NotImplementedError(
            "MySQL Sink is not fully implemented yet. Please use PostgreSQL or file output."
        )

    def _build_postgres_conn_str(self) -> str:
        """Build PostgreSQL connection string."""
        user = self.config.get("user", "postgres")
        password = self.config.get("password", "")
        host = self.config["host"]
        port = self.config["port"]
        database = self.config["database"]

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
