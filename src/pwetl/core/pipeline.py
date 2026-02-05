"""ETL Pipeline."""

from typing import Dict
import pathway as pw
from pwetl.sources.base import BaseSource
from pwetl.sinks.base import BaseSink
from pwetl.transforms.base import BaseTransform
from pwetl.utils.logger import get_logger


LOGGER = get_logger()


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
        try:
            # Stage 1: Initialize
            LOGGER.debug("Setup Pipeline workflow...")
            self._setup_all()

            # Stage 2: Source - Read data
            tables = self._read_sources()

            # Stage 3: Transform - Process data
            LOGGER.debug("  Processing with Transform module...")
            result_tables = self._transform(tables)

            # Stage 4: Sink - Write data
            self._write_sinks(result_tables)

            # Run Pathway
            LOGGER.debug("Setup done, start pathway Pipeline...")
            pw.run(monitoring_level=pw.MonitoringLevel.NONE)
            LOGGER.debug("Completed execution.")

        finally:
            LOGGER.debug("Cleaning up resources...")
            self._teardown_all()

    def _setup_all(self) -> None:
        """Initialize all components."""
        # Initialize Sources
        for name, source in self.sources.items():
            try:
                source.setup()
            except Exception as e:
                raise RuntimeError(f"Source '{name}' initialization failed: {e}") from e

        # Initialize Transform
        try:
            self.transform.setup()
        except Exception as e:
            raise RuntimeError(f"Transform initialization failed: {e}") from e

        # Initialize Sinks
        for name, sink in self.sinks.items():
            try:
                sink.setup()
            except Exception as e:
                raise RuntimeError(f"Sink '{name}' initialization failed: {e}") from e

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
                LOGGER.debug("  Read Source '%s'...", name)
                tables[name] = source.read()
            except Exception as e:
                raise RuntimeError(f"Source '{name}' read failed: {e}") from e

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
                raise TypeError(
                    "Transform must return Dict[str, pw.Table], "
                    f"but returned {type(result_tables)}"
                )

            return result_tables

        except Exception as e:
            raise RuntimeError(f"Transform processing failed: {e}") from e

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
                    raise ValueError(
                        f"Transform did not produce required table for Sink '{name}'.\n"
                        f"Available tables: {', '.join(result_tables.keys())}"
                    )
                LOGGER.debug("  Write Sink '%s'...", name)

                table = result_tables[name]
                sink.write(table)

            except Exception as e:
                raise RuntimeError(f"Sink '{name}' write failed: {e}") from e

    def _teardown_all(self) -> None:
        """Clean up all components."""
        # Clean up Sources
        for name, source in self.sources.items():
            try:
                source.teardown()
            except Exception as e:
                LOGGER.debug("Source '%s' cleanup failed: %s", name, e)

        # Clean up Transform
        try:
            self.transform.teardown()
        except Exception as e:
            LOGGER.debug("Transform cleanup failed: %s", e)

        # Clean up Sinks
        for name, sink in self.sinks.items():
            try:
                sink.teardown()
            except Exception as e:
                LOGGER.debug("Sink '%s' cleanup failed: %s", name, e)
