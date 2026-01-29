"""配置載入器。"""
from pathlib import Path
from typing import Any, Dict, List, Union
from pwetl.utils.env import EnvVarSubstitution


class ConfigLoader:
    """YAML 配置載入器。

    負責：
    1. 載入 YAML 配置檔案
    2. 替換環境變數
    3. 驗證配置結構
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
        with open(path, 'r', encoding='utf-8') as f:
            try:
                config = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"YAML 語法錯誤: {e}")

        if config is None:
            raise ValueError("配置檔案是空的")

        # 替換環境變數
        config = EnvVarSubstitution.substitute(config)

        # 驗證配置結構
        ConfigLoader._validate(config)

        return config

    @staticmethod
    def _validate(config: Dict[str, Any]) -> None:
        """驗證配置結構。

        Args:
            config: 配置字典

        Raises:
            ValueError: 當配置結構錯誤時
        """
        # 檢查必要欄位
        if 'sources' not in config:
            raise ValueError("配置缺少 'sources' 欄位")

        if 'transform' not in config:
            raise ValueError("配置缺少 'transform' 欄位")

        if 'sinks' not in config:
            raise ValueError("配置缺少 'sinks' 欄位")

        # 驗證 sources
        ConfigLoader._validate_sources(config['sources'])

        # 驗證 transform
        ConfigLoader._validate_transform(config['transform'])

        # 驗證 sinks
        ConfigLoader._validate_sinks(config['sinks'])

    @staticmethod
    def _validate_sources(sources: Any) -> None:
        """驗證 sources 配置。

        Args:
            sources: sources 配置

        Raises:
            ValueError: 當配置格式錯誤時
        """
        if not isinstance(sources, list):
            raise ValueError("'sources' 必須是列表")

        if len(sources) == 0:
            raise ValueError("'sources' 不能為空")

        source_names = set()

        for i, source in enumerate(sources):
            if not isinstance(source, dict):
                raise ValueError(f"sources[{i}] 必須是字典")

            # 檢查必要欄位
            if 'name' not in source:
                raise ValueError(f"sources[{i}] 缺少 'name' 欄位")

            if 'type' not in source:
                raise ValueError(
                    f"sources[{i}] (name='{source.get('name')}') 缺少 'type' 欄位"
                )

            # 檢查 name 是否重複
            name = source['name']
            if name in source_names:
                raise ValueError(f"Source name 重複: '{name}'")
            source_names.add(name)

    @staticmethod
    def _validate_transform(transform: Any) -> None:
        """驗證 transform 配置。

        Args:
            transform: transform 配置

        Raises:
            ValueError: 當配置格式錯誤時
        """
        if not isinstance(transform, str):
            raise ValueError(
                "'transform' 必須是字串（格式: 'module.ClassName'）"
            )

        if '.' not in transform:
            raise ValueError(
                f"'transform' 格式錯誤: '{transform}'\n"
                f"正確格式: 'module.ClassName' 或 'module.py.ClassName'"
            )

    @staticmethod
    def _validate_sinks(sinks: Any) -> None:
        """驗證 sinks 配置。

        Args:
            sinks: sinks 配置

        Raises:
            ValueError: 當配置格式錯誤時
        """
        if not isinstance(sinks, list):
            raise ValueError("'sinks' 必須是列表")

        if len(sinks) == 0:
            raise ValueError("'sinks' 不能為空")

        sink_names = set()

        for i, sink in enumerate(sinks):
            if not isinstance(sink, dict):
                raise ValueError(f"sinks[{i}] 必須是字典")

            # 檢查必要欄位
            if 'name' not in sink:
                raise ValueError(f"sinks[{i}] 缺少 'name' 欄位")

            if 'type' not in sink:
                raise ValueError(
                    f"sinks[{i}] (name='{sink.get('name')}') 缺少 'type' 欄位"
                )

            # 檢查 name 是否重複
            name = sink['name']
            if name in sink_names:
                raise ValueError(f"Sink name 重複: '{name}'")
            sink_names.add(name)
