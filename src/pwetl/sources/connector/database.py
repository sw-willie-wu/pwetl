"""Database polling connector for streaming mode."""

from typing import Any, Callable, Dict, List, Optional
import time
import pathway as pw
from pwetl.sources.connector.base import HashDiffConnectorMixin
from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)


class DatabaseConnectorSubject(HashDiffConnectorMixin, pw.io.python.ConnectorSubject):
    """Database polling connector for streaming mode."""

    def __init__(
        self,
        engine,
        query: str,
        refresh_interval: int,
        mode: str,
        validate_fn: Optional[
            Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]
        ] = None,
        diff_ignore_fields: Optional[list] = None,
    ):
        super().__init__()
        self.__init_hash_diff__(diff_ignore_fields=diff_ignore_fields)
        self._engine = engine
        self._query = query
        self._refresh_interval = refresh_interval
        self._mode = mode
        self._validate_fn = validate_fn
        self._deletions_enabled = False

    def run(self):
        """Continuously fetch data from database and insert into Pathway."""
        while True:
            try:
                data = self._execute_query()

                emitted = self._emit_diff(data, self._validate_fn)

                LOGGER.info("Fetched %d records, %d new", len(data), emitted)

                if self._mode == "static":
                    LOGGER.info("Static mode: database fetch completed")
                    break

                LOGGER.info(
                    "Streaming mode: waiting %d seconds before next poll...",
                    self._refresh_interval,
                )
                time.sleep(self._refresh_interval)

            except Exception as e:
                LOGGER.error("Database query failed: %s", e)
                if self._mode == "static":
                    raise
                LOGGER.info(
                    "Streaming mode: retrying after %d seconds...",
                    self._refresh_interval,
                )
                time.sleep(self._refresh_interval)

    def _execute_query(self) -> List[Dict[str, Any]]:
        """Execute SQL query and return list of dicts."""
        from sqlalchemy import text

        with self._engine.connect() as conn:
            result = conn.execute(text(self._query))
            columns = list(result.keys())
            return [dict(zip(columns, row)) for row in result.fetchall()]
