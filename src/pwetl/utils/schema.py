"""Schema 解析工具。"""
from typing import Dict, Type

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
    def parse(cls, schema_config: Dict[str, str]) -> Type[pw.Schema]:
        """從配置建立 Pathway Schema。

        Args:
            schema_config: Schema 配置，格式為 {欄位名稱: 型態字串}
                例如：{'id': 'int', 'name': 'str', 'created_at': 'datetime'}

        Returns:
            Pathway Schema 類別

        Raises:
            ValueError: 當型態不支援時

        Example:
            >>> schema_config = {'id': 'int', 'name': 'str'}
            >>> schema = SchemaParser.parse(schema_config)
            >>> # 等同於建立:
            >>> # class MySchema(pw.Schema):
            >>> #     id: int
            >>> #     name: str
        """
        # 驗證所有型態
        for field_name, type_str in schema_config.items():
            if type_str not in cls.TYPE_MAP:
                raise ValueError(
                    f"不支援的型態: '{type_str}'\n"
                    f"支援的型態: {', '.join(cls.TYPE_MAP.keys())}"
                )

        # 動態建立 Schema 類別，使用 __annotations__
        schema_dict = {
            '__annotations__': {
                field_name: cls.TYPE_MAP[type_str]
                for field_name, type_str in schema_config.items()
            }
        }

        return type('DynamicSchema', (pw.Schema,), schema_dict)

    @classmethod
    def add_custom_type(cls, type_name: str, type_class: Type) -> None:
        """新增自定義型態到型態對應表。

        Args:
            type_name: 型態名稱（在 YAML 中使用）
            type_class: 對應的 Python 類別
        """
        cls.TYPE_MAP[type_name] = type_class
