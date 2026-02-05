"""Configuration loader."""

from pathlib import Path
from typing import Any, Dict, Union

import yaml
from pydantic import ValidationError

from pwetl.core.schema import BaseETLSchema
from pwetl.utils.env import EnvVarSubstitution
from pwetl.core.exceptions import ConfigurationError


class ConfigLoader:
    """YAML configuration loader.

    Responsibilities:
    1. Load YAML configuration files
    2. Substitute environment variables
    3. Validate configuration structure using Pydantic
    """

    @staticmethod
    def load(config_path: Union[str, Path]) -> Dict[str, Any]:
        """Load and validate configuration file.

        Args:
            config_path: Path to configuration file

        Returns:
            Parsed configuration dictionary

        Raises:
            FileNotFoundError: When configuration file does not exist
            ConfigurationError: When configuration format is invalid
            yaml.YAMLError: When YAML syntax is invalid
        """
        path = Path(config_path)

        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Load YAML
        with open(path, "r", encoding="utf-8") as f:
            try:
                config_dict = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ConfigurationError(f"YAML syntax error: {e}") from e

        if config_dict is None:
            raise ConfigurationError("Configuration file is empty")

        # Substitute environment variables
        config_dict = EnvVarSubstitution.substitute(config_dict)

        # Validate configuration structure using Pydantic
        try:
            config_model = BaseETLSchema(**config_dict)
        except ValidationError as e:
            # Format Pydantic errors in a more user-friendly way
            error_messages = []
            for error in e.errors():
                loc = " -> ".join(str(x) for x in error["loc"])
                msg = error["msg"]
                error_messages.append(f"  - {loc}: {msg}")

            raise ConfigurationError(
                "Configuration validation failed:\n" + "\n".join(error_messages)
            ) from e

        # Convert to dictionary format (for backward compatibility)
        return config_model.to_dict()

    @staticmethod
    def load_as_model(config_path: Union[str, Path]) -> BaseETLSchema:
        """Load configuration and return as Pydantic model.

        Args:
            config_path: Path to configuration file

        Returns:
            BaseETLSchema model instance

        Raises:
            FileNotFoundError: When configuration file does not exist
            ConfigurationError: When configuration format is invalid
        """
        path = Path(config_path)

        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Load YAML
        with open(path, "r", encoding="utf-8") as f:
            try:
                config_dict = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ConfigurationError(f"YAML syntax error: {e}") from e

        if config_dict is None:
            raise ConfigurationError("Configuration file is empty")

        # Substitute environment variables
        config_dict = EnvVarSubstitution.substitute(config_dict)

        # Validate configuration structure using Pydantic
        try:
            return BaseETLSchema(**config_dict)
        except ValidationError as e:
            # Format Pydantic error messages
            error_messages = []
            for error in e.errors():
                loc = " -> ".join(str(x) for x in error["loc"])
                msg = error["msg"]
                error_messages.append(f"  - {loc}: {msg}")

            raise ConfigurationError(
                "Configuration validation failed:\n" + "\n".join(error_messages)
            ) from e
