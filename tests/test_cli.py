"""Tests for CLI."""

import pytest
from unittest.mock import patch
from pwetl import cli


class TestCLI:
    """Test CLI functions."""

    def test_cli_entry_point_missing_config(self):
        """Test CLI entry point without config."""
        with patch('sys.argv', ['pwetl']):
            with pytest.raises(SystemExit):
                cli.cli_entry_point()

    def test_cli_entry_point_version(self):
        """Test CLI version flag."""
        with patch('sys.argv', ['pwetl', '--version']):
            with pytest.raises(SystemExit) as exc_info:
                cli.cli_entry_point()
            assert exc_info.value.code == 0
