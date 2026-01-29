"""Database data sources."""
from typing import Any, Dict, Optional, Type
import pathway as pw
from pwetl.sources.base import BaseSource
from pwetl.utils.schema import SchemaParser


class DatabaseSource(BaseSource):
    """資料庫資料源。

    支援 PostgreSQL 和 MySQL。
    """

    required_config = ['db_type', 'host', 'database', 'table']
    optional_config = {
        'port': None,       # 預設端口由 db_type 決定
        'user': None,       # 使用者名稱
        'password': None,   # 密碼
        'query': None,      # 自訂 SQL 查詢（優先於 table）
        'schema': None,     # 可選的 Schema
    }

    # 支援的資料庫類型及其預設端口
    DB_DEFAULTS = {
        'postgresql': 5432,
        'mysql': 3306,
    }

    def __init__(self, name: str, config: Dict[str, Any]):
        """初始化資料庫 Source。"""
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

    def read(self) -> pw.Table:
        """從資料庫讀取資料。

        Returns:
            pw.Table: 包含資料的 Pathway Table

        Raises:
            ValueError: 當資料庫類型不支援時
        """
        db_type = self.config['db_type']

        if db_type == 'postgresql':
            return self._read_postgresql()
        if db_type == 'mysql':
            return self._read_mysql()
        raise ValueError(
            f"不支援的資料庫類型: '{db_type}'\n"
            f"支援的類型: {', '.join(self.DB_DEFAULTS.keys())}"
        )

    def _read_postgresql(self) -> pw.Table:
        """從 PostgreSQL 讀取資料。"""
        # 建立連線字串
        conn_str = self._build_postgres_conn_str()

        # 取得查詢
        query = self._get_query()

        # 解析 Schema
        schema = self._get_schema()

        # 讀取資料
        if schema:
            return pw.io.postgres.read(
                conn_str,
                query=query,
                schema=schema,
            )
        return pw.io.postgres.read(
            conn_str,
            query=query,
        )

    def _read_mysql(self) -> pw.Table:
        """從 MySQL 讀取資料。"""
        # MySQL 需要使用 connector
        try:
            import mysql.connector  # pylint: disable=unused-import
        except ImportError as exc:
            raise ImportError(
                "MySQL 支援需要安裝額外套件：\n"
                "pip install 'pwetl[mysql]' 或 pip install mysql-connector-python"
            ) from exc

        # 建立連線配置
        conn_config = {
            'host': self.config['host'],
            'port': self.config['port'],
            'database': self.config['database'],
            'user': self.config.get('user'),
            'password': self.config.get('password'),
        }

        # 取得查詢
        query = self._get_query()

        # 建立連線
        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor(dictionary=True)

        try:
            # 執行查詢
            cursor.execute(query)
            data = cursor.fetchall()

            # 轉換為 Pathway Table（透過 JSONL）
            return self._data_to_table(data)

        finally:
            cursor.close()
            conn.close()

    def _build_postgres_conn_str(self) -> str:
        """建立 PostgreSQL 連線字串。"""
        user = self.config.get('user', 'postgres')
        password = self.config.get('password', '')
        host = self.config['host']
        port = self.config['port']
        database = self.config['database']

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    def _get_query(self) -> str:
        """取得 SQL 查詢。

        Returns:
            SQL 查詢字串
        """
        # 優先使用自訂查詢
        query = self.config.get('query')
        if query:
            return query

        # 否則使用簡單的 SELECT * FROM table
        table = self.config['table']
        return f"SELECT * FROM {table}"

    def _get_schema(self) -> Optional[Type[pw.Schema]]:
        """取得 Schema。

        Returns:
            Pathway Schema 類別，如果沒有指定則回傳 None
        """
        schema_config = self.config.get('schema')
        if schema_config:
            return SchemaParser.parse(schema_config)
        return None

    def _data_to_table(self, data: list) -> pw.Table:
        """將資料轉換為 Pathway Table。"""
        import tempfile
        import json
        import os

        # 建立暫存檔案
        fd, temp_path = tempfile.mkstemp(suffix='.jsonl', text=True)

        try:
            # 寫入資料
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')

            # 解析 Schema
            schema = self._get_schema()

            # 讀取為 Pathway Table
            if schema:
                table = pw.io.jsonlines.read(temp_path, schema=schema, mode='static')
            else:
                table = pw.io.jsonlines.read(temp_path, mode='static')

            return table

        finally:
            pass
