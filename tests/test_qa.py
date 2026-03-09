"""QA agent tests: log output, bad config rejection, and error propagation."""

import logging
import pytest
from unittest.mock import MagicMock, patch

from pwetl.core.pipeline import Pipeline
from pwetl.core.config import ConfigLoader
from pwetl.core.exceptions import (
    ConfigurationError,
    RegistryError,
    SourceError,
    SinkError,
    TransformError,
)
from pwetl.core.registry import SourceFactory, SinkFactory


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_pipeline(source_names=("input",), sink_names=("output",)):
    """Create a Pipeline with MagicMock components for log/error testing."""
    sources = {}
    for name in source_names:
        src = MagicMock()
        src.setup.return_value = None
        src.read.return_value = MagicMock()  # fake pw.Table
        src.teardown.return_value = None
        sources[name] = src

    transform = MagicMock()
    transform.setup.return_value = None
    transform.transform.return_value = {n: MagicMock() for n in sink_names}
    transform.teardown.return_value = None

    sinks = {}
    for name in sink_names:
        snk = MagicMock()
        snk.setup.return_value = None
        snk.write.return_value = None
        snk.teardown.return_value = None
        sinks[name] = snk

    return Pipeline(sources=sources, transform=transform, sinks=sinks)


# ===================================================================
# Part 1: Pipeline Log Output
# ===================================================================


class TestPipelineLogOutput:
    """Verify that Pipeline emits correct INFO logs at each lifecycle stage."""

    def test_full_lifecycle_logs(self, caplog):
        """All 7 key lifecycle logs appear in order."""
        pipeline = _make_pipeline()

        with caplog.at_level(logging.INFO, logger="pwetl"):
            with patch("pathway.run"):
                pipeline.run()

        messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
        expected = [
            "Pipeline starting...",
            "setup complete",
            "Sources read complete",
            "Transform complete",
            "Sinks write scheduled",
            "Running Pathway engine...",
            "Pipeline completed",
        ]
        for keyword in expected:
            assert any(keyword in m for m in messages), (
                f"Expected log containing '{keyword}' not found in: {messages}"
            )

        # Verify ordering: each keyword appears after the previous one
        positions = []
        for keyword in expected:
            for i, m in enumerate(messages):
                if keyword in m:
                    positions.append(i)
                    break
        assert positions == sorted(positions), (
            f"Lifecycle logs not in expected order: {positions}"
        )

    def test_source_initialized_log(self, caplog):
        """Source initialization logged with source name."""
        pipeline = _make_pipeline(source_names=("sales",))

        with caplog.at_level(logging.INFO, logger="pwetl"):
            with patch("pathway.run"):
                pipeline.run()

        info = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("Source 'sales' initialized" in m for m in info)

    def test_sink_initialized_log(self, caplog):
        """Sink initialization logged with sink name."""
        pipeline = _make_pipeline(sink_names=("db_output",))

        with caplog.at_level(logging.INFO, logger="pwetl"):
            with patch("pathway.run"):
                pipeline.run()

        info = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("Sink 'db_output' initialized" in m for m in info)

    def test_transform_initialized_log(self, caplog):
        """Transform initialization logged."""
        pipeline = _make_pipeline()

        with caplog.at_level(logging.INFO, logger="pwetl"):
            with patch("pathway.run"):
                pipeline.run()

        info = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("Transform initialized" in m for m in info)

    def test_source_read_complete_log(self, caplog):
        """Source read complete logged with source name."""
        pipeline = _make_pipeline(source_names=("csv_in",))

        with caplog.at_level(logging.INFO, logger="pwetl"):
            with patch("pathway.run"):
                pipeline.run()

        info = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("Source 'csv_in' read complete" in m for m in info)

    def test_sink_write_scheduled_log(self, caplog):
        """Sink write scheduled logged with sink name."""
        pipeline = _make_pipeline(sink_names=("file_out",))

        with caplog.at_level(logging.INFO, logger="pwetl"):
            with patch("pathway.run"):
                pipeline.run()

        info = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("Sink 'file_out' write scheduled" in m for m in info)

    def test_multiple_sources_each_logged(self, caplog):
        """Each source gets its own initialized + read complete log."""
        pipeline = _make_pipeline(
            source_names=("src_a", "src_b"),
            sink_names=("out",),
        )

        with caplog.at_level(logging.INFO, logger="pwetl"):
            with patch("pathway.run"):
                pipeline.run()

        info = [r.message for r in caplog.records if r.levelno == logging.INFO]
        for name in ("src_a", "src_b"):
            assert any(f"Source '{name}' initialized" in m for m in info)
            assert any(f"Source '{name}' read complete" in m for m in info)


# ===================================================================
# Part 2: Log Level Conventions
# ===================================================================


class TestLogLevelConventions:
    """Verify WARNING/ERROR log level rules per docs/logging.md."""

    def test_source_teardown_failure_warning(self, caplog):
        """Source teardown failure → WARNING (not ERROR)."""
        pipeline = _make_pipeline()
        pipeline.sources["input"].teardown.side_effect = RuntimeError("conn lost")

        with caplog.at_level(logging.WARNING, logger="pwetl"):
            with patch("pathway.run"):
                with pytest.raises(SourceError):
                    pipeline.run()

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("teardown failed" in r.message for r in warnings)

    def test_sink_teardown_failure_warning(self, caplog):
        """Sink teardown failure → WARNING (not ERROR)."""
        pipeline = _make_pipeline()
        pipeline.sinks["output"].teardown.side_effect = RuntimeError("write fail")

        with caplog.at_level(logging.WARNING, logger="pwetl"):
            with patch("pathway.run"):
                with pytest.raises(SinkError):
                    pipeline.run()

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("teardown failed" in r.message for r in warnings)

    def test_transform_teardown_failure_warning(self, caplog):
        """Transform teardown failure → WARNING (not ERROR)."""
        pipeline = _make_pipeline()
        pipeline.transform.teardown.side_effect = RuntimeError("cleanup fail")

        with caplog.at_level(logging.WARNING, logger="pwetl"):
            with patch("pathway.run"):
                with pytest.raises(TransformError):
                    pipeline.run()

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("teardown failed" in r.message for r in warnings)

    def test_no_error_in_pipeline_logs(self, caplog):
        """Successful run produces no ERROR-level logs from pipeline."""
        pipeline = _make_pipeline()

        with caplog.at_level(logging.DEBUG, logger="pwetl"):
            with patch("pathway.run"):
                pipeline.run()

        pipeline_errors = [
            r for r in caplog.records
            if r.levelno == logging.ERROR and r.name.startswith("pwetl.core.pipeline")
        ]
        assert pipeline_errors == []

    def test_teardown_also_failed_warning(self, caplog):
        """Main error + teardown error → 'Teardown also failed' at WARNING."""
        pipeline = _make_pipeline()
        # Main flow fails
        pipeline.sources["input"].read.side_effect = RuntimeError("boom")
        # Teardown also fails
        pipeline.sinks["output"].teardown.side_effect = RuntimeError("cleanup boom")

        with caplog.at_level(logging.WARNING, logger="pwetl"):
            with pytest.raises(SourceError):
                pipeline.run()

        warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("Teardown also failed" in m for m in warnings)


# ===================================================================
# Part 3: Bad Config
# ===================================================================


class TestBadConfigYAML:
    """ConfigLoader rejects invalid YAML configs with ConfigurationError."""

    def test_missing_sources(self, tmp_path):
        f = tmp_path / "c.yaml"
        f.write_text(
            "transform: t.T\n"
            "sinks:\n"
            "  - name: out\n"
            "    type: file\n"
        )
        with pytest.raises(ConfigurationError):
            ConfigLoader.load(f)

    def test_missing_transform(self, tmp_path):
        f = tmp_path / "c.yaml"
        f.write_text(
            "sources:\n"
            "  - name: in\n"
            "    type: csv\n"
            "sinks:\n"
            "  - name: out\n"
            "    type: file\n"
        )
        with pytest.raises(ConfigurationError):
            ConfigLoader.load(f)

    def test_missing_sinks(self, tmp_path):
        f = tmp_path / "c.yaml"
        f.write_text(
            "sources:\n"
            "  - name: in\n"
            "    type: csv\n"
            "transform: t.T\n"
        )
        with pytest.raises(ConfigurationError):
            ConfigLoader.load(f)

    def test_empty_sources(self, tmp_path):
        f = tmp_path / "c.yaml"
        f.write_text(
            "sources: []\n"
            "transform: t.T\n"
            "sinks:\n"
            "  - name: out\n"
            "    type: file\n"
        )
        with pytest.raises(ConfigurationError):
            ConfigLoader.load(f)

    def test_empty_sinks(self, tmp_path):
        f = tmp_path / "c.yaml"
        f.write_text(
            "sources:\n"
            "  - name: in\n"
            "    type: csv\n"
            "transform: t.T\n"
            "sinks: []\n"
        )
        with pytest.raises(ConfigurationError):
            ConfigLoader.load(f)

    def test_source_no_name(self, tmp_path):
        f = tmp_path / "c.yaml"
        f.write_text(
            "sources:\n"
            "  - type: csv\n"
            "transform: t.T\n"
            "sinks:\n"
            "  - name: out\n"
            "    type: file\n"
        )
        with pytest.raises(ConfigurationError):
            ConfigLoader.load(f)

    def test_source_no_type(self, tmp_path):
        f = tmp_path / "c.yaml"
        f.write_text(
            "sources:\n"
            "  - name: in\n"
            "transform: t.T\n"
            "sinks:\n"
            "  - name: out\n"
            "    type: file\n"
        )
        with pytest.raises(ConfigurationError):
            ConfigLoader.load(f)

    def test_duplicate_source_names(self, tmp_path):
        f = tmp_path / "c.yaml"
        f.write_text(
            "sources:\n"
            "  - name: data\n"
            "    type: csv\n"
            "  - name: data\n"
            "    type: json\n"
            "transform: t.T\n"
            "sinks:\n"
            "  - name: out\n"
            "    type: file\n"
        )
        with pytest.raises(ConfigurationError):
            ConfigLoader.load(f)

    def test_duplicate_sink_names(self, tmp_path):
        f = tmp_path / "c.yaml"
        f.write_text(
            "sources:\n"
            "  - name: in\n"
            "    type: csv\n"
            "transform: t.T\n"
            "sinks:\n"
            "  - name: out\n"
            "    type: file\n"
            "  - name: out\n"
            "    type: csv\n"
        )
        with pytest.raises(ConfigurationError):
            ConfigLoader.load(f)

    def test_transform_no_dot(self, tmp_path):
        f = tmp_path / "c.yaml"
        f.write_text(
            "sources:\n"
            "  - name: in\n"
            "    type: csv\n"
            "transform: InvalidFormat\n"
            "sinks:\n"
            "  - name: out\n"
            "    type: file\n"
        )
        with pytest.raises(ConfigurationError):
            ConfigLoader.load(f)

    def test_empty_file(self, tmp_path):
        f = tmp_path / "c.yaml"
        f.write_text("")
        with pytest.raises(ConfigurationError):
            ConfigLoader.load(f)


class TestBadConfigRegistry:
    """SourceFactory / SinkFactory reject unknown types with RegistryError."""

    def test_unknown_source_type(self):
        with pytest.raises(RegistryError, match="Unknown Source type"):
            SourceFactory.create("x", {"name": "x", "type": "nonexistent"})

    def test_unknown_sink_type(self):
        with pytest.raises(RegistryError, match="Unknown Sink type"):
            SinkFactory.create("x", {"name": "x", "type": "nonexistent"})

    def test_source_missing_type_field(self):
        with pytest.raises(RegistryError, match="missing 'type'"):
            SourceFactory.create("x", {"name": "x"})

    def test_sink_missing_type_field(self):
        with pytest.raises(RegistryError, match="missing 'type'"):
            SinkFactory.create("x", {"name": "x"})


class TestBadConfigDatabaseSink:
    """DatabaseSink rejects invalid configs."""

    def test_missing_dsn(self):
        from pwetl.sinks.database import DatabaseSink
        with pytest.raises(ValueError, match="dsn"):
            DatabaseSink("t", {"table": "t"})

    def test_missing_table(self):
        from pwetl.sinks.database import DatabaseSink
        with pytest.raises(ValueError, match="table"):
            DatabaseSink("t", {"dsn": "sqlite://"})

    def test_invalid_write_mode(self):
        from pwetl.sinks.database import DatabaseSink
        with pytest.raises(ValueError, match="write_mode"):
            DatabaseSink("t", {"dsn": "sqlite://", "table": "t", "write_mode": "merge"})

    def test_upsert_no_pk(self):
        from pwetl.sinks.database import DatabaseSink
        with pytest.raises(ValueError, match="primary_key"):
            DatabaseSink("t", {"dsn": "sqlite://", "table": "t", "write_mode": "upsert"})

    def test_columns_init_sql_conflict(self):
        from pwetl.sinks.database import DatabaseSink
        with pytest.raises(ValueError, match="mutually exclusive"):
            DatabaseSink("t", {
                "dsn": "sqlite://",
                "table": "t",
                "columns": {"id": "int, pk"},
                "init_sql": "setup.sql",
            })


class TestBadConfigDatabaseSource:
    """DatabaseSource rejects invalid configs."""

    def test_missing_dsn(self):
        from pwetl.sources.database import DatabaseSource
        with pytest.raises(ValueError, match="dsn"):
            DatabaseSource("t", {"query_sql": "q.sql"})

    def test_missing_query_and_table(self):
        from pwetl.sources.database import DatabaseSource
        with pytest.raises(ValueError, match="query_sql"):
            DatabaseSource("t", {"dsn": "sqlite://"})


# ===================================================================
# Part 4: Error Propagation
# ===================================================================


class TestErrorPropagation:
    """Pipeline wraps component errors into SourceError/SinkError/TransformError."""

    # -- Setup failures --

    def test_source_setup_raises_source_error(self):
        pipeline = _make_pipeline()
        pipeline.sources["input"].setup.side_effect = RuntimeError("bad dsn")

        with pytest.raises(SourceError, match="initialization failed"):
            pipeline.run()

    def test_sink_setup_raises_sink_error(self):
        pipeline = _make_pipeline()
        pipeline.sinks["output"].setup.side_effect = RuntimeError("no table")

        with pytest.raises(SinkError, match="initialization failed"):
            pipeline.run()

    def test_transform_setup_raises_transform_error(self):
        pipeline = _make_pipeline()
        pipeline.transform.setup.side_effect = RuntimeError("import error")

        with pytest.raises(TransformError, match="initialization failed"):
            pipeline.run()

    # -- Read / Write failures --

    def test_source_read_raises_source_error(self):
        pipeline = _make_pipeline()
        pipeline.sources["input"].read.side_effect = RuntimeError("conn refused")

        with pytest.raises(SourceError, match="read failed"):
            pipeline.run()

    # -- Teardown failures (main flow OK) --

    def test_sink_teardown_raises_sink_error(self):
        """Sink teardown failure propagates as SinkError when main flow succeeds."""
        pipeline = _make_pipeline()
        pipeline.sinks["output"].teardown.side_effect = RuntimeError("write fail")

        with patch("pathway.run"):
            with pytest.raises(SinkError, match="teardown failed"):
                pipeline.run()

    def test_source_teardown_raises_source_error(self):
        """Source teardown failure propagates as SourceError when main flow succeeds."""
        pipeline = _make_pipeline()
        pipeline.sources["input"].teardown.side_effect = RuntimeError("cleanup fail")

        with patch("pathway.run"):
            with pytest.raises(SourceError, match="teardown failed"):
                pipeline.run()

    # -- Error priority --

    def test_main_error_priority(self, caplog):
        """Main error takes priority over teardown error."""
        pipeline = _make_pipeline()
        pipeline.sources["input"].read.side_effect = RuntimeError("main boom")
        pipeline.sinks["output"].teardown.side_effect = RuntimeError("teardown boom")

        with caplog.at_level(logging.WARNING, logger="pwetl"):
            with pytest.raises(SourceError, match="read failed"):
                pipeline.run()

        warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("Teardown also failed" in m for m in warnings)

    # -- Transform validation --

    def test_transform_bad_return_type(self):
        """Transform returning non-dict raises TransformError."""
        pipeline = _make_pipeline()
        pipeline.transform.transform.return_value = [MagicMock()]  # list, not dict

        with patch("pathway.run"):
            with pytest.raises(TransformError, match="must return Dict"):
                pipeline.run()

    def test_missing_sink_table(self):
        """Transform not producing required sink table raises TransformError."""
        pipeline = _make_pipeline(sink_names=("output",))
        pipeline.transform.transform.return_value = {"wrong_name": MagicMock()}

        with patch("pathway.run"):
            with pytest.raises(TransformError, match="did not produce"):
                pipeline.run()

    # -- Sink-specific SinkError --

    def test_db_sink_no_engine_raises_sink_error(self):
        """DatabaseSink._execute_write() with engine=None raises SinkError."""
        from pwetl.sinks.database import DatabaseSink

        sink = DatabaseSink("test", {"dsn": "sqlite://", "table": "t"})
        sink._engine = None

        with pytest.raises(SinkError, match="no engine"):
            sink._execute_write()

    def test_api_sink_no_temp_path_raises_sink_error(self):
        """APISink.teardown() with no temp_path raises SinkError."""
        from pwetl.sinks.api import APISink

        sink = APISink("test", {"url": "http://example.com"})
        sink._temp_path = None

        with pytest.raises(SinkError, match="no temp_path"):
            sink.teardown()

    def test_api_sink_missing_file_raises_sink_error(self, tmp_path):
        """APISink.teardown() with missing temp file raises SinkError."""
        from pwetl.sinks.api import APISink

        sink = APISink("test", {"url": "http://example.com"})
        sink._temp_path = str(tmp_path / "nonexistent.jsonl")

        with pytest.raises(SinkError, match="does not exist"):
            sink.teardown()
