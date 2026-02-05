"""Environment variable substitution utility."""
import os
import re
from pathlib import Path
from typing import Any, Union


class EnvVarSubstitution:
    """Environment variable substitution utility.

    Supports two syntaxes:
    - ${VAR_NAME}: Required environment variable
    - ${VAR_NAME:default}: Environment variable with default value
    """

    ENV_VAR_PATTERN = re.compile(r'\$\{([^}:]+)(?::([^}]*))?\}')

    @classmethod
    def substitute(cls, value: Any) -> Any:
        """Recursively substitute environment variables.

        Args:
            value: Value to process, can be str, dict, list, or other types

        Returns:
            Substituted value

        Raises:
            ValueError: When required environment variable does not exist
        """
        if isinstance(value, str):
            return cls._substitute_string(value)
        if isinstance(value, dict):
            return {k: cls.substitute(v) for k, v in value.items()}
        if isinstance(value, list):
            return [cls.substitute(item) for item in value]
        return value

    @classmethod
    def _substitute_string(cls, value: str) -> str:
        """Substitute environment variables in string.

        Args:
            value: String to process

        Returns:
            Substituted string

        Raises:
            ValueError: When required environment variable does not exist
        """
        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(2)

            env_value = os.getenv(var_name)

            if env_value is None:
                if default_value is not None:
                    return default_value
                raise ValueError(
                    f"Environment variable '{var_name}' does not exist and has no default value"
                )

            return env_value

        return cls.ENV_VAR_PATTERN.sub(replace_var, value)


def load_env_file(env_file: Union[str, Path] = '.env') -> None:
    """Load .env file.

    Args:
        env_file: Path to .env file, defaults to .env in current directory
    """
    env_path = Path(env_file)

    if not env_path.exists():
        return

    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Parse KEY=VALUE format
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                # Only set if environment variable doesn't exist
                if key not in os.environ:
                    os.environ[key] = value
