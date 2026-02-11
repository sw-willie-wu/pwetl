"""File-based data sinks."""

from pathlib import Path

import pathway as pw

from pwetl.sinks.base import BaseSink
from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)


class FileSink(BaseSink):
    """File output.

    Supported formats: CSV, JSON, JSONL
    """

    required_config = ["path"]
    optional_config = {
        "format": "csv",  # Default to CSV
    }

    def __init__(self, name: str, config: dict):
        """Initialize FileSink."""
        super().__init__(name, config)
        self._jsonl_temp_path = None
        self._json_output_path = None

    # Supported file formats
    SUPPORTED_FORMATS = ["csv", "json", "jsonl"]

    def write(self, table: pw.Table) -> None:
        """Write to file.

        Args:
            table: Pathway Table to write

        Raises:
            ValueError: When file format is not supported
        """
        # Apply schema (if defined)
        table = self._apply_schema(table)

        path = self.config["path"]
        # Auto-detect format from file extension if not explicitly set
        file_format = self.config.get("format")
        if not file_format:
            # Extract extension from path
            ext = Path(path).suffix.lstrip('.')
            file_format = ext if ext in self.SUPPORTED_FORMATS else "csv"

        # Check if format is supported
        if file_format not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported file format: '{file_format}'\n"
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # Ensure directory exists
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        LOGGER.info("Sink '%s': writing %s to %s", self.name, file_format, path)

        # Write file based on format
        if file_format == "csv":
            self._write_csv(table, path)
        elif file_format == "json":
            self._write_json(table, path)
        elif file_format == "jsonl":
            self._write_jsonl(table, path)

    def _write_csv(self, table: pw.Table, path: str) -> None:
        """Write to CSV file."""
        pw.io.csv.write(table, path)

    def _write_json(self, table: pw.Table, path: str) -> None:
        """Write to JSON file (array format)."""
        # First write to JSONL format
        self._jsonl_temp_path = path + ".jsonl_temp"
        pw.io.jsonlines.write(table, self._jsonl_temp_path)
        # Record JSON file that needs post-processing
        self._json_output_path = path

    def _write_jsonl(self, table: pw.Table, path: str) -> None:
        """Write to JSONL file."""
        pw.io.jsonlines.write(table, path)

    def teardown(self) -> None:
        """Clean up and post-process (convert JSONL to JSON array)."""
        if self._jsonl_temp_path and self._json_output_path:
            import json

            # Read JSONL file and convert to JSON array
            objects = []
            with open(self._jsonl_temp_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        objects.append(json.loads(line))

            # Write JSON array
            with open(self._json_output_path, "w", encoding="utf-8") as f:
                json.dump(objects, f, ensure_ascii=False, indent=2)

            # Delete temporary file
            Path(self._jsonl_temp_path).unlink(missing_ok=True)
            LOGGER.info("Sink '%s': converted JSONL to JSON array", self.name)
