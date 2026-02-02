"""Base class for all data sinks."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List
import pathway as pw


class BaseSink(ABC):
    """所有 Sink 的抽象基類。

    所有自定義 Sink 都必須繼承此類別並實作 write() 方法。
    """

    # 子類可以覆寫這些屬性來定義必要和可選的配置參數
    required_config: List[str] = []
    optional_config: Dict[str, Any] = {}

    def __init__(self, name: str, config: Dict[str, Any]):
        """初始化 Sink。

        Args:
            name: Sink 的名稱，用於在 Pipeline 中識別
            config: Sink 的配置參數
        """
        self.name = name
        self.config = config
        self.schema_class = None
        self._validate_config()
        self._setup_schema()

    def _validate_config(self) -> None:
        """驗證配置參數。

        檢查必要參數是否存在，並設定可選參數的預設值。

        Raises:
            ValueError: 當缺少必要參數時
        """
        # 檢查必要參數
        for key in self.required_config:
            if key not in self.config:
                raise ValueError(
                    f"Sink '{self.name}' 缺少必要配置參數: {key}"
                )

        # 設定可選參數的預設值
        for key, default in self.optional_config.items():
            self.config.setdefault(key, default)

    @abstractmethod
    def write(self, table: pw.Table) -> None:
        """寫入 Pathway Table。

        Args:
            table: 要寫入的 Pathway Table

        Raises:
            Exception: 寫入失敗時拋出異常
        """

    def setup(self) -> None:
        """初始化資源（可選）。

        在 write() 之前被呼叫，用於建立連線、建立資料表等。
        子類可以覆寫此方法。
        """

    def teardown(self) -> None:
        """清理資源（可選）。

        在 write() 之後被呼叫，用於關閉連線、釋放資源等。
        子類可以覆寫此方法。
        """

    def _setup_schema(self) -> None:
        """設定 schema（如果配置中有定義）。"""
        if 'schema' in self.config:
            from pwetl.utils.schema import SchemaParser
            parser = SchemaParser(self.config['schema'])
            self.schema_class = parser.parse()

    def _apply_schema(self, table: pw.Table) -> pw.Table:
        """應用 schema 到 table（如果有定義 schema）。

        Args:
            table: 輸入的 Pathway Table

        Returns:
            應用 schema 後的 Table，如果沒有定義 schema 則返回原 table
        """
        if self.schema_class is None:
            return table

        # 根據 schema 的類型注解進行選擇和轉換
        selections = {}
        for field, field_type in self.schema_class.__annotations__.items():
            # 取得原始類型（去除 Optional）
            import typing
            origin = typing.get_origin(field_type)
            if origin is typing.Union:
                # Optional[T] 是 Union[T, None]
                args = typing.get_args(field_type)
                actual_type = args[0] if args else field_type
            else:
                actual_type = field_type
            
            # 根據類型進行轉換
            if actual_type in (int, float, bool, str):
                selections[field] = pw.cast(actual_type, pw.this[field])
            else:
                # 其他類型（如 dict, datetime 等）直接選擇
                selections[field] = pw.this[field]
        
        return table.select(**selections)
