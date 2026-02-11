"""Base class for all data sources."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import pathway as pw
from pwetl.utils.logger import get_logger

LOGGER = get_logger(__name__)


class BaseSource(ABC):
    """Abstract base class for all Sources.

    All custom Sources must inherit this class and implement the read() method.
    """

    # Subclasses can override these attributes to define required and optional config parameters
    required_config: List[str] = []
    optional_config: Dict[str, Any] = {}

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize Source.

        Args:
            name: Source name, used to identify in Pipeline
            config: Source configuration parameters
        """
        self.name = name
        self.config = config
        self._validate_config()

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
                    f"Source '{self.name}' is missing required configuration parameter: {key}"
                )

        # Set default values for optional parameters
        for key, default in self.optional_config.items():
            self.config.setdefault(key, default)

    def _get_validation_mode(self) -> str:
        """Get validation mode.

        Returns:
            Validation mode: 'sample' (default), 'strict', 'none'
        """
        return self.config.get("validation_mode", "sample")

    def _get_validation_model(self):
        """Get Pydantic validation model from schema config.

        Returns:
            Pydantic model class, or None if validation not needed
        """
        validation_mode = self._get_validation_mode()
        if validation_mode == "none":
            return None

        schema_config = self.config.get("schema")
        if not schema_config:
            return None

        try:
            from pwetl.utils.schema import SchemaParser

            return SchemaParser.create_pydantic_model(schema_config)
        except Exception as e:
            LOGGER.warning("Source '%s': cannot create validation model: %s", self.name, e)
            return None

    def _validate_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate a single record (for streaming sources).

        This method is for streaming sources that process records one at a time.

        Args:
            record: Single data record

        Returns:
            Validated/normalized record, or None if validation fails in strict mode

        Raises:
            ValueError: When validation fails in strict mode
        """
        validation_mode = self._get_validation_mode()
        if validation_mode == "none":
            return record

        pydantic_model = self._get_validation_model()
        if pydantic_model is None:
            return record

        from pydantic import ValidationError

        try:
            validated = pydantic_model(**record)
            # Always normalize data after successful validation
            return validated.model_dump()

        except ValidationError as e:
            if validation_mode == "strict":
                # In strict mode, raise error
                raise ValueError(f"Data validation failed: {e}") from e
            # In sample mode, log warning and return original
            LOGGER.warning("Source '%s': validation warning: %s", self.name, e)
            return record

    def _validate_batch(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate a batch of records (for batch sources).

        This method is for batch sources that load all data at once.
        Equivalent to _process_data_with_validation but with clearer naming.

        Args:
            data: List of data records

        Returns:
            Validated/normalized data list

        Raises:
            ValueError: When validation fails in strict mode
        """
        return self._process_data_with_validation(data, self.config.get("schema", {}))

    def _process_data_with_validation(
        self, data: List[Dict[str, Any]], schema_config: Dict
    ) -> List[Dict[str, Any]]:
        """Process data according to validation_mode.

        Unified entry point that automatically selects validation strategy based on config:
        - none: No processing, return directly
        - sample: Validate sampling, show warnings, return original data
        - strict: Validate and normalize all data, raise error on failure

        Args:
            data: List of data records
            schema_config: Schema configuration

        Returns:
            Processed data list (normalized in strict mode)

        Raises:
            ValueError: When validation fails in strict mode
        """
        validation_mode = self._get_validation_mode()

        # none mode: No processing
        if validation_mode == "none" or not schema_config:
            return data

        if not data:
            return data

        from pydantic import ValidationError
        from pwetl.utils.schema import SchemaParser

        # Create Pydantic model
        try:
            pydantic_model = SchemaParser.create_pydantic_model(schema_config)
        except Exception as e:
            LOGGER.warning("Source '%s': cannot create validation model: %s", self.name, e)
            return data

        # strict mode: Validate and convert all data, raise error on failure
        if validation_mode == "strict":
            normalized_data = []
            errors = []

            for idx, row in enumerate(data):
                try:
                    validated = pydantic_model(**row)
                    # Convert to basic types (UUID→str, Decimal→float, etc.)
                    normalized_data.append(validated.model_dump())
                except ValidationError as e:
                    errors.append({"row": idx + 1, "errors": e.errors()})

            if errors:
                self._show_validation_errors(errors, mode="strict")
                raise ValueError(
                    f"strict mode: {len(errors)} rows failed validation, please fix the data"
                )

            return normalized_data

        # sample mode: Validate and convert all data, but only warn on errors
        normalized_data = []
        errors = []

        for idx, row in enumerate(data):
            try:
                validated = pydantic_model(**row)
                # Always normalize data after successful validation
                normalized_data.append(validated.model_dump())
            except ValidationError as e:
                # On error, keep original data and record error
                normalized_data.append(row)
                errors.append({"row": idx + 1, "errors": e.errors()})

        if errors:
            self._show_validation_errors(errors, mode="sample")

        return normalized_data

    def _validate_schema_data_sample(
        self, data: List[Dict[str, Any]], pydantic_model
    ) -> None:
        """Sample validation of data (original logic).

        Args:
            data: List of data records
            pydantic_model: Pydantic model
        """
        from pydantic import ValidationError

        if not data:
            return

        # Validate all data
        errors = []
        max_errors_to_show = 10

        for idx, row in enumerate(data):
            try:
                pydantic_model(**row)
            except ValidationError as e:
                errors.append({"row": idx + 1, "errors": e.errors()})

                if len(errors) >= max_errors_to_show:
                    break

        # If errors found, show warnings
        if errors:
            self._show_validation_errors(errors, mode="sample")

    def _show_validation_errors(self, errors: List[Dict], mode: str = "sample") -> None:
        """Display validation errors.

        Args:
            errors: List of errors
            mode: Validation mode
        """
        if mode == "strict":
            warning_parts = [
                "\nData validation failed (strict mode): "
                f"{len(errors)} rows do not match schema",
                "   strict mode requires all data to pass validation\n",
            ]
        else:
            warning_parts = [
                f"\nData validation warning: {len(errors)} rows do not match schema",
                "   These rows may be filtered out by Pathway during execution\n",
            ]

            # Show error details
            for error_info in errors[:5]:  # Show details for first 5 rows at most
                warning_parts.append(f"   Row {error_info['row']}:")
                for err in error_info["errors"][:3]:  # Show at most 3 errors per row
                    field = ".".join(str(x) for x in err["loc"])
                    msg = err["msg"]
                    warning_parts.append(f"     - {field}: {msg}")
                if len(error_info["errors"]) > 3:
                    warning_parts.append(
                        f"     ... ({len(error_info['errors']) - 3} more errors)"
                    )

            if len(errors) > 5:
                warning_parts.append(
                    f"\n   ... ({len(errors) - 5} more rows with errors)"
                )

            if mode == "sample":
                warning_parts.append("\n   Suggestions:")
                warning_parts.append(
                    "      - Make nullable fields Optional (e.g., 'Address: str?')"
                )
                warning_parts.append(
                    "      - Or add 'validation_mode: none' "
                    "in config to skip validation"
                )
                warning_parts.append(
                    "      - Or use 'validation_mode: strict' "
                    "to enforce validation on all data\n"
                )

            LOGGER.warning("\n".join(warning_parts))

    @abstractmethod
    def read(self) -> pw.Table:
        """Read data and return Pathway Table.

        Returns:
            pw.Table: Pathway Table containing the data

        Raises:
            Exception: When read fails
        """

    def setup(self) -> None:
        """Initialize resources (optional).

        Called before read(), used to establish connections, load resources, etc.
        Subclasses can override this method.
        """

    def teardown(self) -> None:
        """Clean up resources (optional).

        Called after read(), used to close connections, release resources, etc.
        Subclasses can override this method.
        """
