"""Test environment variable substitution utilities."""

import os
import pytest
from pathlib import Path
from pwetl.utils.env import EnvVarSubstitution, load_env_file


class TestEnvVarSubstitution:
    """Test EnvVarSubstitution class."""

    def test_substitute_simple_string(self):
        """Test substituting a simple environment variable."""
        os.environ['TEST_VAR'] = 'test_value'
        result = EnvVarSubstitution.substitute('${TEST_VAR}')
        assert result == 'test_value'

    def test_substitute_with_default(self):
        """Test substituting with default value."""
        # Variable doesn't exist, should use default
        if 'NONEXISTENT_VAR' in os.environ:
            del os.environ['NONEXISTENT_VAR']
        result = EnvVarSubstitution.substitute('${NONEXISTENT_VAR:default_value}')
        assert result == 'default_value'

    def test_substitute_missing_required_var(self):
        """Test that missing required variable raises error."""
        if 'REQUIRED_VAR' in os.environ:
            del os.environ['REQUIRED_VAR']
        with pytest.raises(ValueError, match="Environment variable 'REQUIRED_VAR' does not exist and has no default value"):
            EnvVarSubstitution.substitute('${REQUIRED_VAR}')

    def test_substitute_in_string(self):
        """Test substituting variable within a string."""
        os.environ['HOST'] = 'localhost'
        os.environ['PORT'] = '5432'
        result = EnvVarSubstitution.substitute('postgresql://${HOST}:${PORT}/db')
        assert result == 'postgresql://localhost:5432/db'

    def test_substitute_dict(self):
        """Test substituting variables in a dictionary."""
        os.environ['DB_HOST'] = 'localhost'
        os.environ['DB_PORT'] = '5432'

        config = {
            'host': '${DB_HOST}',
            'port': '${DB_PORT}',
            'database': 'mydb'
        }

        result = EnvVarSubstitution.substitute(config)
        assert result == {
            'host': 'localhost',
            'port': '5432',
            'database': 'mydb'
        }

    def test_substitute_list(self):
        """Test substituting variables in a list."""
        os.environ['VAR1'] = 'value1'
        os.environ['VAR2'] = 'value2'

        items = ['${VAR1}', '${VAR2}', 'static_value']
        result = EnvVarSubstitution.substitute(items)
        assert result == ['value1', 'value2', 'static_value']

    def test_substitute_nested_structure(self):
        """Test substituting variables in nested dict/list structure."""
        os.environ['API_KEY'] = 'secret123'
        os.environ['API_URL'] = 'https://api.example.com'

        config = {
            'sources': [
                {
                    'type': 'api',
                    'url': '${API_URL}',
                    'headers': {
                        'Authorization': 'Bearer ${API_KEY}'
                    }
                }
            ]
        }

        result = EnvVarSubstitution.substitute(config)
        assert result['sources'][0]['url'] == 'https://api.example.com'
        assert result['sources'][0]['headers']['Authorization'] == 'Bearer secret123'

    def test_substitute_non_string_values(self):
        """Test that non-string values are returned unchanged."""
        assert EnvVarSubstitution.substitute(123) == 123
        assert EnvVarSubstitution.substitute(45.67) == 45.67
        assert EnvVarSubstitution.substitute(True) is True
        assert EnvVarSubstitution.substitute(None) is None

    def test_substitute_empty_default(self):
        """Test substituting with empty default value."""
        if 'EMPTY_VAR' in os.environ:
            del os.environ['EMPTY_VAR']
        result = EnvVarSubstitution.substitute('${EMPTY_VAR:}')
        assert result == ''


class TestLoadEnvFile:
    """Test load_env_file function."""

    def test_load_env_file(self, tmp_path):
        """Test loading .env file."""
        env_file = tmp_path / '.env'
        env_file.write_text(
            'TEST_KEY1=value1\n'
            'TEST_KEY2="value2"\n'
            "TEST_KEY3='value3'\n"
            '# Comment line\n'
            '\n'
            'TEST_KEY4=value4\n',
            encoding='utf-8'
        )

        load_env_file(env_file)

        assert os.environ['TEST_KEY1'] == 'value1'
        assert os.environ['TEST_KEY2'] == 'value2'
        assert os.environ['TEST_KEY3'] == 'value3'
        assert os.environ['TEST_KEY4'] == 'value4'

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading nonexistent file doesn't raise error."""
        nonexistent = tmp_path / 'nonexistent.env'
        load_env_file(nonexistent)  # Should not raise

    def test_env_file_doesnt_override_existing(self, tmp_path):
        """Test that .env file doesn't override existing environment variables."""
        os.environ['EXISTING_VAR'] = 'original_value'

        env_file = tmp_path / '.env'
        env_file.write_text('EXISTING_VAR=new_value\n', encoding='utf-8')

        load_env_file(env_file)

        # Should keep original value
        assert os.environ['EXISTING_VAR'] == 'original_value'
