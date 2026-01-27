"""File-based data sinks."""
from pathlib import Path
from typing import Any, Dict, List
import pathway as pw
from pwetl.sinks.base import BaseSink


class FileSink(BaseSink):
    """檔案輸出。

    支援的格式：CSV, JSON, JSONL, Parquet
    """

    required_config = ['path']
    optional_config = {
        'format': 'csv',  # 預設為 CSV
    }

    # 支援的檔案格式
    SUPPORTED_FORMATS = ['csv', 'json', 'jsonl', 'parquet']

    def write(self, table: pw.Table) -> None:
        """寫入檔案。

        Args:
            table: 要寫入的 Pathway Table

        Raises:
            ValueError: 當檔案格式不支援時
        """
        path = self.config['path']
        file_format = self.config['format']

        # 檢查格式是否支援
        if file_format not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"不支援的檔案格式: '{file_format}'\n"
                f"支援的格式: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # 確保目錄存在
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        # 根據格式寫入檔案
        if file_format == 'csv':
            self._write_csv(table, path)
        elif file_format == 'json':
            self._write_json(table, path)
        elif file_format == 'jsonl':
            self._write_jsonl(table, path)
        elif file_format == 'parquet':
            self._write_parquet(table, path)

    def _write_csv(self, table: pw.Table, path: str) -> None:
        """寫入 CSV 檔案。"""
        pw.io.csv.write(table, path)

    def _write_json(self, table: pw.Table, path: str) -> None:
        """寫入 JSON 檔案。"""
        # JSON 使用 JSONL 格式（每行一個物件）
        pw.io.jsonlines.write(table, path)

    def _write_jsonl(self, table: pw.Table, path: str) -> None:
        """寫入 JSONL 檔案。"""
        pw.io.jsonlines.write(table, path)

    def _write_parquet(self, table: pw.Table, path: str) -> None:
        """寫入 Parquet 檔案。"""
        pw.io.parquet.write(table, path)
