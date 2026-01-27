"""pwetl - A flexible ETL framework based on Pathway.

Just write transforms and config YAML to build your ETL service.
"""

__version__ = '0.1.0'

# 核心類別
from pwetl.core.engine import ETLEngine
from pwetl.core.pipeline import Pipeline
from pwetl.core.config import ConfigLoader
from pwetl.core.registry import (
    SOURCE_REGISTRY,
    SINK_REGISTRY,
    SourceFactory,
    SinkFactory,
)

# Base 類別
from pwetl.sources.base import BaseSource
from pwetl.sinks.base import BaseSink
from pwetl.transforms.base import BaseTransform

# 內建 Sources
from pwetl.sources.file import FileSource
from pwetl.sources.api import APISource
from pwetl.sources.database import DatabaseSource

# 內建 Sinks
from pwetl.sinks.file import FileSink
from pwetl.sinks.database import DatabaseSink
from pwetl.sinks.api import APISink

# 工具
from pwetl.utils.env import EnvVarSubstitution, load_env_file
from pwetl.utils.loader import DynamicLoader, TransformLoader
from pwetl.utils.schema import SchemaParser

# 註冊內建 Sources 和 Sinks（避免循環引用）
from pwetl.sources import _register_sources
from pwetl.sinks import _register_sinks

_register_sources()
_register_sinks()

__all__ = [
    # 版本
    '__version__',

    # 核心
    'ETLEngine',
    'Pipeline',
    'ConfigLoader',
    'SOURCE_REGISTRY',
    'SINK_REGISTRY',
    'SourceFactory',
    'SinkFactory',

    # Base 類別
    'BaseSource',
    'BaseSink',
    'BaseTransform',

    # 內建 Sources
    'FileSource',
    'APISource',
    'DatabaseSource',

    # 內建 Sinks
    'FileSink',
    'DatabaseSink',
    'APISink',

    # 工具
    'EnvVarSubstitution',
    'load_env_file',
    'DynamicLoader',
    'TransformLoader',
    'SchemaParser',
]
