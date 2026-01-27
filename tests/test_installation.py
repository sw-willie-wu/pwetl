"""Test pwetl installation and basic imports."""

import pytest


def test_import_pwetl():
    """Test that pwetl can be imported."""
    import pwetl
    assert hasattr(pwetl, '__version__')
    assert pwetl.__version__


def test_import_version():
    """Test that version can be imported."""
    from pwetl import __version__
    assert __version__
    assert isinstance(__version__, str)


def test_import_core_components():
    """Test that core components can be imported."""
    from pwetl import ETLEngine, Pipeline
    assert ETLEngine is not None
    assert Pipeline is not None


def test_import_config():
    """Test that ConfigLoader can be imported."""
    from pwetl.core.config import ConfigLoader
    assert ConfigLoader is not None


def test_import_file_source():
    """Test that FileSource can be imported."""
    from pwetl.sources.file import FileSource
    assert FileSource is not None


def test_import_file_sink():
    """Test that FileSink can be imported."""
    from pwetl.sinks.file import FileSink
    assert FileSink is not None


def test_import_transform_loader():
    """Test that TransformLoader can be imported."""
    from pwetl.utils.loader import TransformLoader
    assert TransformLoader is not None


def test_package_structure():
    """Test that package structure is correct."""
    import pwetl.core
    import pwetl.sources
    import pwetl.sinks
    import pwetl.utils

    assert pwetl.core is not None
    assert pwetl.sources is not None
    assert pwetl.sinks is not None
    assert pwetl.utils is not None
