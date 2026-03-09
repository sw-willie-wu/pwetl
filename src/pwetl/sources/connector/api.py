"""API polling connector for streaming mode."""

from typing import Any, Callable, Dict, List, Optional
import time
import requests
import pathway as pw
from pwetl.sources.connector.base import HashDiffConnectorMixin
from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)


class APIConnectorSubject(HashDiffConnectorMixin, pw.io.python.ConnectorSubject):
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
        diff_ignore_fields: Optional[list] = None,
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
            diff_ignore_fields: Fields to exclude from dedup hash (optional)
        """
        super().__init__()
        self.__init_hash_diff__(diff_ignore_fields=diff_ignore_fields)
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

                # Insert only new/changed records into Pathway
                emitted = self._emit_diff(data, self.validate_fn)

                LOGGER.info("Fetched %d records from API, %d new", len(data), emitted)

                # If static mode, execute only once
                if self.mode == "static":
                    LOGGER.info("Static mode: API fetch completed, exiting")
                    break

                # Streaming mode: wait before next poll
                LOGGER.debug(
                    "Streaming mode: waiting %d seconds before next poll...", self.refresh_interval
                )
                time.sleep(self.refresh_interval)

            except Exception as e:
                LOGGER.warning("API request failed: %s", e)
                if self.mode == "static":
                    raise
                # Streaming mode: continue retrying
                LOGGER.debug(
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
