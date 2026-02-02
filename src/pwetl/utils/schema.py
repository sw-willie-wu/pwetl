"""Schema 解析工具。"""
from typing import Dict, Type, Optional, Any, Union

import pathway as pw


class SchemaParser:
    """Pathway Schema 解析工具。"""

    # 型態對應表：YAML 字串 -> Python/Pathway 型態
    TYPE_MAP: Dict[str, Type] = {
        'str': str,
        'int': int,
        'float': float,
        'bool': bool,
        'bytes': bytes,
        'datetime': pw.DateTimeNaive,
        'duration': pw.Duration,
        'json': pw.Json,
    }

    @classmethod
    def parse(cls, schema_config: Dict[str, Union[str, Dict]]) -> Type[pw.Schema]:
        """從配置建立 Pathway Schema。

        Args:
            schema_config: Schema 配置，格式為 {欄位名稱: 型態字串或嵌套字典}
                例如：
                - 簡單型態: {'id': 'int', 'name': 'str'}
                - Optional (? 語法): {'address': 'str?', 'age': 'int?'}
                - Optional (完整語法): {'address': 'Optional[str]'}
                - 嵌套物件: {'Point': {'Latitude': 'float', 'Longitude': 'float'}}

        Returns:
            Pathway Schema 類別

        Raises:
            ValueError: 當型態不支援時

        Example:
            >>> schema_config = {
            ...     'id': 'int',
            ...     'name': 'str',
            ...     'address': 'str?',  # Optional[str]
            ...     'Point': {'Latitude': 'float', 'Longitude': 'float'}
            ... }
            >>> schema = SchemaParser.parse(schema_config)
        """
        # 驗證並解析所有型態
        annotations = {}
        for field_name, type_def in schema_config.items():
            annotations[field_name] = cls._parse_type(type_def)

        # 動態建立 Schema 類別，使用 __annotations__
        schema_dict = {'__annotations__': annotations}

        return type('DynamicSchema', (pw.Schema,), schema_dict)

    @classmethod
    def _parse_type(cls, type_def: Union[str, Dict]) -> Type:
        """解析型態定義。

        Args:
            type_def: 型態定義，可以是：
                - 字串：'str', 'int', 'str?', 'Optional[str]' 等
                - 字典：嵌套的 schema 定義

        Returns:
            對應的 Python 型態

        Raises:
            ValueError: 當型態不支援時
        """
        # 處理嵌套的 schema（字典）
        if isinstance(type_def, dict):
            # 遞迴解析嵌套的 schema，返回 pw.Json
            # Pathway 會將嵌套結構視為 JSON 物件
            return pw.Json
        
        # 以下處理字串型態
        type_str = type_def
        
        # 處理 ? 語法（例如 str?, int?）
        if type_str.endswith('?'):
            base_type_str = type_str[:-1]  # 移除 ?
            if base_type_str not in cls.TYPE_MAP:
                raise ValueError(
                    f"不支援的型態: '{base_type_str}'\n"
                    f"支援的型態: {', '.join(cls.TYPE_MAP.keys())}"
                )
            return Optional[cls.TYPE_MAP[base_type_str]]
        
        # 處理 Optional[...] 語法
        if type_str.startswith('Optional[') and type_str.endswith(']'):
            # 提取內部型態
            inner_type_str = type_str[9:-1]  # 移除 'Optional[' 和 ']'
            if inner_type_str not in cls.TYPE_MAP:
                raise ValueError(
                    f"不支援的型態: '{inner_type_str}'\n"
                    f"支援的型態: {', '.join(cls.TYPE_MAP.keys())}"
                )
            return Optional[cls.TYPE_MAP[inner_type_str]]
        
        # 處理一般型態
        if type_str not in cls.TYPE_MAP:
            raise ValueError(
                f"不支援的型態: '{type_str}'\n"
                f"支援的型態: {', '.join(cls.TYPE_MAP.keys())} 或 型態? 或 Optional[型態] 或嵌套字典"
            )
        
        return cls.TYPE_MAP[type_str]

    @classmethod
    def add_custom_type(cls, type_name: str, type_class: Type) -> None:
        """新增自定義型態到型態對應表。

        Args:
            type_name: 型態名稱（在 YAML 中使用）
            type_class: 對應的 Python 類別
        """
        cls.TYPE_MAP[type_name] = type_class
