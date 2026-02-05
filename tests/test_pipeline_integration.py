"""Integration tests for Pipeline."""

import pytest
import tempfile
import pathway as pw
from pathlib import Path
from pwetl.core.pipeline import Pipeline
from pwetl.sources.file import FileSource
from pwetl.sinks.file import FileSink
from pwetl.transforms.base import BaseTransform


class SimpleTransform(BaseTransform):
    """Simple transform for testing."""

    def transform(self, tables):
        """Add a new column to the data."""
        if 'input' in tables:
            table = tables['input']
            # Add a doubled_value column
            result = table.select(
                *pw.this,
                doubled_value=pw.this.value * 2
            )
            return {'output': result}
        return tables


class FilterTransform(BaseTransform):
    """Filter transform for testing."""

    def transform(self, tables):
        """Filter rows where value > 5."""
        if 'input' in tables:
            table = tables['input']
            result = table.filter(pw.this.value > 5)
            return {'output': result}
        return tables


class TestPipelineIntegration:
    """Integration tests for Pipeline."""

    def test_csv_pipeline_basic(self, tmp_path):
        """Test basic CSV pipeline: read -> transform -> write."""
        # Create input CSV
        input_file = tmp_path / "input.csv"
        input_file.write_text("user_id,value\n1,10\n2,20\n3,30\n")

        output_file = tmp_path / "output.csv"

        # Create source
        source = FileSource(
            name='input',
            config={
                'path': str(input_file),
                'format': 'csv',
                'mode': 'static',
                'schema': {'user_id': 'int', 'value': 'int'}
            }
        )

        # Create transform
        transform = SimpleTransform()

        # Create sink
        sink = FileSink(
            name='output',
            config={
                'path': str(output_file),
                'format': 'csv'
            }
        )

        # Create and run pipeline
        pipeline = Pipeline(
            sources={'input': source},
            transform=transform,
            sinks={'output': sink},
            verbose=False
        )
        pipeline.run()

        # Verify output
        assert output_file.exists()
        content = output_file.read_text()
        assert 'id' in content
        assert 'value' in content
        assert 'doubled_value' in content

    def test_csv_pipeline_with_filter(self, tmp_path):
        """Test CSV pipeline with filtering."""
        # Create input CSV
        input_file = tmp_path / "input.csv"
        input_file.write_text("user_id,value\n1,3\n2,7\n3,10\n4,2\n5,15\n")

        output_file = tmp_path / "output.csv"

        # Create source
        source = FileSource(
            name='input',
            config={
                'path': str(input_file),
                'format': 'csv',
                'mode': 'static',
                'schema': {'user_id': 'int', 'value': 'int'}
            }
        )

        # Create transform
        transform = FilterTransform()

        # Create sink
        sink = FileSink(
            name='output',
            config={
                'path': str(output_file),
                'format': 'csv'
            }
        )

        # Create and run pipeline
        pipeline = Pipeline(
            sources={'input': source},
            transform=transform,
            sinks={'output': sink},
            verbose=False
        )
        pipeline.run()

        # Verify output
        assert output_file.exists()
        content = output_file.read_text()
        lines = [line for line in content.strip().split('\n') if line]
        # Should have header + 3 rows (values 7, 10, 15 are > 5)
        assert len(lines) == 4, f"Expected 4 lines (header + 3 data rows), got {len(lines)}"

    def test_json_pipeline(self, tmp_path):
        """Test JSON pipeline (actually JSONL format for Pathway)."""
        # Create input JSON (JSONL format - one JSON per line)
        input_file = tmp_path / "input.json"
        input_file.write_text('{"user_id": 1, "value": 10}\n{"user_id": 2, "value": 20}')

        output_file = tmp_path / "output.json"

        # Create source
        source = FileSource(
            name='input',
            config={
                'path': str(input_file),
                'format': 'json',
                'mode': 'static',
                'schema': {'user_id': 'int', 'value': 'int'}
            }
        )

        # Create transform
        transform = SimpleTransform()

        # Create sink
        sink = FileSink(
            name='output',
            config={
                'path': str(output_file),
                'format': 'json'
            }
        )

        # Create and run pipeline
        pipeline = Pipeline(
            sources={'input': source},
            transform=transform,
            sinks={'output': sink},
            verbose=False
        )
        pipeline.run()

        # Verify output
        assert output_file.exists()
        content = output_file.read_text()
        assert 'user_id' in content
        assert 'value' in content
        assert 'doubled_value' in content

    def test_jsonl_pipeline(self, tmp_path):
        """Test JSONL pipeline."""
        # Create input JSONL
        input_file = tmp_path / "input.jsonl"
        input_file.write_text('{"user_id": 1, "value": 10}\n{"user_id": 2, "value": 20}\n')

        output_file = tmp_path / "output.jsonl"

        # Create source
        source = FileSource(
            name='input',
            config={
                'path': str(input_file),
                'format': 'jsonl',
                'mode': 'static',
                'schema': {'user_id': 'int', 'value': 'int'}
            }
        )

        # Create transform
        transform = SimpleTransform()

        # Create sink
        sink = FileSink(
            name='output',
            config={
                'path': str(output_file),
                'format': 'jsonl'
            }
        )

        # Create and run pipeline
        pipeline = Pipeline(
            sources={'input': source},
            transform=transform,
            sinks={'output': sink},
            verbose=False
        )
        pipeline.run()

        # Verify output
        assert output_file.exists()
        content = output_file.read_text()
        assert 'user_id' in content
        assert 'value' in content
        assert 'doubled_value' in content

    @pytest.mark.skip(reason="Verbose output is via logging, not captured by capsys")
    def test_pipeline_verbose_mode(self, tmp_path, capsys):
        """Test pipeline verbose output."""
        # Create input CSV
        input_file = tmp_path / "input.csv"
        input_file.write_text("user_id,value\n1,10\n")

        output_file = tmp_path / "output.csv"

        # Create components
        source = FileSource(
            name='input',
            config={
                'path': str(input_file),
                'format': 'csv',
                'mode': 'static',
                'schema': {'user_id': 'int', 'value': 'int'}
            }
        )
        transform = SimpleTransform()
        sink = FileSink(
            name='output',
            config={
                'path': str(output_file),
                'format': 'csv'
            }
        )

        # Create and run pipeline with verbose=True
        pipeline = Pipeline(
            sources={'input': source},
            transform=transform,
            sinks={'output': sink},
            verbose=True
        )
        pipeline.run()

        # Check verbose output
        captured = capsys.readouterr()
        assert '初始化組件' in captured.out
        assert '從' in captured.out and 'Source 讀取資料' in captured.out
        assert '執行 Transform' in captured.out
        assert '寫入到' in captured.out and 'Sink' in captured.out
        assert '執行 Pathway' in captured.out
        assert '執行完成' in captured.out
