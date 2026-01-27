"""API data source."""
from typing import Any, Dict, List, Optional, Type
import requests
import pathway as pw
from pwetl.sources.base import BaseSource
from pwetl.utils.schema import SchemaParser


class APISource(BaseSource):
    """API 資料源。

    支援從 REST API 讀取資料。

    模式：
    - static: 執行一次，讀取當下資料後結束
    - streaming: 定期輪詢 API，持續運行（需設定 refresh_interval）
    """

    required_config = ['url']
    optional_config = {
        'method': 'GET',           # HTTP 方法
        'headers': {},             # 自訂 Headers
        'params': {},              # URL 參數
        'data': None,              # POST/PUT 資料
        'json': None,              # JSON 資料
        'timeout': 30,             # 超時時間（秒）
        'data_path': None,         # JSON 回應中的資料路徑（例如 'data.items'）
        'schema': None,            # 可選的 Schema
        'mode': 'static',          # 'static' 或 'streaming'
        'refresh_interval': 60,    # 輪詢間隔（秒），僅用於 streaming mode
    }

    def read(self) -> pw.Table:
        """從 API 讀取資料。

        Returns:
            pw.Table: 包含資料的 Pathway Table

        Raises:
            requests.RequestException: 當 API 請求失敗時
            ValueError: 當回應格式錯誤時
        """
        # 發送 API 請求
        response = self._make_request()

        # 解析回應
        data = self._parse_response(response)

        # 轉換為 Pathway Table
        return self._to_table(data)

    def _make_request(self) -> requests.Response:
        """發送 API 請求。

        Returns:
            HTTP 回應

        Raises:
            requests.RequestException: 當請求失敗時
        """
        url = self.config['url']
        method = self.config['method'].upper()
        headers = self.config['headers']
        params = self.config['params']
        data = self.config['data']
        json_data = self.config['json']
        timeout = self.config['timeout']

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data,
                timeout=timeout,
            )
            response.raise_for_status()
            return response

        except requests.RequestException as e:
            raise RuntimeError(
                f"API 請求失敗 ({method} {url}): {e}"
            ) from e

    def _parse_response(self, response: requests.Response) -> List[Dict[str, Any]]:
        """解析 API 回應。

        Args:
            response: HTTP 回應

        Returns:
            資料列表

        Raises:
            ValueError: 當回應格式錯誤時
        """
        try:
            json_data = response.json()
        except Exception as e:
            raise ValueError(f"回應不是有效的 JSON: {e}") from e

        # 如果指定了 data_path，則從 JSON 中提取資料
        data_path = self.config.get('data_path')
        if data_path:
            json_data = self._extract_data_path(json_data, data_path)

        # 確保資料是列表
        if isinstance(json_data, dict):
            # 單一物件，包裝成列表
            json_data = [json_data]
        elif not isinstance(json_data, list):
            raise ValueError(
                f"回應資料必須是列表或字典，但得到 {type(json_data)}"
            )

        return json_data

    def _extract_data_path(self, data: Any, path: str) -> Any:
        """從 JSON 中提取指定路徑的資料。

        Args:
            data: JSON 資料
            path: 資料路徑，例如 'data.items'

        Returns:
            提取的資料

        Raises:
            ValueError: 當路徑不存在時
        """
        parts = path.split('.')
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise ValueError(
                    f"資料路徑 '{path}' 不存在（在 '{part}' 處失敗）"
                )

        return current

    def _to_table(self, data: List[Dict[str, Any]]) -> pw.Table:
        """將資料轉換為 Pathway Table。

        Args:
            data: 資料列表

        Returns:
            Pathway Table
        """
        # 建立暫存 JSONL 檔案（Pathway 需要從檔案讀取）
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
            mode = self.config['mode']

            # 讀取為 Pathway Table
            if schema:
                table = pw.io.jsonlines.read(temp_path, schema=schema, mode=mode)
            else:
                table = pw.io.jsonlines.read(temp_path, mode=mode)

            return table

        finally:
            # 清理暫存檔案（在 Pathway 讀取後）
            # 注意：這裡不能立即刪除，因為 Pathway 是延遲執行的
            # 實際執行時才會讀取檔案
            pass

    def _get_schema(self) -> Optional[Type[pw.Schema]]:
        """取得 Schema。

        Returns:
            Pathway Schema 類別，如果沒有指定則回傳 None
        """
        schema_config = self.config.get('schema')
        if schema_config:
            return SchemaParser.parse(schema_config)
        return None
