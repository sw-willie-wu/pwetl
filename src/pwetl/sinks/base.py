"""Base class for all data sinks."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
import pathway as pw


class BaseSink(ABC):
    """Abstract base class for all Sinks.

    All custom Sinks must inherit this class and implement the write() method.
    """

    # Subclasses can override these attributes to define required and optional config parameters
    required_config: List[str] = []
    optional_config: Dict[str, Any] = {}

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize Sink.

        Args:
            name: Sink name, used to identify in Pipeline
            config: Sink configuration parameters
        """
        self.name = name
        self.config = config
        self.schema_class = None
        self._validate_config()
        self._setup_schema()

    def _validate_config(self) -> None:
        """Validate configuration parameters.

        Check if required parameters exist and set default values for optional parameters.

        Raises:
            ValueError: When required parameters are missing
        """
        # Check required parameters
        for key in self.required_config:
            if key not in self.config:
                raise ValueError(
                    f"Sink '{self.name}' is missing required configuration parameter: {key}"
                )

        # Set default values for optional parameters
        for key, default in self.optional_config.items():
            self.config.setdefault(key, default)

    @abstractmethod
    def write(self, table: pw.Table) -> None:
        """Write Pathway Table.

        Args:
            table: Pathway Table to write

        Raises:
            Exception: When write fails
        """

    def setup(self) -> None:
        """Initialize resources (optional).

        Called before write(), used to establish connections, create tables, etc.
        Subclasses can override this method.
        """

    def teardown(self) -> None:
        """Clean up resources (optional).

        Called after write(), used to close connections, release resources, etc.
        Subclasses can override this method.
        """

    def _setup_schema(self) -> None:
        """Set up schema (if defined in configuration)."""
        if "schema" in self.config:
            from pwetl.utils.schema import SchemaParser

            self.schema_class = SchemaParser.parse(self.config["schema"])

    def _apply_schema(self, table: pw.Table) -> pw.Table:
        """Apply schema to table (if schema is defined).

        Args:
            table: Input Pathway Table

        Returns:
            Table after applying schema, returns original table if no schema is defined
        """
        if self.schema_class is None:
            return table

        # Select and convert based on schema type annotations
        selections = {}
        for field, field_type in self.schema_class.__annotations__.items():
            # Get the original type (remove Optional)
            import typing

            origin = typing.get_origin(field_type)
            if origin is typing.Union:
                # Optional[T] is Union[T, None]
                args = typing.get_args(field_type)
                actual_type = args[0] if args else field_type
            else:
                actual_type = field_type

            # Convert based on type
            if actual_type in (int, float, bool, str):
                selections[field] = pw.cast(actual_type, pw.this[field])
            else:
                # Other types (dict, datetime, etc.) are selected directly
                selections[field] = pw.this[field]

        return table.select(**selections)
