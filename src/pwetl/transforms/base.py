"""Base class for all transforms."""
from abc import ABC, abstractmethod
from typing import Dict
import pathway as pw


class BaseTransform(ABC):
    """所有 Transform 的抽象基類。

    所有自定義 Transform 都必須繼承此類別並實作 transform() 方法。
    """

    @abstractmethod
    def transform(self, tables: Dict[str, pw.Table]) -> Dict[str, pw.Table]:
        """轉換資料。

        Args:
            tables: 輸入的資料表，格式為 Dict[source_name, pw.Table]

        Returns:
            Dict[sink_name, pw.Table]: 輸出的資料表

        Raises:
            Exception: 轉換失敗時拋出異常
        """

    def setup(self) -> None:
        """初始化資源（可選）。

        在 transform() 之前被呼叫，用於載入模型、建立連線等。
        子類可以覆寫此方法。
        """

    def teardown(self) -> None:
        """清理資源（可選）。

        在 transform() 之後被呼叫，用於釋放資源、關閉連線等。
        子類可以覆寫此方法。
        """
