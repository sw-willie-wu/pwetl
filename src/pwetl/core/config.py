"""配置載入器。"""
from pathlib import Path
from typing import Any, Dict, Union

import yaml
from pydantic import ValidationError

from pwetl.core.schema import BaseETLSchema
from pwetl.utils.env import EnvVarSubstitution


class ConfigLoader:
    """YAML 配置載入器。

    負責：
    1. 載入 YAML 配置檔案
    2. 替換環境變數
    3. 驗證配置結構（使用 Pydantic）
    """

    @staticmethod
    def load(config_path: Union[str, Path]) -> Dict[str, Any]:
        """載入並驗證配置檔案。

        Args:
            config_path: 配置檔案路徑

        Returns:
            解析後的配置字典

        Raises:
            FileNotFoundError: 當配置檔案不存在時
            ValueError: 當配置格式錯誤時
            yaml.YAMLError: 當 YAML 語法錯誤時
        """
        path = Path(config_path)

        # 檢查檔案是否存在
        if not path.exists():
            raise FileNotFoundError(f"配置檔案不存在: {config_path}")

        # 載入 YAML
        with open(path, "r", encoding="utf-8") as f:
            try:
                config_dict = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"YAML 語法錯誤: {e}") from e

        if config_dict is None:
            raise ValueError("配置檔案是空的")

        # 替換環境變數
        config_dict = EnvVarSubstitution.substitute(config_dict)

        # 使用 Pydantic 驗證配置結構
        try:
            config_model = BaseETLSchema(**config_dict)
        except ValidationError as e:
            # 格式化 Pydantic 錯誤訊息為更友善的格式
            error_messages = []
            for error in e.errors():
                loc = " -> ".join(str(x) for x in error["loc"])
                msg = error["msg"]
                error_messages.append(f"  - {loc}: {msg}")

            raise ValueError(
                "配置驗證失敗:\n" + "\n".join(error_messages)
            ) from e

        # 轉換為字典格式（保持向後兼容）
        return config_model.to_dict()

    @staticmethod
    def load_as_model(config_path: Union[str, Path]) -> BaseETLSchema:
        """載入配置並回傳 Pydantic 模型。

        Args:
            config_path: 配置檔案路徑

        Returns:
            BaseETLSchema 模型實例

        Raises:
            FileNotFoundError: 當配置檔案不存在時
            ValueError: 當配置格式錯誤時
        """
        path = Path(config_path)

        # 檢查檔案是否存在
        if not path.exists():
            raise FileNotFoundError(f"配置檔案不存在: {config_path}")

        # 載入 YAML
        with open(path, "r", encoding="utf-8") as f:
            try:
                config_dict = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"YAML 語法錯誤: {e}") from e

        if config_dict is None:
            raise ValueError("配置檔案是空的")

        # 替換環境變數
        config_dict = EnvVarSubstitution.substitute(config_dict)

        # 使用 Pydantic 驗證配置結構
        try:
            return BaseETLSchema(**config_dict)
        except ValidationError as e:
            # 格式化 Pydantic 錯誤訊息
            error_messages = []
            for error in e.errors():
                loc = " -> ".join(str(x) for x in error["loc"])
                msg = error["msg"]
                error_messages.append(f"  - {loc}: {msg}")

            raise ValueError(
                "配置驗證失敗:\n" + "\n".join(error_messages)
            ) from e
