"""Test registry and factory classes."""

import pytest
from pathlib import Path
from pwetl.core.registry import SOURCE_REGISTRY, SINK_REGISTRY, SourceFactory, SinkFactory
from pwetl.core.exceptions import RegistryError
from pwetl.sources.base import BaseSource
from pwetl.sinks.base import BaseSink


class TestSourceFactory:
    """Test SourceFactory class."""

    def test_create_builtin_source(self):
        """Test creating built-in source."""
        config = {
            'name': 'test',
            'type': 'csv',
            'path': 'test.csv'
        }

        source = SourceFactory.create('test', config)
        assert source is not None
        assert isinstance(source, BaseSource)

    def test_create_missing_type(self):
        """Test creating source without type raises error."""
        config = {'name': 'test', 'path': 'test.csv'}

        with pytest.raises(RegistryError):
            SourceFactory.create('test', config)

    def test_create_unknown_type(self):
        """Test creating source with unknown type raises error."""
        config = {'name': 'test', 'type': 'unknown'}

        with pytest.raises(RegistryError):
            SourceFactory.create('test', config)

    def test_create_custom_source(self, tmp_path):
        """Test creating custom source."""
        # Create a custom source module
        custom_source = tmp_path / 'custom_source.py'
        custom_source.write_text(
            'from pwetl.sources.base import BaseSource\n'
            'import pathway as pw\n'
            '\n'
            'class CustomSource(BaseSource):\n'
            '    required_config = []\n'
            '    optional_config = {}\n'
            '\n'
            '    def read(self) -> pw.Table:\n'
            '        import pandas as pd\n'
            '        df = pd.DataFrame({"a": [1, 2, 3]})\n'
            '        return pw.debug.table_from_pandas(df)\n',
            encoding='utf-8'
        )

        # Add tmp_path to sys.path so module can be imported
        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            config = {
                'name': 'test',
                'type': 'custom',
                'module': 'custom_source.CustomSource'
            }

            source = SourceFactory.create('test', config)
            assert source is not None
            assert isinstance(source, BaseSource)
        finally:
            sys.path.remove(str(tmp_path))

    def test_create_custom_source_missing_module(self):
        """Test creating custom source without module raises error."""
        config = {
            'name': 'test',
            'type': 'custom',
            'class': 'CustomSource'
        }

        with pytest.raises(RegistryError):
            SourceFactory.create('test', config)

    def test_create_custom_source_invalid_format(self):
        """Test creating custom source with invalid module format raises error."""
        config = {
            'name': 'test',
            'type': 'custom',
            'module': 'custom_source'  # Missing .ClassName
        }

        with pytest.raises(RegistryError):
            SourceFactory.create('test', config)

    def test_create_custom_source_not_base_source(self, tmp_path):
        """Test creating custom source that doesn't inherit BaseSource raises error."""
        # Create a module with non-BaseSource class
        bad_source = tmp_path / 'bad_source.py'
        bad_source.write_text(
            'class NotASource:\n'
            '    pass\n',
            encoding='utf-8'
        )

        # Add tmp_path to sys.path so module can be imported
        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            config = {
                'name': 'test',
                'type': 'custom',
                'module': 'bad_source.NotASource'
            }

            with pytest.raises(TypeError, match="must inherit from BaseSource"):
                SourceFactory.create('test', config)
        finally:
            sys.path.remove(str(tmp_path))


class TestSinkFactory:
    """Test SinkFactory class."""

    def test_create_builtin_sink(self):
        """Test creating built-in sink."""
        config = {
            'name': 'test',
            'type': 'csv',
            'path': 'output.csv'
        }

        sink = SinkFactory.create('test', config)
        assert sink is not None
        assert isinstance(sink, BaseSink)

    def test_create_missing_type(self):
        """Test creating sink without type raises error."""
        config = {'name': 'test', 'path': 'output.csv'}

        with pytest.raises(RegistryError):
            SinkFactory.create('test', config)

    def test_create_unknown_type(self):
        """Test creating sink with unknown type raises error."""
        config = {'name': 'test', 'type': 'unknown'}

        with pytest.raises(RegistryError):
            SinkFactory.create('test', config)

    def test_create_custom_sink(self, tmp_path):
        """Test creating custom sink."""
        # Create a custom sink module
        custom_sink = tmp_path / 'custom_sink.py'
        custom_sink.write_text(
            'from pwetl.sinks.base import BaseSink\n'
            'import pathway as pw\n'
            '\n'
            'class CustomSink(BaseSink):\n'
            '    required_config = []\n'
            '    optional_config = {}\n'
            '\n'
            '    def write(self, table: pw.Table) -> None:\n'
            '        pass\n',
            encoding='utf-8'
        )

        # Add tmp_path to sys.path so module can be imported
        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            config = {
                'name': 'test',
                'type': 'custom',
                'module': 'custom_sink.CustomSink'
            }

            sink = SinkFactory.create('test', config)
            assert sink is not None
            assert isinstance(sink, BaseSink)
        finally:
            sys.path.remove(str(tmp_path))

    def test_create_custom_sink_missing_module(self):
        """Test creating custom sink without module raises error."""
        config = {
            'name': 'test',
            'type': 'custom',
            'class': 'CustomSink'
        }

        with pytest.raises(RegistryError):
            SinkFactory.create('test', config)

    def test_create_custom_sink_invalid_format(self):
        """Test creating custom sink with invalid module format raises error."""
        config = {
            'name': 'test',
            'type': 'custom',
            'module': 'custom_sink'  # Missing .ClassName
        }

        with pytest.raises(RegistryError):
            SinkFactory.create('test', config)

    def test_create_custom_sink_not_base_sink(self, tmp_path):
        """Test creating custom sink that doesn't inherit BaseSink raises error."""
        # Create a module with non-BaseSink class
        bad_sink = tmp_path / 'bad_sink.py'
        bad_sink.write_text(
            'class NotASink:\n'
            '    pass\n',
            encoding='utf-8'
        )

        # Add tmp_path to sys.path so module can be imported
        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            config = {
                'name': 'test',
                'type': 'custom',
                'module': 'bad_sink.NotASink'
            }

            with pytest.raises(TypeError, match="must inherit from BaseSink"):
                SinkFactory.create('test', config)
        finally:
            sys.path.remove(str(tmp_path))


class TestRegistry:
    """Test SOURCE_REGISTRY and SINK_REGISTRY."""

    def test_source_registry_not_empty(self):
        """Test that SOURCE_REGISTRY contains built-in sources."""
        assert len(SOURCE_REGISTRY) > 0
        assert 'csv' in SOURCE_REGISTRY
        assert 'json' in SOURCE_REGISTRY

    def test_sink_registry_not_empty(self):
        """Test that SINK_REGISTRY contains built-in sinks."""
        assert len(SINK_REGISTRY) > 0
        assert 'csv' in SINK_REGISTRY
        assert 'json' in SINK_REGISTRY

    def test_registered_sources_are_base_source(self):
        """Test that all registered sources inherit from BaseSource."""
        for source_type, source_class in SOURCE_REGISTRY.items():
            assert issubclass(source_class, BaseSource), \
                f"{source_type} should be a subclass of BaseSource"

    def test_registered_sinks_are_base_sink(self):
        """Test that all registered sinks inherit from BaseSink."""
        for sink_type, sink_class in SINK_REGISTRY.items():
            assert issubclass(sink_class, BaseSink), \
                f"{sink_type} should be a subclass of BaseSink"
