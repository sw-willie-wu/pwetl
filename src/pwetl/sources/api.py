"""API data source."""

from typing import Any, Dict, Optional, Type
import pathway as pw
from pwetl.sources.base import BaseSource
from pwetl.sources.connector.api import APIConnectorSubject
from pwetl.utils.schema import SchemaParser
from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)


class APISource(BaseSource):
    """API data source.

    Supports reading data from REST APIs.

    Modes:
    - static: Execute once, read current data and exit
    - streaming: Poll API periodically, run continuously (requires refresh_interval)
    """

    required_config = ["url"]
    optional_config = {
        "method": "GET",  # HTTP method
        "headers": {},  # Custom headers
        "params": {},  # URL parameters
        "timeout": 30,  # Timeout in seconds
        "data_path": None,  # Data path in JSON response (e.g., 'Data')
        "schema": None,  # Optional schema
        "mode": "static",  # 'static' or 'streaming'
        "refresh_interval": 60,  # Polling interval in seconds (for streaming mode only)
        "validation_mode": "sample",  # Validation mode
        "diff_ignore_fields": None,  # Fields to exclude from dedup hash (e.g. timestamps)
    }

    def __init__(self, name: str, config: dict):
        """Initialize APISource."""
        super().__init__(name, config)
        self._connector = None

    def setup(self) -> None:
        """Initialize connector with configuration.

        Creates the APIConnectorSubject instance with all necessary parameters.
        Validation is automatically provided by the framework.
        """
        self._connector = APIConnectorSubject(
            url=self.config["url"],
            mode=self.config["mode"],
            refresh_interval=self.config["refresh_interval"],
            method=self.config.get("method", "GET"),
            headers=self.config.get("headers", {}),
            params=self.config.get("params", {}),
            timeout=self.config.get("timeout", 30),
            data_path=self.config.get("data_path"),
            validate_fn=self._validate_record,  # Framework provides validation
            diff_ignore_fields=self.config.get("diff_ignore_fields"),
        )
        LOGGER.info("Source '%s': connector initialized (mode=%s)", self.name, self.config["mode"])

    def read(self) -> pw.Table:
        """Read data from API using the connector.

        Returns:
            pw.Table: Pathway Table containing the data

        Raises:
            RuntimeError: When connector not initialized
        """
        if self._connector is None:
            raise RuntimeError(
                f"Source '{self.name}' connector not initialized. "
                "setup() must be called before read()."
            )

        LOGGER.info("Source '%s': building Pathway read graph", self.name)
        schema = self._get_schema()

        # Build Pathway computation graph using the connector
        table = pw.io.python.read(
            self._connector,
            schema=schema,
            autocommit_duration_ms=1000,
        )

        return table

    def _get_schema(self) -> Optional[Type[pw.Schema]]:
        """Get Schema.

        Returns:
            Pathway Schema class, or None if not specified
        """
        schema_config = self.config.get("schema")
        if schema_config:
            return SchemaParser.parse(schema_config)
        return None
