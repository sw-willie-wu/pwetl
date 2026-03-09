"""ETL Pipeline."""

from typing import Dict
import pathway as pw
from pwetl.sources.base import BaseSource
from pwetl.sinks.base import BaseSink
from pwetl.transforms.base import BaseTransform
from pwetl.core.exceptions import SourceError, TransformError, SinkError
from pwetl.utils.logger import get_logger


LOGGER = get_logger(__name__)


class Pipeline:
    """ETL Pipeline.

    Orchestrates the execution flow: Source → Transform → Sink.
    """

    def __init__(
        self,
        sources: Dict[str, BaseSource],
        transform: BaseTransform,
        sinks: Dict[str, BaseSink],
        verbose: bool = False,
    ):
        """Initialize Pipeline.

        Args:
            sources: Dictionary of Source instances, format: {name: BaseSource}
            transform: Transform instance
            sinks: Dictionary of Sink instances, format: {name: BaseSink}
            verbose: Whether to show detailed output
        """
        self.sources = sources
        self.transform = transform
        self.sinks = sinks
        self.verbose = verbose

    def run(self) -> None:
        """Execute Pipeline.

        Execution order:
        1. Initialize all components (setup)
        2. Read data from all Sources
        3. Process data with Transform
        4. Write to all Sinks
        5. Run Pathway
        6. Clean up all components (teardown)

        Raises:
            RuntimeError: When any stage fails
        """
        main_error = None
        try:
            LOGGER.info("Pipeline starting...")

            # Stage 1: Initialize
            self._setup_all()
            LOGGER.info("Pipeline setup complete")

            # Stage 2: Source - Read data
            tables = self._read_sources()
            LOGGER.info("Sources read complete")

            # Stage 3: Transform - Process data
            result_tables = self._transform(tables)
            LOGGER.info("Transform complete")

            # Stage 4: Sink - Write data
            self._write_sinks(result_tables)
            LOGGER.info("Sinks write scheduled")

            # Run Pathway
            LOGGER.info("Running Pathway engine...")
            pw.run(monitoring_level=pw.MonitoringLevel.NONE)
            LOGGER.info("Pipeline completed")

        except Exception as e:
            main_error = e

        # Always run teardown — all components get a chance to clean up
        LOGGER.debug("Cleaning up resources...")
        teardown_error = self._teardown_all()

        # Raise: main flow error takes priority over teardown error
        if main_error is not None:
            if teardown_error is not None:
                LOGGER.warning("Teardown also failed: %s", teardown_error)
            raise main_error
        if teardown_error is not None:
            raise teardown_error

    def _setup_all(self) -> None:
        """Initialize all components."""
        # Initialize Sources
        for name, source in self.sources.items():
            try:
                source.setup()
                LOGGER.info("  Source '%s' initialized", name)
            except Exception as e:
                raise SourceError(f"Source '{name}' initialization failed: {e}") from e

        # Initialize Transform
        try:
            self.transform.setup()
            LOGGER.info("  Transform initialized")
        except Exception as e:
            raise TransformError(f"Transform initialization failed: {e}") from e

        # Initialize Sinks
        for name, sink in self.sinks.items():
            try:
                sink.setup()
                LOGGER.info("  Sink '%s' initialized", name)
            except Exception as e:
                raise SinkError(f"Sink '{name}' initialization failed: {e}") from e

    def _read_sources(self) -> Dict[str, pw.Table]:
        """Read data from all Sources.

        Returns:
            Dictionary of tables, format: {source_name: pw.Table}

        Raises:
            RuntimeError: When any Source read fails
        """
        tables = {}

        for name, source in self.sources.items():
            try:
                tables[name] = source.read()
                LOGGER.info("  Source '%s' read complete", name)
            except Exception as e:
                raise SourceError(f"Source '{name}' read failed: {e}") from e

        return tables

    def _transform(self, tables: Dict[str, pw.Table]) -> Dict[str, pw.Table]:
        """Execute Transform.

        Args:
            tables: Dictionary of input tables

        Returns:
            Dictionary of output tables

        Raises:
            RuntimeError: When Transform processing fails
        """
        try:
            result_tables = self.transform.transform(tables)

            # Validate return value
            if not isinstance(result_tables, dict):
                raise TransformError(
                    f"Transform must return Dict[str, pw.Table], but returned {type(result_tables)}"
                )

            return result_tables

        except TransformError:
            raise
        except Exception as e:
            raise TransformError(f"Transform processing failed: {e}") from e

    def _write_sinks(self, result_tables: Dict[str, pw.Table]) -> None:
        """Write to all Sinks.

        Args:
            result_tables: Dictionary of tables to write

        Raises:
            RuntimeError: When any Sink write fails
        """
        for name, sink in self.sinks.items():
            try:
                if name not in result_tables:
                    raise TransformError(
                        f"Transform did not produce required table for Sink '{name}'.\n"
                        f"Available tables: {', '.join(result_tables.keys())}"
                    )

                table = result_tables[name]
                sink.write(table)
                LOGGER.info("  Sink '%s' write scheduled", name)

            except (TransformError, SinkError):
                raise
            except Exception as e:
                raise SinkError(f"Sink '{name}' write failed: {e}") from e

    def _teardown_all(self) -> SourceError | TransformError | SinkError | None:
        """Clean up all components.

        All components are cleaned up even if some fail.
        Returns the first error (wrapped in the appropriate type) or None.
        """
        first_error = None

        # Clean up Sources
        for name, source in self.sources.items():
            try:
                source.teardown()
            except Exception as e:
                LOGGER.warning("Source '%s' teardown failed: %s", name, e)
                if first_error is None:
                    first_error = (
                        e if isinstance(e, SourceError)
                        else SourceError(f"Source '{name}' teardown failed: {e}")
                    )

        # Clean up Transform
        try:
            self.transform.teardown()
        except Exception as e:
            LOGGER.warning("Transform teardown failed: %s", e)
            if first_error is None:
                first_error = (
                    e if isinstance(e, TransformError)
                    else TransformError(f"Transform teardown failed: {e}")
                )

        # Clean up Sinks
        for name, sink in self.sinks.items():
            try:
                sink.teardown()
            except Exception as e:
                LOGGER.warning("Sink '%s' teardown failed: %s", name, e)
                if first_error is None:
                    first_error = (
                        e if isinstance(e, SinkError)
                        else SinkError(f"Sink '{name}' teardown failed: {e}")
                    )

        return first_error
