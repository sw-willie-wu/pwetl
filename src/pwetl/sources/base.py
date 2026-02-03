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
                raise ValueError(f"Source '{self.name}' 缺少必要配置參數: {key}")

        # 設定可選參數的預設值
        for key, default in self.optional_config.items():
            self.config.setdefault(key, default)

    def _get_validation_mode(self) -> str:
        """取得驗證模式。

        Returns:
            驗證模式: 'sample' (預設), 'strict', 'none'
        """
        return self.config.get("validation_mode", "sample")

    def _process_data_with_validation(
        self, data: List[Dict[str, Any]], schema_config: Dict
    ) -> List[Dict[str, Any]]:
        """根據 validation_mode 處理資料。

        這是統一的入口，自動根據配置選擇驗證策略：
        - none: 不處理，直接返回
        - sample: 驗證採樣，顯示警告，返回原始資料
        - strict: 全部驗證並標準化，失敗則拋出錯誤

        Args:
            data: 資料列表
            schema_config: Schema 配置

        Returns:
            處理後的資料列表（strict 模式下會標準化）

        Raises:
            ValueError: strict 模式下驗證失敗
        """
        validation_mode = self._get_validation_mode()

        # none 模式：不處理
        if validation_mode == "none" or not schema_config:
            return data

        if not data:
            return data

        import warnings
        from pydantic import ValidationError
        from pwetl.utils.schema import SchemaParser

        # 建立 Pydantic 模型
        try:
            pydantic_model = SchemaParser.create_pydantic_model(schema_config)
        except Exception as e:
            warnings.warn(f"無法建立驗證模型: {e}", UserWarning)
            return data

        # strict 模式：驗證並轉換所有資料
        if validation_mode == "strict":
            normalized_data = []
            errors = []

            for idx, row in enumerate(data):
                try:
                    validated = pydantic_model(**row)
                    # 轉換為基本型別（UUID→str, Decimal→float 等）
                    normalized_data.append(validated.model_dump())
                except ValidationError as e:
                    errors.append({"row": idx + 1, "errors": e.errors()})

            if errors:
                self._show_validation_errors(errors, mode="strict")
                raise ValueError(
                    f"strict 模式下發現 {len(errors)} 行資料驗證失敗，請修正資料"
                )

            return normalized_data

        # sample 模式：只驗證，不轉換
        self._validate_schema_data_sample(data, pydantic_model)
        return data

    def _validate_schema_data_sample(
        self, data: List[Dict[str, Any]], pydantic_model
    ) -> None:
        """採樣驗證資料（原有邏輯）。

        Args:
            data: 資料列表
            pydantic_model: Pydantic 模型
        """
        from pydantic import ValidationError

        if not data:
            return

        # 驗證所有資料
        errors = []
        max_errors_to_show = 10

        for idx, row in enumerate(data):
            try:
                pydantic_model(**row)
            except ValidationError as e:
                errors.append({"row": idx + 1, "errors": e.errors()})

                if len(errors) >= max_errors_to_show:
                    break

        # 如果發現錯誤，顯示警告
        if errors:
            self._show_validation_errors(errors, mode="sample")

    def _show_validation_errors(self, errors: List[Dict], mode: str = "sample") -> None:
        """顯示驗證錯誤。

        Args:
            errors: 錯誤列表
            mode: 驗證模式
        """
        import warnings

        if mode == "strict":
            warning_parts = [
                f"\n❌ 資料驗證失敗 (strict 模式): 發現 {len(errors)} 行資料不符合 schema",
                f"   strict 模式要求所有資料必須通過驗證\n",
            ]
        else:
            warning_parts = [
                f"\n⚠️  資料驗證警告: 發現 {len(errors)} 行資料不符合 schema",
                f"   這些行在執行時可能會被 Pathway 過濾掉\n",
            ]

            # 顯示錯誤詳情
            for error_info in errors[:5]:  # 最多顯示前 5 行的詳細錯誤
                warning_parts.append(f"   第 {error_info['row']} 行:")
                for err in error_info["errors"][:3]:  # 每行最多顯示 3 個錯誤
                    field = ".".join(str(x) for x in err["loc"])
                    msg = err["msg"]
                    warning_parts.append(f"     - {field}: {msg}")
                if len(error_info["errors"]) > 3:
                    warning_parts.append(
                        f"     ... (還有 {len(error_info['errors']) - 3} 個錯誤)"
                    )

            if len(errors) > 5:
                warning_parts.append(f"\n   ... (還有 {len(errors) - 5} 行有錯誤)")

            if mode == "sample":
                warning_parts.append("\n   💡 建議:")
                warning_parts.append(
                    "      - 將可為 null 的欄位改為 Optional (例如: 'Address: str?')"
                )
                warning_parts.append(
                    "      - 或在配置中添加 'validation_mode: none' 跳過檢查"
                )
                warning_parts.append(
                    "      - 或使用 'validation_mode: strict' 強制驗證所有資料\n"
                )

            warnings.warn("\n".join(warning_parts), UserWarning, stacklevel=4)

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
