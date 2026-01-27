"""Database data sinks."""
from typing import Any, Dict
import pathway as pw
from pwetl.sinks.base import BaseSink


class DatabaseSink(BaseSink):
    """資料庫輸出。

    支援 PostgreSQL 和 MySQL。
    """

    required_config = ['db_type', 'host', 'database', 'table']
    optional_config = {
        'port': None,       # 預設端口由 db_type 決定
        'user': None,       # 使用者名稱
        'password': None,   # 密碼
    }

    # 支援的資料庫類型及其預設端口
    DB_DEFAULTS = {
        'postgresql': 5432,
        'mysql': 3306,
    }

    def __init__(self, name: str, config: Dict[str, Any]):
        """初始化資料庫 Sink。"""
        super().__init__(name, config)

        # 設定預設端口
        if self.config.get('port') is None:
            db_type = self.config['db_type']
            if db_type in self.DB_DEFAULTS:
                self.config['port'] = self.DB_DEFAULTS[db_type]
            else:
                raise ValueError(
                    f"不支援的資料庫類型: '{db_type}'\n"
                    f"支援的類型: {', '.join(self.DB_DEFAULTS.keys())}"
                )

    def write(self, table: pw.Table) -> None:
        """寫入資料庫。

        Args:
            table: 要寫入的 Pathway Table

        Raises:
            ValueError: 當資料庫類型不支援時
        """
        db_type = self.config['db_type']

        if db_type == 'postgresql':
            self._write_postgresql(table)
        elif db_type == 'mysql':
            self._write_mysql(table)
        else:
            raise ValueError(
                f"不支援的資料庫類型: '{db_type}'\n"
                f"支援的類型: {', '.join(self.DB_DEFAULTS.keys())}"
            )

    def _write_postgresql(self, table: pw.Table) -> None:
        """寫入 PostgreSQL。"""
        # 建立連線字串
        conn_str = self._build_postgres_conn_str()
        table_name = self.config['table']

        # 寫入資料
        pw.io.postgres.write(table, conn_str, table_name)

    def _write_mysql(self, table: pw.Table) -> None:
        """寫入 MySQL。"""
        # MySQL 需要特殊處理（Pathway 可能不直接支援）
        try:
            import mysql.connector
        except ImportError:
            raise ImportError(
                "MySQL 支援需要安裝額外套件：\n"
                "pip install 'pwetl[mysql]' 或 pip install mysql-connector-python"
            )

        # 注意：Pathway 可能不直接支援 MySQL 寫入
        # 這裡提供基本實作，可能需要調整
        raise NotImplementedError(
            "MySQL Sink 尚未完全實作。建議使用 PostgreSQL 或檔案輸出。"
        )

    def _build_postgres_conn_str(self) -> str:
        """建立 PostgreSQL 連線字串。"""
        user = self.config.get('user', 'postgres')
        password = self.config.get('password', '')
        host = self.config['host']
        port = self.config['port']
        database = self.config['database']

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
