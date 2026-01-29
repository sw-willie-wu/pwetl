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
