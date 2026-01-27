"""ETL Pipeline。"""
from typing import Dict
import pathway as pw
from pwetl.sources.base import BaseSource
from pwetl.sinks.base import BaseSink
from pwetl.transforms.base import BaseTransform


class Pipeline:
    """ETL Pipeline。

    負責編排 Source → Transform → Sink 的執行流程。
    """

    def __init__(
        self,
        sources: Dict[str, BaseSource],
        transform: BaseTransform,
        sinks: Dict[str, BaseSink],
        verbose: bool = False,
    ):
        """初始化 Pipeline。

        Args:
            sources: Source 實例字典，格式為 {name: BaseSource}
            transform: Transform 實例
            sinks: Sink 實例字典，格式為 {name: BaseSink}
            verbose: 是否顯示詳細輸出
        """
        self.sources = sources
        self.transform = transform
        self.sinks = sinks
        self.verbose = verbose

    def run(self) -> None:
        """執行 Pipeline。

        執行順序：
        1. 初始化所有組件（setup）
        2. 從所有 Sources 讀取資料
        3. Transform 處理資料
        4. 寫入所有 Sinks
        5. 執行 Pathway
        6. 清理所有組件（teardown）

        Raises:
            RuntimeError: 當任何階段失敗時
        """
        try:
            # 階段 1: 初始化
            if self.verbose:
                print("🔧 初始化組件...")
            self._setup_all()

            # 階段 2: Source - 讀取資料
            if self.verbose:
                print(f"📥 從 {len(self.sources)} 個 Source 讀取資料...")
            tables = self._read_sources()

            # 階段 3: Transform - 處理資料
            if self.verbose:
                print("⚙️  執行 Transform...")
            result_tables = self._transform(tables)

            # 階段 4: Sink - 寫入資料
            if self.verbose:
                print(f"📤 寫入到 {len(self.sinks)} 個 Sink...")
            self._write_sinks(result_tables)

            # 執行 Pathway
            if self.verbose:
                print("🚀 執行 Pathway...")
            pw.run()

            if self.verbose:
                print("✅ Pipeline 執行完成")

        finally:
            # 階段 5: 清理
            if self.verbose:
                print("🧹 清理資源...")
            self._teardown_all()

    def _setup_all(self) -> None:
        """初始化所有組件。"""
        # 初始化 Sources
        for name, source in self.sources.items():
            try:
                source.setup()
            except Exception as e:
                raise RuntimeError(
                    f"Source '{name}' 初始化失敗: {e}"
                ) from e

        # 初始化 Transform
        try:
            self.transform.setup()
        except Exception as e:
            raise RuntimeError(f"Transform 初始化失敗: {e}") from e

        # 初始化 Sinks
        for name, sink in self.sinks.items():
            try:
                sink.setup()
            except Exception as e:
                raise RuntimeError(
                    f"Sink '{name}' 初始化失敗: {e}"
                ) from e

    def _read_sources(self) -> Dict[str, pw.Table]:
        """從所有 Sources 讀取資料。

        Returns:
            資料表字典，格式為 {source_name: pw.Table}

        Raises:
            RuntimeError: 當任何 Source 讀取失敗時
        """
        tables = {}

        for name, source in self.sources.items():
            try:
                if self.verbose:
                    print(f"  - 讀取 Source '{name}'...")
                tables[name] = source.read()
            except Exception as e:
                raise RuntimeError(
                    f"Source '{name}' 讀取失敗: {e}"
                ) from e

        return tables

    def _transform(self, tables: Dict[str, pw.Table]) -> Dict[str, pw.Table]:
        """執行 Transform。

        Args:
            tables: 輸入資料表字典

        Returns:
            輸出資料表字典

        Raises:
            RuntimeError: 當 Transform 處理失敗時
        """
        try:
            result_tables = self.transform.transform(tables)

            # 驗證回傳值
            if not isinstance(result_tables, dict):
                raise TypeError(
                    "Transform 必須回傳 Dict[str, pw.Table]，"
                    f"但回傳了 {type(result_tables)}"
                )

            return result_tables

        except Exception as e:
            raise RuntimeError(f"Transform 處理失敗: {e}") from e

    def _write_sinks(self, result_tables: Dict[str, pw.Table]) -> None:
        """寫入所有 Sinks。

        Args:
            result_tables: 要寫入的資料表字典

        Raises:
            RuntimeError: 當任何 Sink 寫入失敗時
        """
        for name, sink in self.sinks.items():
            try:
                if name not in result_tables:
                    raise ValueError(
                        f"Transform 沒有產生 Sink '{name}' 需要的資料表。\n"
                        f"可用的資料表: {', '.join(result_tables.keys())}"
                    )

                if self.verbose:
                    print(f"  - 寫入 Sink '{name}'...")

                table = result_tables[name]
                sink.write(table)

            except Exception as e:
                raise RuntimeError(
                    f"Sink '{name}' 寫入失敗: {e}"
                ) from e

    def _teardown_all(self) -> None:
        """清理所有組件。"""
        # 清理 Sources
        for name, source in self.sources.items():
            try:
                source.teardown()
            except Exception as e:
                if self.verbose:
                    print(f"⚠️  Source '{name}' 清理失敗: {e}")

        # 清理 Transform
        try:
            self.transform.teardown()
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Transform 清理失敗: {e}")

        # 清理 Sinks
        for name, sink in self.sinks.items():
            try:
                sink.teardown()
            except Exception as e:
                if self.verbose:
                    print(f"⚠️  Sink '{name}' 清理失敗: {e}")
