"""Schema 解析工具。"""

from types import UnionType
from typing import Dict, Type, Optional, Union, get_origin

import pathway as pw
import pydantic
from pydantic import BaseModel, create_model

# 延遲導入以支援動態查找
try:
    import datetime as datetime_module
except ImportError:
    datetime_module = None

try:
    import decimal as decimal_module
except ImportError:
    decimal_module = None

try:
    import uuid as uuid_module
except ImportError:
    uuid_module = None


class SchemaParser:
    """Pathway Schema 解析工具。"""

    # 型態對應表：YAML 字串 -> Python/Pathway 型態（常用簡寫）
    TYPE_MAP: Dict[str, Type] = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "bytes": bytes,
        "datetime": pw.DateTimeNaive,
        "duration": pw.Duration,
        "json": pw.Json,
    }

    # Pydantic 型態對應（常用簡寫）
    PYDANTIC_TYPE_MAP: Dict[str, Type] = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "bytes": bytes,
        "datetime": datetime_module.datetime if datetime_module else str,
        "duration": str,
        "json": dict,
    }

    # Pathway 動態查找模組（按順序嘗試）
    PATHWAY_MODULES = [pw]

    # Pydantic 動態查找模組（按順序嘗試）
    PYDANTIC_MODULES = [pydantic]  # EmailStr, HttpUrl, etc.

    # Pathway 特定型別 → Pydantic 相容型別的映射
    PATHWAY_TO_PYDANTIC: Dict[str, Type] = {
        "DateTimeNaive": str,  # Pathway 的 DateTimeNaive 對應 Pydantic 的 str
        "DateTime": str,
        "Duration": str,
        "Json": dict,  # 注意：使用 dict 而不是 pydantic.Json
    }

    # Pydantic 特定型別 → Pathway 相容型別的映射
    # 大多數 Pydantic 特殊型別（EmailStr, HttpUrl 等）本質上是字串驗證
    PYDANTIC_TO_PATHWAY: Dict[str, Type] = {
        "EmailStr": str,
        "HttpUrl": str,
        "AnyUrl": str,
        "IPvAnyAddress": str,
        "NameEmail": str,
        "UUID": str,  # UUID → str for Pathway
        "Decimal": float,  # Decimal → float for Pathway
        # 可以根據需要繼續添加
    }

    # 通用型別模組（兩者都可用）
    @classmethod
    def _get_common_type_modules(cls):
        """取得通用型別模組列表（動態構建以避免 import 錯誤）。"""
        modules = [
            __builtins__ if isinstance(__builtins__, dict) else vars(__builtins__),
        ]
        # 添加可選的標準庫模組
        if datetime_module is not None:
            modules.append(datetime_module)
        if decimal_module is not None:
            modules.append(decimal_module)
        if uuid_module is not None:
            modules.append(uuid_module)
        return modules

    @classmethod
    def parse(cls, schema_config: Dict[str, Union[str, Dict]]) -> Type[pw.Schema]:
        """從配置建立 Pathway Schema。

        Args:
            schema_config: Schema 配置，格式為 {欄位名稱: 型態字串或嵌套字典}
                例如：
                - 簡單型態: {'id': 'int', 'name': 'str'}
                - Optional: {'address': 'str?', 'age': 'int?'}
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
        schema_dict = {"__annotations__": annotations}

        return type("DynamicSchema", (pw.Schema,), schema_dict)

    @classmethod
    def create_pydantic_model(
        cls, schema_config: Dict[str, Union[str, Dict]], model_name: str = "DataModel"
    ) -> Type[BaseModel]:
        """從配置建立 Pydantic 模型用於驗證。

        Args:
            schema_config: Schema 配置
            model_name: 模型名稱

        Returns:
            Pydantic BaseModel 類別
        """
        fields = {}

        for field_name, type_def in schema_config.items():
            field_type = cls._parse_pydantic_type(type_def, field_name)

            # 如果是 Optional 型態，允許 None
            if get_origin(field_type) is Union:
                fields[field_name] = (field_type, None)
            else:
                fields[field_name] = (field_type, ...)

        return create_model(model_name, **fields)

    @classmethod
    def _dynamic_type_lookup(cls, type_name: str, search_modules: list) -> Type | None:
        """從指定模組動態查找型別。

        Args:
            type_name: 型別名稱（例如 'EmailStr', 'HttpUrl', 'UUID'）
            search_modules: 要搜尋的模組列表

        Returns:
            找到的型別類別，找不到則返回 None
        """
        for module in search_modules:
            # 處理 dict 型的 __builtins__
            if isinstance(module, dict):
                if type_name in module:
                    return module[type_name]
            else:
                # 正常模組
                try:
                    type_class = getattr(module, type_name, None)
                    if type_class is not None:
                        return type_class
                except AttributeError:
                    continue
        return None

    @classmethod
    def _parse_pydantic_type(
        cls, type_def: Union[str, Dict], field_name: str = "Field"
    ) -> Type | UnionType:
        """解析 Pydantic 型態定義。

        Args:
            type_def: 型態定義
            field_name: 欄位名稱（用於嵌套模型命名）

        Returns:
            Pydantic 相容的型態（可能是 Type 或 UnionType）
        """
        # 處理嵌套的 schema（字典）- 遞迴創建 Pydantic 模型
        if isinstance(type_def, dict):
            nested_model_name = f"{field_name}Model"
            return cls.create_pydantic_model(type_def, nested_model_name)

        type_str = type_def

        # 處理 ? 語法（例如 str?, int?）
        if type_str.endswith("?"):
            base_type_str = type_str[:-1]

            # 先查 map
            if base_type_str in cls.PYDANTIC_TYPE_MAP:
                return Optional[cls.PYDANTIC_TYPE_MAP[base_type_str]]

            # 再查 Pathway 映射表（已知的映射優先）
            if base_type_str in cls.PATHWAY_TO_PYDANTIC:
                return Optional[cls.PATHWAY_TO_PYDANTIC[base_type_str]]

            # 動態查找 Pydantic 型別
            base_type = cls._dynamic_type_lookup(
                base_type_str, cls.PYDANTIC_MODULES + cls._get_common_type_modules()
            )
            if base_type:
                return Optional[base_type]

            # 嘗試動態從 Pathway 查找
            pw_type = cls._dynamic_type_lookup(base_type_str, cls.PATHWAY_MODULES)
            if pw_type:
                # Pathway 型別沒有對應的映射，使用 object（允許任何值）
                return Optional[object]

            raise ValueError(
                f"不支援的型態: '{base_type_str}'\n"
                f"支援的內建簡寫: {', '.join(cls.PYDANTIC_TYPE_MAP.keys())}\n"
                f"或從 pydantic 模組的任何型別（例如 EmailStr, HttpUrl, UUID）"
            )

        # 處理一般型態
        # 先查 map（常用簡寫）
        if type_str in cls.PYDANTIC_TYPE_MAP:
            return cls.PYDANTIC_TYPE_MAP[type_str]

        # 再查 Pathway 映射表
        if type_str in cls.PATHWAY_TO_PYDANTIC:
            return cls.PATHWAY_TO_PYDANTIC[type_str]

        # 動態查找 Pydantic 型別
        found_type = cls._dynamic_type_lookup(
            type_str, cls.PYDANTIC_MODULES + cls._get_common_type_modules()
        )
        if found_type:
            return found_type

        # 嘗試動態從 Pathway 查找
        pw_type = cls._dynamic_type_lookup(type_str, cls.PATHWAY_MODULES)
        if pw_type:
            # Pathway 型別沒有對應的映射，使用 object（允許任何值）
            return object

        raise ValueError(
            f"不支援的型態: '{type_str}'\n"
            f"支援的內建簡寫: {', '.join(cls.PYDANTIC_TYPE_MAP.keys())}\n"
            f"或從 pydantic 模組的任何型別（例如 EmailStr, HttpUrl, UUID）\n"
            f"或使用嵌套字典定義"
        )

    @classmethod
    def _parse_type(cls, type_def: Union[str, Dict]) -> Type | UnionType:
        """解析型態定義。

        Args:
            type_def: 型態定義，可以是：
                - 字串：'str', 'int', 'str?' 等
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
        if type_str.endswith("?"):
            base_type_str = type_str[:-1]  # 移除 ?

            # 先查 map
            if base_type_str in cls.TYPE_MAP:
                return Optional[cls.TYPE_MAP[base_type_str]]

            # 再查 Pydantic 映射表
            if base_type_str in cls.PYDANTIC_TO_PATHWAY:
                return Optional[cls.PYDANTIC_TO_PATHWAY[base_type_str]]

            # 動態查找 Pathway 型別
            base_type = cls._dynamic_type_lookup(
                base_type_str, cls.PATHWAY_MODULES + cls._get_common_type_modules()
            )
            if base_type:
                return Optional[base_type]

            # 嘗試動態從 Pydantic 查找，預設映射為 str
            pydantic_type = cls._dynamic_type_lookup(
                base_type_str, cls.PYDANTIC_MODULES
            )
            if pydantic_type:
                return Optional[str]  # Pydantic 特殊型別大多是字串驗證

            raise ValueError(
                f"不支援的型態: '{base_type_str}'\n"
                f"支援的內建簡寫: {', '.join(cls.TYPE_MAP.keys())}\n"
                f"或從 pathway 模組的任何型別（例如 DateTimeNaive, Duration, Json）"
            )

        # 處理一般型態
        # 先查 map（常用簡寫）
        if type_str in cls.TYPE_MAP:
            return cls.TYPE_MAP[type_str]

        # 再查 Pydantic 映射表
        if type_str in cls.PYDANTIC_TO_PATHWAY:
            return cls.PYDANTIC_TO_PATHWAY[type_str]

        # 動態查找 Pathway 型別
        found_type = cls._dynamic_type_lookup(
            type_str, cls.PATHWAY_MODULES + cls._get_common_type_modules()
        )
        if found_type:
            return found_type

        # 嘗試動態從 Pydantic 查找，預設映射為 str
        pydantic_type = cls._dynamic_type_lookup(type_str, cls.PYDANTIC_MODULES)
        if pydantic_type:
            return str  # Pydantic 特殊型別大多是字串驗證

        raise ValueError(
            f"不支援的型態: '{type_str}'\n"
            f"支援的內建簡寫: {', '.join(cls.TYPE_MAP.keys())}\n"
            f"或從 pathway 模組的任何型別（例如 DateTimeNaive, Duration, Json）\n"
            f"或使用嵌套字典定義"
        )

    @classmethod
    def add_custom_type(cls, type_name: str, type_class: Type) -> None:
        """新增自定義型態到型態對應表。

        Args:
            type_name: 型態名稱（在 YAML 中使用）
            type_class: 對應的 Python 類別
        """
        cls.TYPE_MAP[type_name] = type_class
