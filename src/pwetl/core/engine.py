"""ETL Engine."""

import sys
from pathlib import Path
from typing import Union

from pwetl.core.config import ConfigLoader
from pwetl.core.exceptions import ConfigurationError
from pwetl.core.pipeline import Pipeline
from pwetl.core.registry import SinkFactory, SourceFactory
from pwetl.utils.env import load_env_file
from pwetl.utils.loader import TransformLoader
from pwetl.utils.logger import get_logger


LOGGER = get_logger(__name__)


class ETLEngine:
    """ETL Engine.

    Responsibilities:
    1. Load configuration
    2. Build pipeline
    3. Execute ETL workflow
    """

    def __init__(
        self,
        config_path: Union[str, Path],
        env_file: Union[str, Path, None] = None,
        verbose: bool = False,
    ):
        """Initialize ETL Engine.

        Args:
            config_path: Path to configuration file
            env_file: Path to .env file, if None will auto-discover
            verbose: Whether to show detailed output
        """
        self.config_path = Path(config_path).resolve()
        self.env_file = env_file
        self.verbose = verbose
        self.config: dict | None = None
        self.pipeline: Pipeline | None = None

        # Add configuration directory to Python path to allow loading relative modules
        config_dir = str(self.config_path.parent)
        if config_dir not in sys.path:
            sys.path.insert(0, config_dir)

    def execute(self) -> None:
        """Execute ETL workflow.

        Raises:
            Exception: When execution fails
        """
        try:
            LOGGER.debug("Start ETL Engine execution...")
            LOGGER.debug("Loading environment variables...")
            self._load_env()

            # Load configuration
            LOGGER.debug("Loading yaml configuration...")
            self._load_config()

            # Build Pipeline
            LOGGER.debug("Initializing Pipeline structure...")
            self._build_pipeline()

            # Execute Pipeline
            if self.pipeline is None:
                raise RuntimeError("Pipeline not initialized, cannot execute.")
            self.pipeline.run()

        except Exception:
            if self.verbose:
                import traceback

                traceback.print_exc()
            raise

    def dry_run(self) -> None:
        """Dry-run mode: validate configuration only, do not execute.

        Raises:
            Exception: When validation fails
        """
        try:
            print("Validation mode...")

            # Load environment variables
            print("  ✓ Load environment variables")
            self._load_env()

            # Load configuration
            print("  ✓ Load configuration")
            self._load_config()

            # Build Pipeline (validates all components can be correctly created)
            print("  ✓ Validate Pipeline configuration")
            self._build_pipeline()

            print("\nConfiguration validation passed")

        except Exception as e:
            print(f"\nValidation failed: {e}")
            if self.verbose:
                import traceback

                print("\nDetailed error information:")
                traceback.print_exc()
            raise

    def _load_env(self) -> None:
        """Load environment variables."""
        if self.env_file:
            load_env_file(self.env_file)
        else:
            # Auto-discover .env file
            load_env_file(".env")

    def _load_config(self) -> None:
        """Load configuration.

        Raises:
            ConfigurationError: When configuration loading fails
        """
        self.config = ConfigLoader.load(self.config_path)

    def _build_pipeline(self) -> None:
        """Build Pipeline.

        Raises:
            ConfigurationError: When Source/Sink/Transform config is invalid
            RuntimeError: When Pipeline building fails for other reasons
        """
        if self.config is None:
            raise RuntimeError("Configuration not loaded, cannot build Pipeline.")

        # Build Sources
        sources = {}
        for source_config in self.config["sources"]:
            name = source_config["name"]
            try:
                sources[name] = SourceFactory.create(name, source_config)
            except Exception as e:
                raise ConfigurationError(
                    f"Source '{name}' configuration error: {e}"
                ) from e
        LOGGER.debug(
            "  Find %d Sources: %s", len(sources), ", ".join(sources.keys())
        )

        # Load Transform
        try:
            transform = TransformLoader.load(self.config["transform"])
        except Exception as e:
            raise ConfigurationError(
                f"Transform configuration error: {e}"
            ) from e
        LOGGER.debug("  Find Transform module: %s", self.config["transform"])

        # Build Sinks
        sinks = {}
        for sink_config in self.config["sinks"]:
            name = sink_config["name"]
            try:
                sinks[name] = SinkFactory.create(name, sink_config)
            except Exception as e:
                raise ConfigurationError(
                    f"Sink '{name}' configuration error: {e}"
                ) from e
        LOGGER.debug("  Find %d Sinks: %s", len(sinks), ", ".join(sinks.keys()))

        # Create Pipeline
        self.pipeline = Pipeline(
            sources=sources,
            transform=transform,
            sinks=sinks,
            verbose=self.verbose,
        )
