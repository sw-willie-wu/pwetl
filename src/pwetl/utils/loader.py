"""動態載入工具。"""
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Type


class DynamicLoader:
    """動態載入類別的工具。

    支援從檔案路徑或 package 路徑載入類別。
    """

    @staticmethod
    def load_class(module_path: str, class_name: str) -> Type:
        """從模組載入類別。

        Args:
            module_path: 模組路徑，可以是：
                - 檔案路徑: 'my_sources.py' 或 'path/to/my_sources.py'
                - Package 路徑: 'my_package.sources'
            class_name: 類別名稱

        Returns:
            載入的類別

        Raises:
            ImportError: 當模組或類別不存在時
            ValueError: 當路徑格式錯誤時
        """
        if module_path.endswith('.py'):
            return DynamicLoader._load_from_file(module_path, class_name)
        return DynamicLoader._load_from_package(module_path, class_name)

    @staticmethod
    def _load_from_file(file_path: str, class_name: str) -> Type:
        """從檔案載入類別。

        Args:
            file_path: Python 檔案路徑
            class_name: 類別名稱

        Returns:
            載入的類別

        Raises:
            ImportError: 當檔案或類別不存在時
        """
        path = Path(file_path)

        if not path.exists():
            raise ImportError(f"檔案不存在: {file_path}")

        # 建立模組名稱（移除 .py 後綴）
        module_name = path.stem

        # 載入模組
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"無法載入模組: {file_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # 取得類別
        if not hasattr(module, class_name):
            raise ImportError(
                f"模組 '{module_name}' 中找不到類別 '{class_name}'"
            )

        return getattr(module, class_name)

    @staticmethod
    def _load_from_package(module_path: str, class_name: str) -> Type:
        """從 package 載入類別。

        Args:
            module_path: Package 路徑，例如 'my_package.sources'
            class_name: 類別名稱

        Returns:
            載入的類別

        Raises:
            ImportError: 當模組或類別不存在時
        """
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError as exc:
            raise ImportError(f"找不到模組: {module_path}") from exc

        if not hasattr(module, class_name):
            raise ImportError(
                f"模組 '{module_path}' 中找不到類別 '{class_name}'"
            )

        return getattr(module, class_name)


class TransformLoader:
    """Transform 載入工具。"""

    @staticmethod
    def load(transform_config: str):
        """從配置載入 Transform。

        Args:
            transform_config: Transform 配置，格式為 'module.ClassName'
                例如：'transforms.MyTransform' 或 'my_transforms.py.MyTransform'

        Returns:
            BaseTransform 實例

        Raises:
            ValueError: 當配置格式錯誤時
            ImportError: 當模組或類別不存在時
            TypeError: 當類別不是 BaseTransform 的子類時
        """
        from pwetl.transforms import BaseTransform

        if '.' not in transform_config:
            raise ValueError(
                f"Transform 配置格式錯誤: '{transform_config}'\n"
                f"正確格式: 'module.ClassName' 或 'module.py.ClassName'"
            )

        # 分割模組路徑和類別名稱
        parts = transform_config.rsplit('.', 1)
        if len(parts) != 2:
            raise ValueError(
                f"Transform 配置格式錯誤: '{transform_config}'\n"
                f"正確格式: 'module.ClassName' 或 'module.py.ClassName'"
            )

        module_path, class_name = parts

        # 載入類別
        transform_class = DynamicLoader.load_class(module_path, class_name)

        # 驗證是否為 BaseTransform 的子類
        if not issubclass(transform_class, BaseTransform):
            raise TypeError(
                f"類別 '{class_name}' 必須繼承自 BaseTransform"
            )

        # 建立實例
        return transform_class()
