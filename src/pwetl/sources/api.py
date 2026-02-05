"""API data source."""

from typing import Any, Callable, Dict, List, Optional, Type
import time
import requests
import pathway as pw
from pwetl.sources.base import BaseSource
from pwetl.utils.schema import SchemaParser
from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)


class APIConnectorSubject(pw.io.python.ConnectorSubject):
    """Custom API polling connector."""

    def __init__(
        self,
        url: str,
        mode: str,
        refresh_interval: int,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
        data_path: Optional[str] = None,
        validate_fn: Optional[
            Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]
        ] = None,
    ):
        """Initialize API connector.

        Args:
            url: API endpoint URL
            mode: Operating mode ('static' or 'streaming')
            refresh_interval: Polling interval in seconds (for streaming mode)
            method: HTTP method (default: GET)
            headers: Custom headers (optional)
            params: URL parameters (optional)
            timeout: Request timeout in seconds (default: 30)
            data_path: JSON path to extract data (optional)
            validate_fn: Validation function provided by source (optional)
        """
        super().__init__()
        self.url = url
        self.mode = mode
        self.refresh_interval = refresh_interval
        self.method = method.upper()
        self.headers = headers or {}
        self.params = params or {}
        self.timeout = timeout
        self.data_path = data_path
        self.validate_fn = validate_fn
        self._deletions_enabled = False  # API doesn't delete data

    def run(self):
        """Continuously fetch data from API and insert into Pathway."""
        while True:
            try:
                # Fetch data from API
                data = self._fetch_api_data()

                # Insert each record into Pathway with validation
                for record in data:
                    # Apply validation if provided
                    if self.validate_fn:
                        validated_record = self.validate_fn(record)
                        if validated_record is not None:
                            self.next(**validated_record)
                    else:
                        self.next(**record)

                LOGGER.info("Successfully fetched %d records from API", len(data))

                # If static mode, execute only once
                if self.mode == "static":
                    LOGGER.info("Static mode: API fetch completed, exiting")
                    break

                # Streaming mode: wait before next poll
                LOGGER.info(
                    "Streaming mode: waiting %d seconds before next poll...", self.refresh_interval
                )
                time.sleep(self.refresh_interval)

            except Exception as e:
                LOGGER.error("API request failed: %s", e)
                if self.mode == "static":
                    raise
                # Streaming mode: continue retrying
                LOGGER.info(
                    "Streaming mode: retrying after %d seconds...", self.refresh_interval
                )
                time.sleep(self.refresh_interval)

    def _fetch_api_data(self) -> List[Dict[str, Any]]:
        """Fetch data from API.

        Returns:
            List of data records

        Raises:
            RuntimeError: When API request fails
            ValueError: When response format is invalid
        """
        try:
            response = requests.request(
                method=self.method,
                url=self.url,
                headers=self.headers,
                params=self.params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            LOGGER.info("fetch api: %d", response.status_code)
        except requests.RequestException as e:
            raise RuntimeError(
                f"API request failed ({self.method} {self.url}): {e}"
            ) from e

        # Parse JSON response
        try:
            json_data = response.json()
        except Exception as e:
            raise ValueError(f"Response is not valid JSON: {e}") from e

        # Extract data from specified path
        if self.data_path:
            parts = self.data_path.split(".")
            current = json_data
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    raise ValueError(
                        f"Data path '{self.data_path}' not found (failed at '{part}')"
                    )
            json_data = current

        # Ensure data is a list
        if isinstance(json_data, dict):
            json_data = [json_data]
        elif not isinstance(json_data, list):
            raise ValueError(
                f"Response data must be a list or dict, but got {type(json_data)}"
            )

        return json_data


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
        )

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
