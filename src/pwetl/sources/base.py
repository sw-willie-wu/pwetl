"""Base class for all data sources."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import pathway as pw


class BaseSource(ABC):
    """所有 Source 的抽象基類。

    所有自定義 Source 都必須繼承此類別並實作 read() 方法。
    """

    # 子類可以覆寫這些屬性來定義必要和可選的配置參數
    required_config: List[str] = []
    optional_config: Dict[str, Any] = {}

    def __init__(self, name: str, config: Dict[str, Any]):
        """初始化 Source。

        Args:
            name: Source 的名稱，用於在 Pipeline 中識別
            config: Source 的配置參數
        """
        self.name = name
        self.config = config
        self._validate_config()

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
                    f"Source '{self.name}' 缺少必要配置參數: {key}"
                )

        # 設定可選參數的預設值
        for key, default in self.optional_config.items():
            self.config.setdefault(key, default)

    def _validate_schema_data(self, data: List[Dict[str, Any]], schema_config: Dict) -> None:
        """驗證資料是否符合 schema。
        
        Args:
            data: 資料列表
            schema_config: Schema 配置
            
        Raises:
            ValueError: 當資料不符合 schema 時
        """
        if not data or not schema_config:
            return
            
        # 檢查第一筆資料作為樣本
        sample = data[0]
        errors = []
        
        for field_name, type_def in schema_config.items():
            # 跳過嵌套物件（dict）
            if isinstance(type_def, dict):
                continue
                
            value = sample.get(field_name)
            
            # 檢查是否為 null 且不是 Optional
            if value is None:
                # 檢查是否為 Optional 型態
                is_optional = (
                    isinstance(type_def, str) and 
                    (type_def.endswith('?') or type_def.startswith('Optional['))
                )
                
                if not is_optional:
                    errors.append(
                        f"欄位 '{field_name}' 的值為 null，但 schema 定義為 '{type_def}' (非 Optional)\n"
                        f"  提示: 如果允許 null 值，請使用 '{type_def}?' 或 'Optional[{type_def}]'"
                    )
        
        if errors:
            error_msg = "資料驗證失敗:\n" + "\n".join(errors)
            error_msg += f"\n\n檢查的資料樣本: {sample}"
            raise ValueError(error_msg)

    @abstractmethod
    def read(self) -> pw.Table:
        """讀取資料並回傳 Pathway Table。

        Returns:
            pw.Table: 包含資料的 Pathway Table

        Raises:
            Exception: 讀取失敗時拋出異常
        """

    def setup(self) -> None:
        """初始化資源（可選）。

        在 read() 之前被呼叫，用於建立連線、載入資源等。
        子類可以覆寫此方法。
        """

    def teardown(self) -> None:
        """清理資源（可選）。

        在 read() 之後被呼叫，用於關閉連線、釋放資源等。
        子類可以覆寫此方法。
        """
