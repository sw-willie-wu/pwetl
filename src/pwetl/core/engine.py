"""ETL Engine。"""

import sys
from pathlib import Path
from typing import Union

from pwetl.core.config import ConfigLoader
from pwetl.core.pipeline import Pipeline
from pwetl.core.registry import SinkFactory, SourceFactory
from pwetl.utils.env import load_env_file
from pwetl.utils.loader import TransformLoader
from pwetl.utils.logger import get_logger


LOGGER = get_logger()


class ETLEngine:
    """ETL Engine。

    負責：
    1. 載入配置
    2. 建立 Pipeline
    3. 執行 ETL 流程
    """

    def __init__(
        self,
        config_path: Union[str, Path],
        env_file: Union[str, Path, None] = None,
        verbose: bool = False,
    ):
        """初始化 ETL Engine。

        Args:
            config_path: 配置檔案路徑
            env_file: .env 檔案路徑，如果為 None 則自動尋找
            verbose: 是否顯示詳細輸出
        """
        self.config_path = Path(config_path).resolve()
        self.env_file = env_file
        self.verbose = verbose
        self.config: dict | None = None
        self.pipeline: Pipeline | None = None

        # 將配置檔案所在目錄加入 Python 路徑，以便載入相對模組
        config_dir = str(self.config_path.parent)
        if config_dir not in sys.path:
            sys.path.insert(0, config_dir)

    def execute(self) -> None:
        """執行 ETL 流程。

        Raises:
            Exception: 當執行失敗時
        """
        try:
            LOGGER.debug("Start ETL Engine execution...")
            LOGGER.debug("Loading environment variables...")
            self._load_env()

            # 載入配置
            LOGGER.debug("Loading yaml configuration...")
            self._load_config()

            # 建立 Pipeline
            LOGGER.debug("Initializing Pipeline structure...")
            self._build_pipeline()

            # 執行 Pipeline
            if self.pipeline is None:
                raise RuntimeError("Pipeline 尚未建立，無法執行。")
            self.pipeline.run()

        except Exception as e:
            LOGGER.error("Execution failed: %s", e)
            if self.verbose:
                import traceback

                LOGGER.error("\nTraceback:")
                traceback.print_exc()
            raise

    def dry_run(self) -> None:
        """乾跑模式：只驗證配置，不執行。

        Raises:
            Exception: 當驗證失敗時
        """
        try:
            print("🔍 驗證模式...")

            # 載入環境變數
            print("  ✓ 載入環境變數")
            self._load_env()

            # 載入配置
            print("  ✓ 載入配置")
            self._load_config()

            # 建立 Pipeline（驗證所有組件都能正確建立）
            print("  ✓ 驗證 Pipeline 配置")
            self._build_pipeline()

            print("\n✅ 配置驗證通過")

        except Exception as e:
            print(f"\n❌ 驗證失敗: {e}")
            if self.verbose:
                import traceback

                print("\n詳細錯誤訊息:")
                traceback.print_exc()
            raise

    def _load_env(self) -> None:
        """載入環境變數。"""
        if self.env_file:
            load_env_file(self.env_file)
        else:
            # 自動尋找 .env 檔案
            load_env_file(".env")

    def _load_config(self) -> None:
        """載入配置。

        Raises:
            Exception: 當配置載入失敗時
        """
        try:
            self.config = ConfigLoader.load(self.config_path)
        except Exception as e:
            raise RuntimeError(f"配置載入失敗: {e}") from e

    def _build_pipeline(self) -> None:
        """建立 Pipeline。

        Raises:
            RuntimeError: 當 Pipeline 建立失敗時
        """
        try:
            if self.config is None:
                raise RuntimeError("配置尚未載入，無法建立 Pipeline。")

            # 建立 Sources
            sources = {}
            for source_config in self.config["sources"]:
                name = source_config["name"]
                sources[name] = SourceFactory.create(name, source_config)
            LOGGER.debug(
                "  Find %d Sources: %s", len(sources), ", ".join(sources.keys())
            )
            # 載入 Transform
            transform = TransformLoader.load(self.config["transform"])
            LOGGER.debug("  Find Transform module: %s", self.config["transform"])

            # 建立 Sinks
            sinks = {}
            for sink_config in self.config["sinks"]:
                name = sink_config["name"]
                sinks[name] = SinkFactory.create(name, sink_config)
            LOGGER.debug(
                "  Find %d Sinks: %s", len(sinks), ", ".join(sinks.keys())
            )

            # 建立 Pipeline
            self.pipeline = Pipeline(
                sources=sources,
                transform=transform,
                sinks=sinks,
                verbose=self.verbose,
            )
            # LOGGER.debug("Start build Pipeline flow...")

        except Exception as e:
            raise RuntimeError(f"Build Pipeline failed: {e}") from e
