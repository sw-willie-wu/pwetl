"""pwetl - A flexible ETL framework based on Pathway.

Just write transforms and config YAML to build your ETL service.
"""

__version__ = '0.1.0'

# Core classes
from pwetl.core.engine import ETLEngine
from pwetl.core.pipeline import Pipeline
from pwetl.core.config import ConfigLoader
from pwetl.core.registry import (
    SOURCE_REGISTRY,
    SINK_REGISTRY,
    SourceFactory,
    SinkFactory,
)

# Base classes
from pwetl.sources.base import BaseSource
from pwetl.sinks.base import BaseSink
from pwetl.transforms.base import BaseTransform

# Built-in Sources
from pwetl.sources.file import FileSource
from pwetl.sources.api import APISource
from pwetl.sources.database import DatabaseSource

# Built-in Sinks
from pwetl.sinks.file import FileSink
from pwetl.sinks.database import DatabaseSink
from pwetl.sinks.api import APISink

# Utilities
from pwetl.utils.env import EnvVarSubstitution, load_env_file
from pwetl.utils.loader import DynamicLoader, TransformLoader
from pwetl.utils.schema import SchemaParser

# Exceptions
from pwetl.core.exceptions import (
    PWETLError,
    ConfigurationError,
    ValidationError,
    SchemaError,
    SourceError,
    SinkError,
    TransformError,
    RegistryError,
    LoaderError,
)

# Register built-in Sources and Sinks (avoid circular imports)
from pwetl.sources import _register_sources
from pwetl.sinks import _register_sinks

_register_sources()
_register_sinks()

__all__ = [
    # Version
    '__version__',

    # Core
    'ETLEngine',
    'Pipeline',
    'ConfigLoader',
    'SOURCE_REGISTRY',
    'SINK_REGISTRY',
    'SourceFactory',
    'SinkFactory',

    # Base classes
    'BaseSource',
    'BaseSink',
    'BaseTransform',

    # Built-in Sources
    'FileSource',
    'APISource',
    'DatabaseSource',

    # Built-in Sinks
    'FileSink',
    'DatabaseSink',
    'APISink',

    # Utilities
    'EnvVarSubstitution',
    'load_env_file',
    'DynamicLoader',
    'TransformLoader',
    'SchemaParser',

    # Exceptions
    'PWETLError',
    'ConfigurationError',
    'ValidationError',
    'SchemaError',
    'SourceError',
    'SinkError',
    'TransformError',
    'RegistryError',
    'LoaderError',
]
