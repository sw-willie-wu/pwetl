"""Test dynamic loader utilities."""

import pytest
from pathlib import Path
from pwetl.utils.loader import DynamicLoader, TransformLoader
from pwetl.transforms import BaseTransform


class TestDynamicLoader:
    """Test DynamicLoader class."""

    def test_load_from_package(self):
        """Test loading class from package."""
        # Load a known class from pwetl
        cls = DynamicLoader.load_class('pwetl.sources.file', 'FileSource')
        assert cls is not None
        assert cls.__name__ == 'FileSource'

    def test_load_from_file(self, tmp_path):
        """Test loading class from file."""
        # Create a test module file
        test_module = tmp_path / 'test_module.py'
        test_module.write_text(
            'class TestClass:\n'
            '    pass\n',
            encoding='utf-8'
        )

        # Load the class
        cls = DynamicLoader.load_class(str(test_module), 'TestClass')
        assert cls is not None
        assert cls.__name__ == 'TestClass'

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from nonexistent file raises error."""
        nonexistent = tmp_path / 'nonexistent.py'

        with pytest.raises(ImportError, match="檔案不存在"):
            DynamicLoader.load_class(str(nonexistent), 'SomeClass')

    def test_load_nonexistent_class_from_file(self, tmp_path):
        """Test loading nonexistent class from file raises error."""
        test_module = tmp_path / 'test_module.py'
        test_module.write_text('# Empty module\n', encoding='utf-8')

        with pytest.raises(ImportError, match="找不到類別"):
            DynamicLoader.load_class(str(test_module), 'NonexistentClass')

    def test_load_nonexistent_package(self):
        """Test loading from nonexistent package raises error."""
        with pytest.raises(ImportError, match="找不到模組"):
            DynamicLoader.load_class('nonexistent.package', 'SomeClass')

    def test_load_nonexistent_class_from_package(self):
        """Test loading nonexistent class from package raises error."""
        with pytest.raises(ImportError, match="找不到類別"):
            DynamicLoader.load_class('pwetl.sources', 'NonexistentSource')


class TestTransformLoader:
    """Test TransformLoader class."""

    def test_load_valid_transform(self, tmp_path):
        """Test loading valid transform."""
        # Create a test transform module
        transform_module = tmp_path / 'test_transform.py'
        transform_module.write_text(
            'from pwetl.transforms import BaseTransform\n'
            '\n'
            'class MyTransform(BaseTransform):\n'
            '    def transform(self, tables):\n'
            '        return tables\n',
            encoding='utf-8'
        )

        # Load the transform
        transform_config = f'{transform_module}.MyTransform'
        transform = TransformLoader.load(transform_config)

        assert transform is not None
        assert isinstance(transform, BaseTransform)

    def test_load_invalid_format(self):
        """Test loading with invalid format raises error."""
        with pytest.raises(ValueError, match="Transform 配置格式錯誤"):
            TransformLoader.load('InvalidFormat')

    def test_load_non_transform_class(self, tmp_path):
        """Test loading non-BaseTransform class raises error."""
        # Create a module with non-transform class
        module = tmp_path / 'bad_transform.py'
        module.write_text(
            'class NotATransform:\n'
            '    pass\n',
            encoding='utf-8'
        )

        transform_config = f'{module}.NotATransform'

        with pytest.raises(TypeError, match="必須繼承自 BaseTransform"):
            TransformLoader.load(transform_config)

    def test_load_nonexistent_transform(self):
        """Test loading nonexistent transform raises error."""
        with pytest.raises(ImportError):
            TransformLoader.load('nonexistent.module.Transform')
