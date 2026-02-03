"""File-based data sources."""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import pathway as pw
from pwetl.sources.base import BaseSource
from pwetl.utils.schema import SchemaParser


class FileSource(BaseSource):
    """檔案資料源。

    支援的格式：CSV, JSON, JSONL, Parquet

    可以指定單一檔案或監測資料夾：
    - 單一檔案：path 指向檔案
    - 資料夾監測：path 指向資料夾，使用 regex 或 filename_pattern 過濾
    """

    required_config = ['path']
    optional_config = {
        'format': 'csv',            # 預設為 CSV
        'schema': None,             # 可選的 Schema
        'mode': 'static',           # 'static' 或 'streaming'
        'regex': None,              # 正則表達式過濾檔名（資料夾模式）
        'filename_pattern': None,   # 檔名匹配模式（glob pattern，資料夾模式）
    }

    # 支援的檔案格式
    SUPPORTED_FORMATS = ['csv', 'json', 'jsonl', 'parquet']

    def read(self) -> pw.Table:
        """讀取檔案資料。

        Returns:
            pw.Table: 包含資料的 Pathway Table

        Raises:
            ValueError: 當檔案格式不支援時
            FileNotFoundError: 當檔案或資料夾不存在時
        """
        path = self.config['path']
        file_format = self.config['format']

        # 檢查路徑是否存在
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"路徑不存在: {path}")

        # 檢查格式是否支援
        if file_format not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"不支援的檔案格式: '{file_format}'\n"
                f"支援的格式: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # 解析 Schema
        schema = self._get_schema()
        
        # 檢查是否使用 strict 驗證模式
        validation_mode = self._get_validation_mode()
        
        # strict 模式：先讀取資料、驗證、轉換，再建立 Table
        if validation_mode == 'strict' and schema:
            return self._read_with_strict_validation(path, file_format, schema)

        # 判斷是資料夾還是檔案
        if path_obj.is_dir():
            return self._read_directory(path, file_format, schema)
        return self._read_single_file(path, file_format, schema)

    def _read_single_file(
        self, path: str, file_format: str, schema: Optional[Type[pw.Schema]]
    ) -> pw.Table:
        """讀取單一檔案。"""
        # 根據格式讀取檔案
        if file_format == 'csv':
            return self._read_csv(path, schema)
        if file_format == 'json':
            return self._read_json(path, schema)
        if file_format == 'jsonl':
            return self._read_jsonl(path, schema)
        if file_format == 'parquet':
            return self._read_parquet(path, schema)
        return None

    def _read_directory(
        self, path: str, file_format: str, schema: Optional[Type[pw.Schema]]
    ) -> pw.Table:
        """讀取資料夾內的檔案。

        使用 regex 或 filename_pattern 來過濾檔案。
        """
        regex_pattern = self.config.get('regex')
        filename_pattern = self.config.get('filename_pattern')

        # 根據格式建立最終的讀取路徑
        if regex_pattern:
            # 使用正則表達式過濾
            final_path = self._get_regex_filtered_path(
                path, file_format, regex_pattern
            )
        elif filename_pattern:
            # 使用檔名匹配模式（glob pattern）
            final_path = str(Path(path) / filename_pattern)
        else:
            # 預設讀取所有符合格式的檔案
            final_path = str(Path(path) / f"*.{file_format}")

        # 根據格式讀取檔案
        if file_format == 'csv':
            return self._read_csv(final_path, schema)
        if file_format == 'json':
            return self._read_json(final_path, schema)
        if file_format == 'jsonl':
            return self._read_jsonl(final_path, schema)
        if file_format == 'parquet':
            return self._read_parquet(final_path, schema)
        return None

    def _get_regex_filtered_path(self, directory: str, file_format: str, pattern: str) -> str:
        """使用正則表達式過濾檔案，轉換為 glob pattern。

        注意：Pathway 不直接支援 regex，所以這裡我們需要找出符合的檔案
        並轉換為可用的路徑格式。在 streaming 模式下，這個方法的效果有限。

        Args:
            directory: 資料夾路徑
            file_format: 檔案格式
            pattern: 正則表達式 pattern

        Returns:
            符合條件的檔案路徑 pattern
        """
        regex = re.compile(pattern)
        dir_path = Path(directory)

        # 在 static 模式下，可以直接過濾檔案
        mode = self.config.get('mode', 'static')
        if mode == 'static':
            # 找出所有符合 regex 的檔案
            matching_files = [
                str(f) for f in dir_path.glob(f"*.{file_format}")
                if regex.search(f.name)
            ]

            if not matching_files:
                raise ValueError(
                    f"在 {directory} 中找不到符合 pattern '{pattern}' 的 {file_format} 檔案"
                )

            # 如果只有一個檔案，直接返回
            if len(matching_files) == 1:
                return matching_files[0]

            # 多個檔案：使用 glob pattern（限制較多）
            # 嘗試從 regex 轉換為 glob pattern（簡單情況）
            return self._convert_regex_to_glob(directory, file_format, pattern)
        # streaming 模式：轉換為 glob（限制較多）
        return self._convert_regex_to_glob(directory, file_format, pattern)

    def _convert_regex_to_glob(self, directory: str, file_format: str, pattern: str) -> str:
        """嘗試將簡單的正則表達式轉換為 glob pattern。

        這只支援簡單的 regex pattern。對於複雜的 pattern，建議使用 filename_pattern。
        """
        # 簡單轉換規則
        glob = pattern.replace('.*', '*').replace('.+', '*').replace('\\d', '[0-9]')

        # 如果 pattern 不包含副檔名，加上
        if not glob.endswith(f'.{file_format}'):
            glob = f"{glob}*.{file_format}"

        return str(Path(directory) / glob)

    def _get_schema(self) -> Optional[Type[pw.Schema]]:
        """取得 Schema。

        Returns:
            Pathway Schema 類別，如果沒有指定則回傳 None
        """
        schema_config = self.config.get('schema')
        if schema_config:
            return SchemaParser.parse(schema_config)
        return None
    
    def _read_with_strict_validation(
        self, path: str, file_format: str, schema: Type[pw.Schema]
    ) -> pw.Table:
        """使用 strict 模式讀取：先載入資料、驗證、轉換，再建立 Table。
        
        Args:
            path: 檔案或資料夾路徑
            file_format: 檔案格式
            schema: Pathway Schema
            
        Returns:
            驗證並標準化後的 Pathway Table
        """
        import json
        
        # 讀取原始資料
        path_obj = Path(path)
        schema_config = self.config.get('schema', {})
        
        if path_obj.is_dir():
            # 讀取資料夾中的所有檔案
            raw_data = []
            pattern = f"*.{file_format}"
            for file_path in path_obj.glob(pattern):
                raw_data.extend(self._load_file_data(str(file_path), file_format))
        else:
            raw_data = self._load_file_data(path, file_format)
        
        # 統一的驗證和處理入口
        normalized_data = self._process_data_with_validation(raw_data, schema_config)
        
        # 用處理後的資料建立 Table
        simple_schema = self._create_simple_schema(schema)
        
        # 將 dict 轉成 schema 需要的格式
        rows = []
        field_names = list(simple_schema.__annotations__.keys())
        for row_dict in normalized_data:
            # 按 schema 順序取值，轉成 tuple
            row_tuple = tuple(row_dict.get(field, None) for field in field_names)
            rows.append(row_tuple)
        
        return pw.debug.table_from_rows(schema=simple_schema, rows=rows)
    
    def _load_file_data(self, file_path: str, file_format: str) -> List[Dict[str, Any]]:
        """載入檔案資料為 Python 物件。
        
        Args:
            file_path: 檔案路徑
            file_format: 檔案格式
            
        Returns:
            資料列表
        """
        import csv
        import json
        
        if file_format == 'csv':
            with open(file_path, 'r', encoding='utf-8') as f:
                return list(csv.DictReader(f))
        
        elif file_format in ('json', 'jsonl'):
            data = []
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_format == 'json':
                    content = json.load(f)
                    # 如果是陣列就展開，否則當成單一物件
                    if isinstance(content, list):
                        data = content
                    else:
                        data = [content]
                else:  # jsonl
                    for line in f:
                        line = line.strip()
                        if line:
                            data.append(json.loads(line))
            return data
        
        elif file_format == 'parquet':
            # Parquet 需要用 pandas 或 pyarrow 讀取
            try:
                import pandas as pd
                df = pd.read_parquet(file_path)
                return df.to_dict('records')
            except ImportError:
                raise ImportError("strict 模式讀取 Parquet 需要安裝 pandas")
        
        return []
    
    def _create_simple_schema(self, original_schema: Type[pw.Schema]) -> Type[pw.Schema]:
        """建立簡化的 schema（特殊型別已經轉成基本型別）。
        
        Args:
            original_schema: 原始 schema
            
        Returns:
            簡化的 schema（只包含基本型別）
        """
        # 從 original_schema 取得欄位，但型別簡化
        # 因為資料已經 dump 成基本型別，所以大部分欄位可以用 Any 或推導
        # 最簡單的方式是不指定 schema，讓 Pathway 自動推導
        # 但為了保持欄位順序和型別一致，我們從 config 重新解析
        schema_config = self.config.get('schema', {})
        if not schema_config:
            return None
        
        # 使用已經處理好的映射邏輯
        from pwetl.utils.schema import SchemaParser
        return SchemaParser.parse(schema_config)

    def _read_csv(self, path: str, schema: Optional[Type[pw.Schema]]) -> pw.Table:
        """讀取 CSV 檔案。"""
        mode = self.config['mode']
        if schema:
            return pw.io.csv.read(path, schema=schema, mode=mode)
        return pw.io.csv.read(path, mode=mode)

    def _read_json(self, path: str, schema: Optional[Type[pw.Schema]]) -> pw.Table:
        """讀取 JSON 檔案（單一物件或陣列）。"""
        mode = self.config['mode']
        if schema:
            return pw.io.jsonlines.read(path, schema=schema, mode=mode)
        return pw.io.jsonlines.read(path, mode=mode)

    def _read_jsonl(self, path: str, schema: Optional[Type[pw.Schema]]) -> pw.Table:
        """讀取 JSONL 檔案（每行一個 JSON 物件）。"""
        mode = self.config['mode']
        if schema:
            return pw.io.jsonlines.read(path, schema=schema, mode=mode)
        return pw.io.jsonlines.read(path, mode=mode)

    def _read_parquet(
        self, path: str, _schema: Optional[Type[pw.Schema]]
    ) -> pw.Table:
        """讀取 Parquet 檔案。"""
        mode = self.config['mode']
        # Parquet 檔案已經包含 schema 資訊
        return pw.io.parquet.read(path, mode=mode)
