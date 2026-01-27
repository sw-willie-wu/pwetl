"""Test configuration loader."""

import pytest
import yaml
from pathlib import Path
from pwetl.core.config import ConfigLoader


class TestConfigLoader:
    """Test ConfigLoader class."""

    def test_load_valid_config(self, tmp_path):
        """Test loading valid configuration."""
        config_file = tmp_path / 'config.yaml'
        config_file.write_text(
            'sources:\n'
            '  - name: data\n'
            '    type: csv\n'
            '    path: input.csv\n'
            '\n'
            'transform: transform.MyTransform\n'
            '\n'
            'sinks:\n'
            '  - name: output\n'
            '    type: csv\n'
            '    path: output.csv\n',
            encoding='utf-8'
        )

        config = ConfigLoader.load(config_file)

        assert 'sources' in config
        assert 'transform' in config
        assert 'sinks' in config
        assert len(config['sources']) == 1
        assert config['sources'][0]['name'] == 'data'

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading nonexistent file raises error."""
        nonexistent = tmp_path / 'nonexistent.yaml'

        with pytest.raises(FileNotFoundError):
            ConfigLoader.load(nonexistent)

    def test_load_empty_file(self, tmp_path):
        """Test loading empty file raises error."""
        config_file = tmp_path / 'empty.yaml'
        config_file.write_text('', encoding='utf-8')

        with pytest.raises(ValueError, match="配置檔案是空的"):
            ConfigLoader.load(config_file)

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML raises error."""
        config_file = tmp_path / 'invalid.yaml'
        config_file.write_text('invalid: yaml: syntax:', encoding='utf-8')

        with pytest.raises(ValueError, match="YAML 語法錯誤"):
            ConfigLoader.load(config_file)

    def test_validate_missing_sources(self, tmp_path):
        """Test validation fails when sources missing."""
        config_file = tmp_path / 'config.yaml'
        config_file.write_text(
            'transform: transform.MyTransform\n'
            'sinks:\n'
            '  - name: output\n'
            '    type: csv\n',
            encoding='utf-8'
        )

        with pytest.raises(ValueError, match="配置缺少 'sources' 欄位"):
            ConfigLoader.load(config_file)

    def test_validate_missing_transform(self, tmp_path):
        """Test validation fails when transform missing."""
        config_file = tmp_path / 'config.yaml'
        config_file.write_text(
            'sources:\n'
            '  - name: data\n'
            '    type: csv\n'
            'sinks:\n'
            '  - name: output\n'
            '    type: csv\n',
            encoding='utf-8'
        )

        with pytest.raises(ValueError, match="配置缺少 'transform' 欄位"):
            ConfigLoader.load(config_file)

    def test_validate_missing_sinks(self, tmp_path):
        """Test validation fails when sinks missing."""
        config_file = tmp_path / 'config.yaml'
        config_file.write_text(
            'sources:\n'
            '  - name: data\n'
            '    type: csv\n'
            'transform: transform.MyTransform\n',
            encoding='utf-8'
        )

        with pytest.raises(ValueError, match="配置缺少 'sinks' 欄位"):
            ConfigLoader.load(config_file)

    def test_validate_empty_sources(self, tmp_path):
        """Test validation fails when sources empty."""
        config_file = tmp_path / 'config.yaml'
        config_file.write_text(
            'sources: []\n'
            'transform: transform.MyTransform\n'
            'sinks:\n'
            '  - name: output\n'
            '    type: csv\n',
            encoding='utf-8'
        )

        with pytest.raises(ValueError, match="'sources' 不能為空"):
            ConfigLoader.load(config_file)

    def test_validate_source_missing_name(self, tmp_path):
        """Test validation fails when source missing name."""
        config_file = tmp_path / 'config.yaml'
        config_file.write_text(
            'sources:\n'
            '  - type: csv\n'
            '    path: input.csv\n'
            'transform: transform.MyTransform\n'
            'sinks:\n'
            '  - name: output\n'
            '    type: csv\n',
            encoding='utf-8'
        )

        with pytest.raises(ValueError, match="缺少 'name' 欄位"):
            ConfigLoader.load(config_file)

    def test_validate_source_missing_type(self, tmp_path):
        """Test validation fails when source missing type."""
        config_file = tmp_path / 'config.yaml'
        config_file.write_text(
            'sources:\n'
            '  - name: data\n'
            '    path: input.csv\n'
            'transform: transform.MyTransform\n'
            'sinks:\n'
            '  - name: output\n'
            '    type: csv\n',
            encoding='utf-8'
        )

        with pytest.raises(ValueError, match="缺少 'type' 欄位"):
            ConfigLoader.load(config_file)

    def test_validate_duplicate_source_names(self, tmp_path):
        """Test validation fails when source names duplicate."""
        config_file = tmp_path / 'config.yaml'
        config_file.write_text(
            'sources:\n'
            '  - name: data\n'
            '    type: csv\n'
            '  - name: data\n'
            '    type: json\n'
            'transform: transform.MyTransform\n'
            'sinks:\n'
            '  - name: output\n'
            '    type: csv\n',
            encoding='utf-8'
        )

        with pytest.raises(ValueError, match="Source name 重複"):
            ConfigLoader.load(config_file)

    def test_validate_invalid_transform_format(self, tmp_path):
        """Test validation fails when transform format invalid."""
        config_file = tmp_path / 'config.yaml'
        config_file.write_text(
            'sources:\n'
            '  - name: data\n'
            '    type: csv\n'
            'transform: InvalidFormat\n'
            'sinks:\n'
            '  - name: output\n'
            '    type: csv\n',
            encoding='utf-8'
        )

        with pytest.raises(ValueError, match="'transform' 格式錯誤"):
            ConfigLoader.load(config_file)

    def test_env_var_substitution(self, tmp_path):
        """Test environment variable substitution in config."""
        import os
        os.environ['TEST_INPUT_PATH'] = 'input.csv'
        os.environ['TEST_OUTPUT_PATH'] = 'output.csv'

        config_file = tmp_path / 'config.yaml'
        config_file.write_text(
            'sources:\n'
            '  - name: data\n'
            '    type: csv\n'
            '    path: ${TEST_INPUT_PATH}\n'
            'transform: transform.MyTransform\n'
            'sinks:\n'
            '  - name: output\n'
            '    type: csv\n'
            '    path: ${TEST_OUTPUT_PATH}\n',
            encoding='utf-8'
        )

        config = ConfigLoader.load(config_file)

        assert config['sources'][0]['path'] == 'input.csv'
        assert config['sinks'][0]['path'] == 'output.csv'
