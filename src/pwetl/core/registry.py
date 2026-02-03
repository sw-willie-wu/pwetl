"""Registry and factory for sources and sinks."""
from typing import Dict, Type, Any
from pwetl.sources.base import BaseSource
from pwetl.sinks.base import BaseSink
from pwetl.utils.loader import DynamicLoader


# 全域 Registry：儲存內建和用戶註冊的 Source/Sink 類別
SOURCE_REGISTRY: Dict[str, Type[BaseSource]] = {}
SINK_REGISTRY: Dict[str, Type[BaseSink]] = {}


class SourceFactory:
    """Source 工廠類別。

    負責根據配置建立 Source 實例。
    """

    @staticmethod
    def create(name: str, config: Dict[str, Any]) -> BaseSource:
        """建立 Source 實例。

        Args:
            name: Source 名稱
            config: Source 配置，必須包含 'type' 欄位

        Returns:
            BaseSource 實例

        Raises:
            ValueError: 當配置缺少 'type' 欄位或 type 不存在時
            TypeError: 當自定義類別不是 BaseSource 的子類時
        """
        if 'type' not in config:
            raise ValueError(f"Source '{name}' 配置缺少 'type' 欄位")

        source_type = config['type']

        # 處理自定義 Source（動態載入）
        if source_type == 'custom':
            return SourceFactory._create_custom(name, config)

        # 處理內建 Source（從 Registry 載入）
        if source_type not in SOURCE_REGISTRY:
            raise ValueError(
                f"未知的 Source 類型: '{source_type}'\n"
                f"可用的類型: {', '.join(SOURCE_REGISTRY.keys())}\n"
                f"或使用 'custom' 類型並指定 'module' 和 'class'"
            )

        source_class = SOURCE_REGISTRY[source_type]
        return source_class(name=name, config=config)

    @staticmethod
    def _create_custom(name: str, config: Dict[str, Any]) -> BaseSource:
        """建立自定義 Source。

        Args:
            name: Source 名稱
            config: 必須包含 'module' 欄位，格式為 'module_path.ClassName'

        Returns:
            BaseSource 實例

        Raises:
            ValueError: 當配置缺少必要欄位或格式錯誤時
            TypeError: 當類別不是 BaseSource 的子類時
        """
        if 'module' not in config:
            raise ValueError(
                f"自定義 Source '{name}' 配置缺少 'module' 欄位"
            )

        module_spec = config['module']
        
        # 解析 module.ClassName 格式
        if '.' not in module_spec:
            raise ValueError(
                f"自定義 Source '{name}' 的 'module' 必須是 'module_path.ClassName' 格式"
            )
        
        parts = module_spec.rsplit('.', 1)
        module_path = parts[0]
        class_name = parts[1]

        # 動態載入類別
        source_class = DynamicLoader.load_class(module_path, class_name)

        # 驗證是否為 BaseSource 的子類
        if not issubclass(source_class, BaseSource):
            raise TypeError(
                f"類別 '{class_name}' 必須繼承自 BaseSource"
            )

        return source_class(name=name, config=config)


class SinkFactory:
    """Sink 工廠類別。

    負責根據配置建立 Sink 實例。
    """

    @staticmethod
    def create(name: str, config: Dict[str, Any]) -> BaseSink:
        """建立 Sink 實例。

        Args:
            name: Sink 名稱
            config: Sink 配置，必須包含 'type' 欄位

        Returns:
            BaseSink 實例

        Raises:
            ValueError: 當配置缺少 'type' 欄位或 type 不存在時
            TypeError: 當自定義類別不是 BaseSink 的子類時
        """
        if 'type' not in config:
            raise ValueError(f"Sink '{name}' 配置缺少 'type' 欄位")

        sink_type = config['type']

        # 處理自定義 Sink（動態載入）
        if sink_type == 'custom':
            return SinkFactory._create_custom(name, config)

        # 處理內建 Sink（從 Registry 載入）
        if sink_type not in SINK_REGISTRY:
            raise ValueError(
                f"未知的 Sink 類型: '{sink_type}'\n"
                f"可用的類型: {', '.join(SINK_REGISTRY.keys())}\n"
                f"或使用 'custom' 類型並指定 'module' 和 'class'"
            )

        sink_class = SINK_REGISTRY[sink_type]
        return sink_class(name=name, config=config)

    @staticmethod
    def _create_custom(name: str, config: Dict[str, Any]) -> BaseSink:
        """建立自定義 Sink。

        Args:
            name: Sink 名稱
            config: 必須包含 'module' 欄位，格式為 'module_path.ClassName'

        Returns:
            BaseSink 實例

        Raises:
            ValueError: 當配置缺少必要欄位或格式錯誤時
            TypeError: 當類別不是 BaseSink 的子類時
        """
        if 'module' not in config:
            raise ValueError(
                f"自定義 Sink '{name}' 配置缺少 'module' 欄位"
            )

        module_spec = config['module']
        
        # 解析 module.ClassName 格式
        if '.' not in module_spec:
            raise ValueError(
                f"自定義 Sink '{name}' 的 'module' 必須是 'module_path.ClassName' 格式"
            )
        
        parts = module_spec.rsplit('.', 1)
        module_path = parts[0]
        class_name = parts[1]

        # 動態載入類別
        sink_class = DynamicLoader.load_class(module_path, class_name)

        # 驗證是否為 BaseSink 的子類
        if not issubclass(sink_class, BaseSink):
            raise TypeError(
                f"類別 '{class_name}' 必須繼承自 BaseSink"
            )

        return sink_class(name=name, config=config)
