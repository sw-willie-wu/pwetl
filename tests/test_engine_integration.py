"""Integration tests for ETLEngine."""

import pytest
import tempfile
from pathlib import Path
from pwetl.core.engine import ETLEngine


class TestETLEngineIntegration:
    """Integration tests for ETLEngine."""

    def test_engine_run_basic_csv(self, tmp_path):
        """Test engine running basic CSV ETL."""
        # Create input CSV
        input_file = tmp_path / "input.csv"
        input_file.write_text("user_id,value\n1,10\n2,20\n3,30\n")

        # Create transform module
        transform_file = tmp_path / "transform.py"
        transform_file.write_text("""
import pathway as pw
from pwetl.transforms.base import BaseTransform

class SimpleTransform(BaseTransform):
    def transform(self, tables):
        if 'input' in tables:
            table = tables['input']
            result = table.select(*pw.this, doubled=pw.this.value * 2)
            return {'output': result}
        return tables
""")

        # Create config file
        config_file = tmp_path / "config.yaml"
        config_content = f"""
sources:
  - name: input
    type: csv
    path: {input_file}
    schema:
      user_id: int
      value: int

transform: transform.SimpleTransform

sinks:
  - name: output
    type: file
    path: {tmp_path / "output.csv"}
    format: csv
"""
        config_file.write_text(config_content)

        # Run engine
        engine = ETLEngine(config_path=config_file, verbose=False)
        engine.execute()

        # Verify output
        output_file = tmp_path / "output.csv"
        assert output_file.exists()
        content = output_file.read_text()
        assert 'user_id' in content
        assert 'value' in content
        assert 'doubled' in content

    def test_engine_run_with_env_vars(self, tmp_path):
        """Test engine with environment variables."""
        import os
        import sys
        import importlib

        # Create transform module FIRST
        transform_file = tmp_path / "transform.py"
        transform_file.write_text("""
from pwetl.transforms.base import BaseTransform

class PassThroughTransform(BaseTransform):
    def transform(self, tables):
        # Return with sink name as key
        if 'input' in tables:
            return {'output': tables['input']}
        return tables
""")

        # Add tmp_path to sys.path so transform can be imported
        sys.path.insert(0, str(tmp_path))

        # Clear any cached import
        if 'transform' in sys.modules:
            del sys.modules['transform']

        try:
            # Set environment variables
            os.environ["INPUT_PATH"] = str(tmp_path / "input.csv")
            os.environ["OUTPUT_PATH"] = str(tmp_path / "output.csv")

            # Create input CSV
            input_file = tmp_path / "input.csv"
            input_file.write_text("name,age\\nBob,25\\n")

            # Create config file with environment variables
            config_file = tmp_path / "config.yaml"
            config_content = """
sources:
  - name: input
    type: csv
    path: ${INPUT_PATH}
    schema:
      name: str
      age: int

transform: transform.PassThroughTransform

sinks:
  - name: output
    type: file
    path: ${OUTPUT_PATH}
    format: csv
"""
            config_file.write_text(config_content)

            # Run engine
            engine = ETLEngine(config_path=config_file, verbose=False)
            engine.execute()

            # Verify output
            output_file = tmp_path / "output.csv"
            assert output_file.exists()
        finally:
            # Clean up sys.path
            sys.path.remove(str(tmp_path))

    @pytest.mark.skip(reason="Verbose output is via logging, not captured by capsys")
    def test_engine_run_verbose_mode(self, tmp_path, capsys):
        """Test engine verbose mode."""
        import sys

        # Create transform module FIRST
        transform_file = tmp_path / "transform.py"
        transform_file.write_text("""
from pwetl.transforms.base import BaseTransform

class PassThroughTransform(BaseTransform):
    def transform(self, tables):
        # Return with sink name as key
        if 'input' in tables:
            return {'output': tables['input']}
        return tables
""")

        # Add tmp_path to sys.path so transform can be imported
        sys.path.insert(0, str(tmp_path))

        # Clear any cached import
        if 'transform' in sys.modules:
            del sys.modules['transform']

        try:
            # Create input CSV
            input_file = tmp_path / "input.csv"
            input_file.write_text("name,score\nAlice,90\n")

            # Create config file
            config_file = tmp_path / "config.yaml"
            config_content = f"""
sources:
  - name: input
    type: csv
    path: {input_file}
    schema:
      name: str
      score: int

transform: transform.PassThroughTransform

sinks:
  - name: output
    type: file
    path: {tmp_path / "output.csv"}
    format: csv
"""
            config_file.write_text(config_content)

            # Run engine with verbose=True
            engine = ETLEngine(config_path=config_file, verbose=True)
            engine.execute()

            # Check verbose output
            captured = capsys.readouterr()
            assert '載入配置' in captured.out or '載入環境變數' in captured.out
        finally:
            # Clean up sys.path
            sys.path.remove(str(tmp_path))

    def test_engine_invalid_config(self, tmp_path):
        """Test engine with invalid config raises ConfigurationError."""
        from pwetl.core.exceptions import ConfigurationError

        # Create invalid config (missing required fields)
        config_file = tmp_path / "invalid_config.yaml"
        config_content = """
sources: []
"""
        config_file.write_text(config_content)

        # Engine should raise ConfigurationError
        with pytest.raises(ConfigurationError):
            engine = ETLEngine(config_path=config_file, verbose=False)
            engine.execute()

    def test_engine_bad_sink_config_raises_configuration_error(self, tmp_path):
        """Test that bad sink config raises ConfigurationError."""
        import sys
        from pwetl.core.exceptions import ConfigurationError

        transform_file = tmp_path / "transform.py"
        transform_file.write_text("""
from pwetl.transforms.base import BaseTransform

class T(BaseTransform):
    def transform(self, tables):
        return {'out': tables['input']}
""")
        sys.path.insert(0, str(tmp_path))
        if 'transform' in sys.modules:
            del sys.modules['transform']

        try:
            input_file = tmp_path / "input.csv"
            input_file.write_text("id,val\n1,10\n")

            config_file = tmp_path / "config.yaml"
            # Database sink missing required 'table' config
            config_file.write_text(f"""
sources:
  - name: input
    type: csv
    path: {input_file}
    schema:
      id: int
      val: int

transform: transform.T

sinks:
  - name: out
    type: database
    dsn: sqlite://
""")

            with pytest.raises(ConfigurationError, match="Sink 'out'"):
                engine = ETLEngine(config_path=config_file, verbose=False)
                engine.execute()
        finally:
            sys.path.remove(str(tmp_path))

    def test_engine_nonexistent_config(self):
        """Test engine with nonexistent config file."""
        from pwetl.core.exceptions import ConfigurationError

        with pytest.raises((FileNotFoundError, ConfigurationError)):
            engine = ETLEngine(config_path=Path("/nonexistent/config.yaml"), verbose=False)
            engine.execute()

    def test_engine_multiple_sources_sinks(self, tmp_path):
        """Test engine with multiple sources and sinks."""
        import sys

        # Create transform module FIRST
        transform_file = tmp_path / "transform.py"
        transform_file.write_text("""
import pathway as pw
from pwetl.transforms.base import BaseTransform

class MultiSourceTransform(BaseTransform):
    def transform(self, tables):
        # Return with sink names as keys
        result = {}
        if 'source1' in tables:
            result['output1'] = tables['source1']
        if 'source2' in tables:
            result['output2'] = tables['source2']
        return result
""")

        # Add tmp_path to sys.path so transform can be imported
        sys.path.insert(0, str(tmp_path))

        # Clear any cached import
        if 'transform' in sys.modules:
            del sys.modules['transform']

        try:
            # Create two input CSVs
            input1 = tmp_path / "input1.csv"
            input1.write_text("user_id,value\\n1,100\\n")

            input2 = tmp_path / "input2.csv"
            input2.write_text("user_id,value\\n2,200\\n")

            # Create config file
            config_file = tmp_path / "config.yaml"
            config_content = f"""
sources:
  - name: source1
    type: csv
    path: {input1}
    schema:
      user_id: int
      value: int

  - name: source2
    type: csv
    path: {input2}
    schema:
      user_id: int
      value: int

transform: transform.MultiSourceTransform

sinks:
  - name: output1
    type: file
    path: {tmp_path / "output1.csv"}
    format: csv

  - name: output2
    type: file
    path: {tmp_path / "output2.csv"}
    format: csv
"""
            config_file.write_text(config_content)

            # Run engine
            engine = ETLEngine(config_path=config_file, verbose=False)
            engine.execute()

            # Verify both outputs exist
            assert (tmp_path / "output1.csv").exists()
            assert (tmp_path / "output2.csv").exists()
        finally:
            # Clean up sys.path
            sys.path.remove(str(tmp_path))
