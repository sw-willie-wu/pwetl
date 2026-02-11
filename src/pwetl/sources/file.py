"""File-based data sources."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import pathway as pw
from pwetl.sources.base import BaseSource
from pwetl.utils.schema import SchemaParser
from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)


class FileSource(BaseSource):
    """File data source.

    Supported formats: CSV, JSON, JSONL

    Can specify single file or monitor directory:
    - Single file: path points to file
    - Directory monitoring: path points to directory, use regex or filename_pattern to filter
    """

    required_config = ["path"]
    optional_config = {
        "format": "csv",  # Default to CSV
        "schema": None,  # Optional schema
        "mode": "static",  # 'static' or 'streaming'
        "regex": None,  # Regex to filter filenames (directory mode)
        "filename_pattern": None,  # Filename matching pattern (glob pattern, directory mode)
    }

    # Supported file formats
    SUPPORTED_FORMATS = ["csv", "json", "jsonl"]

    def read(self) -> pw.Table:
        """Read file data.

        Returns:
            pw.Table: Pathway Table containing the data

        Raises:
            ValueError: When file format is not supported
            FileNotFoundError: When file or directory does not exist
        """
        path = self.config["path"]
        file_format = self.config["format"]
        mode = self.config.get("mode", "static")
        LOGGER.info("Source '%s': reading %s (%s, %s mode)", self.name, path, file_format, mode)

        # Check if path exists
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        # Check if format is supported
        if file_format not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported file format: '{file_format}'\n"
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # Parse Schema
        schema = self._get_schema()

        # Check if strict validation mode is used
        validation_mode = self._get_validation_mode()

        # Validation modes that require schema
        if validation_mode in ("sample", "strict") and not schema:
            raise ValueError(
                f"Schema configuration is required when validation_mode='{validation_mode}'. "
                f"Validation modes 'sample' and 'strict' use Pydantic to validate data. "
                f"Please add 'schema' section in your config or set validation_mode='none'."
            )

        # strict mode: read data, validate, transform, then create Table
        if validation_mode == "strict":
            return self._read_with_strict_validation(path, file_format)

        # Determine if it's a directory or a file
        if path_obj.is_dir():
            return self._read_directory(path, file_format, schema)
        return self._read_single_file(path, file_format, schema)

    def _read_single_file(
        self, path: str, file_format: str, schema: Optional[Type[pw.Schema]]
    ) -> pw.Table:
        """Read a single file."""
        # Read file based on format
        if file_format == "csv":
            return self._read_csv(path, schema)
        if file_format == "json":
            return self._read_json(path, schema)
        if file_format == "jsonl":
            return self._read_jsonl(path, schema)
        raise ValueError(f"Unsupported file format: {file_format}")

    def _read_directory(
        self, path: str, file_format: str, schema: Optional[Type[pw.Schema]]
    ) -> pw.Table:
        """Read files in a directory.

        Use regex or filename_pattern to filter files.
        """
        regex_pattern = self.config.get("regex")
        filename_pattern = self.config.get("filename_pattern")

        # Build final read path based on format
        if regex_pattern:
            # Use regex filtering
            final_path = self._get_regex_filtered_path(path, file_format, regex_pattern)
        elif filename_pattern:
            # Use filename matching pattern (glob pattern)
            final_path = str(Path(path) / filename_pattern)
        else:
            # Default: read all files matching the format
            final_path = str(Path(path) / f"*.{file_format}")

        # Read file based on format
        if file_format == "csv":
            return self._read_csv(final_path, schema)
        if file_format == "json":
            return self._read_json(final_path, schema)
        if file_format == "jsonl":
            return self._read_jsonl(final_path, schema)
        raise ValueError(f"Unsupported file format: {file_format}")

    def _get_regex_filtered_path(
        self, directory: str, file_format: str, pattern: str
    ) -> str:
        """Filter files using regular expression, convert to glob pattern.

        Note: Pathway doesn't directly support regex, so we need to find matching files
        and convert to usable path format. This method has limited effectiveness in streaming mode.

        Args:
            directory: Directory path
            file_format: File format
            pattern: Regular expression pattern

        Returns:
            File path pattern matching the criteria
        """
        regex = re.compile(pattern)
        dir_path = Path(directory)

        # In static mode, files can be filtered directly
        mode = self.config.get("mode", "static")
        if mode == "static":
            # Find all files matching the regex
            matching_files = [
                str(f)
                for f in dir_path.glob(f"*.{file_format}")
                if regex.search(f.name)
            ]

            if not matching_files:
                raise ValueError(
                    f"Cannot find {file_format} files matching pattern '{pattern}' in {directory}"
                )

            # If there's only one file, return it directly
            if len(matching_files) == 1:
                return matching_files[0]

            # Multiple files: use glob pattern (more limited)
            # Try to convert regex to glob pattern (simple cases)
            return self._convert_regex_to_glob(directory, file_format, pattern)
        # streaming mode: convert to glob (more limited)
        return self._convert_regex_to_glob(directory, file_format, pattern)

    def _convert_regex_to_glob(
        self, directory: str, file_format: str, pattern: str
    ) -> str:
        """Try to convert simple regular expressions to glob pattern.

        This only supports simple regex patterns.
        For complex patterns, use filename_pattern instead.
        """
        # Simple conversion rules
        glob = pattern.replace(".*", "*").replace(".+", "*").replace("\\d", "[0-9]")

        # If pattern doesn't include file extension, add it
        if not glob.endswith(f".{file_format}"):
            glob = f"{glob}*.{file_format}"

        return str(Path(directory) / glob)

    def _get_schema(self) -> Optional[Type[pw.Schema]]:
        """Get Schema.

        Returns:
            Pathway Schema class, returns None if not specified
        """
        schema_config = self.config.get("schema")
        if schema_config:
            return SchemaParser.parse(schema_config)
        return None

    def _read_with_strict_validation(
        self, path: str, file_format: str
    ) -> pw.Table:
        """Read with strict mode: load data, validate, transform, then create Table.

        Args:
            path: File or directory path
            file_format: File format

        Returns:
            Validated and normalized Pathway Table
        """
        # Load raw data
        path_obj = Path(path)

        if path_obj.is_dir():
            # Read all files in the directory
            raw_data = []
            pattern = f"*.{file_format}"
            for file_path in path_obj.glob(pattern):
                raw_data.extend(self._load_file_data(str(file_path), file_format))
        else:
            raw_data = self._load_file_data(path, file_format)

        # Apply validation automatically (framework handles it)
        normalized_data = self._validate_batch(raw_data)

        # Create Table with processed data
        simple_schema = self._create_simple_schema()

        # Convert dict to schema format
        rows = []
        field_names = list(simple_schema.__annotations__.keys())
        for row_dict in normalized_data:
            # Extract values in schema order, convert to tuple
            row_tuple = tuple(row_dict.get(field, None) for field in field_names)
            rows.append(row_tuple)

        return pw.debug.table_from_rows(schema=simple_schema, rows=rows)

    def _load_file_data(self, file_path: str, file_format: str) -> List[Dict[str, Any]]:
        """Load file data as Python objects.

        Args:
            file_path: File path
            file_format: File format

        Returns:
            Data list
        """
        import csv
        import json

        if file_format == "csv":
            with open(file_path, "r", encoding="utf-8") as f:
                return list(csv.DictReader(f))

        elif file_format in ("json", "jsonl"):
            data = []
            with open(file_path, "r", encoding="utf-8") as f:
                if file_format == "json":
                    content = json.load(f)
                    # If it's an array, expand it; otherwise treat as single object
                    if isinstance(content, list):
                        data = content
                    else:
                        data = [content]
                else:  # jsonl
                    for line in f:
                        line = line.strip()
                        if line:
                            data.append(json.loads(line))
            return data

        return []

    def _create_simple_schema(self) -> Type[pw.Schema]:
        """Create simplified schema (special types already converted to basic types).

        Returns:
            Simplified schema (contains only basic types)
        
        Raises:
            ValueError: If schema config is not provided (should not happen if called correctly)
        """
        # Get fields from original_schema, but simplify types
        # Since data has been dumped to basic types, most fields can use Any or be inferred
        # Simplest approach is not to specify schema, let Pathway auto-infer
        # But to maintain field order and type consistency, we re-parse from config
        schema_config = self.config.get("schema", {})
        if not schema_config:
            # This should not happen if validation is done correctly in read()
            raise ValueError(
                "Schema configuration is missing. "
                "This is an internal error - schema should be validated before calling this method."
            )

        # Use already processed mapping logic
        return SchemaParser.parse(schema_config)

    def _read_csv(self, path: str, schema: Optional[Type[pw.Schema]]) -> pw.Table:
        """Read CSV file."""
        mode = self.config["mode"]
        if schema:
            return pw.io.csv.read(path, schema=schema, mode=mode)
        return pw.io.csv.read(path, mode=mode)

    def _read_json(self, path: str, schema: Optional[Type[pw.Schema]]) -> pw.Table:
        """Read JSON file (single object or array)."""
        mode = self.config["mode"]
        if schema:
            return pw.io.jsonlines.read(path, schema=schema, mode=mode)
        return pw.io.jsonlines.read(path, mode=mode)

    def _read_jsonl(self, path: str, schema: Optional[Type[pw.Schema]]) -> pw.Table:
        """Read JSONL file (one JSON object per line)."""
        mode = self.config["mode"]
        if schema:
            return pw.io.jsonlines.read(path, schema=schema, mode=mode)
        return pw.io.jsonlines.read(path, mode=mode)
