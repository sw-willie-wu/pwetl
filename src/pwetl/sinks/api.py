"""API data sink."""

import time
from typing import Any, Dict, List
import requests
import pathway as pw
from pwetl.sinks.base import BaseSink


class APISink(BaseSink):
    """API output.

    POST data to API endpoint.
    Supports:
    - POST JSON data
    - Custom headers
    - Error retry
    """

    required_config = ["url"]
    optional_config = {
        "method": "POST",  # HTTP method
        "headers": {},  # Custom headers
        "timeout": 30,  # Timeout in seconds
        "max_retry": 3,  # Maximum retry count
        "retry_delay": 1,  # Retry delay in seconds
        "batch_size": 1,  # Batch size (0 means send all at once)
        "format": "json",  # Data format: 'json' or 'form'
    }

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize APISink."""
        super().__init__(name, config)
        self._temp_path = None

    def write(self, table: pw.Table) -> None:
        """POST data to API.

        Args:
            table: Pathway Table to write

        Raises:
            requests.RequestException: When API request fails
        """
        # Pathway is streaming, we need to output data to a temporary location
        # then read and send to API

        import tempfile
        import os

        # Create temporary file
        fd, temp_path = tempfile.mkstemp(suffix=".jsonl", text=True)
        os.close(fd)

        try:
            # Write to temporary file first
            pw.io.jsonlines.write(table, temp_path)

            # Execute Pathway to ensure data is written
            # Note: This runs in Pipeline.run()

            # Read temporary file and send to API
            # This part runs in teardown
            self._temp_path = temp_path

        except Exception:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def teardown(self) -> None:
        """Clean up resources and send data to API."""
        import json
        import os
        import logging

        logger = logging.getLogger(__name__)

        if not hasattr(self, "_temp_path") or self._temp_path is None:
            logger.warning("APISink %s: No temp_path attribute", self.name)
            return

        temp_path: str = self._temp_path
        logger.info(
            "APISink %s: Starting teardown with temp file %s",
            self.name, temp_path
        )

        try:
            # Check if temporary file exists
            if not os.path.exists(temp_path):
                logger.warning("APISink %s: Temp file does not exist", self.name)
                return

            # Read data
            data = []
            with open(temp_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))

            logger.info(
                "APISink %s: Read %d records from temp file",
                self.name, len(data)
            )

            # Send to API
            if data:
                logger.info(
                    "APISink %s: Sending data with format=%s",
                    self.name, self.config.get('format', 'json')
                )
                self._send_to_api(data)
            else:
                logger.warning("APISink %s: No data to send", self.name)

        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.info("APISink %s: Cleaned up temp file", self.name)

    def _send_to_api(self, data: List[Dict[str, Any]]) -> None:
        """Send data to API.

        Args:
            data: List of data to send

        Raises:
            requests.RequestException: When request fails after retries are exhausted
        """
        headers = self.config["headers"]
        batch_size = self.config["batch_size"]
        data_format = self.config.get("format", "json")

        # Set default Content-Type based on format
        if "Content-Type" not in headers:
            if data_format == "form":
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                headers["Content-Type"] = "application/json"

        # Send in batches
        if batch_size > 0:
            batches = [
                data[i : i + batch_size] for i in range(0, len(data), batch_size)
            ]
        else:
            batches = [data]  # Send all at once

        # Send each batch
        for batch in batches:
            self._send_batch(batch)

    def _send_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Send a single batch to API.

        Args:
            batch: Data batch to send

        Raises:
            requests.RequestException: When request still fails after retries are exhausted
        """
        url = self.config["url"]
        method = self.config["method"].upper()
        headers = self.config["headers"]
        timeout = self.config["timeout"]
        max_retry = self.config["max_retry"]
        retry_delay = self.config["retry_delay"]
        data_format = self.config.get("format", "json")

        for attempt in range(max_retry + 1):
            try:
                # Choose data format
                if data_format == "form":
                    # For form data, send each item as separate form fields
                    # If batch has multiple items, flatten to single form
                    form_data = {}
                    if len(batch) == 1:
                        form_data = batch[0]
                    else:
                        # Multiple items: use indexed keys
                        for idx, item in enumerate(batch):
                            for key, value in item.items():
                                form_data[f"{key}_{idx}"] = value

                    response = requests.request(
                        method=method,
                        url=url,
                        data=form_data,
                        headers=headers,
                        timeout=timeout,
                    )
                else:
                    # JSON format (default)
                    response = requests.request(
                        method=method,
                        url=url,
                        json=batch,
                        headers=headers,
                        timeout=timeout,
                    )
                response.raise_for_status()
                return  # Success

            except requests.RequestException as e:
                # If retries remain, wait and retry
                if attempt < max_retry:
                    time.sleep(retry_delay)
                    continue
                # Retries exhausted
                raise RuntimeError(
                    f"API request failed (retried {max_retry} times): {e}"
                ) from e
