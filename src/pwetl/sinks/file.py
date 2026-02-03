"""File-based data sinks."""
from pathlib import Path

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

    def __init__(self, name: str, config: dict):
        """初始化 FileSink。"""
        super().__init__(name, config)
        self._jsonl_temp_path = None
        self._json_output_path = None

    # 支援的檔案格式
    SUPPORTED_FORMATS = ['csv', 'json', 'jsonl', 'parquet']

    def write(self, table: pw.Table) -> None:
        """寫入檔案。

        Args:
            table: 要寫入的 Pathway Table

        Raises:
            ValueError: 當檔案格式不支援時
        """
        # 應用 schema（如果有定義）
        table = self._apply_schema(table)
        
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
        """寫入 JSON 檔案（數組格式）。"""
        # 先寫入 JSONL 格式
        self._jsonl_temp_path = path + '.jsonl_temp'
        pw.io.jsonlines.write(table, self._jsonl_temp_path)
        # 記錄需要後處理的 JSON 文件
        self._json_output_path = path

    def _write_jsonl(self, table: pw.Table, path: str) -> None:
        """寫入 JSONL 檔案。"""
        pw.io.jsonlines.write(table, path)

    def _write_parquet(self, table: pw.Table, path: str) -> None:
        """寫入 Parquet 檔案。"""
        pw.io.parquet.write(table, path)

    def teardown(self) -> None:
        """清理並後處理（將 JSONL 轉換為 JSON 數組）。"""
        if self._jsonl_temp_path and self._json_output_path:
            import json
            
            # 讀取 JSONL 文件並轉換為 JSON 數組
            objects = []
            with open(self._jsonl_temp_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        objects.append(json.loads(line))
            
            # 寫入 JSON 數組
            with open(self._json_output_path, 'w', encoding='utf-8') as f:
                json.dump(objects, f, ensure_ascii=False, indent=2)
            
            # 刪除臨時文件
            Path(self._jsonl_temp_path).unlink(missing_ok=True)
