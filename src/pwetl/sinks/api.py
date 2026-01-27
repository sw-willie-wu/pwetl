"""API data sink."""
import time
from typing import Any, Dict, List
import requests
import pathway as pw
from pwetl.sinks.base import BaseSink


class APISink(BaseSink):
    """API 輸出。

    將資料 POST 到 API endpoint。
    支援：
    - POST JSON 數據
    - 自訂 Headers
    - 錯誤重試
    """

    required_config = ['url']
    optional_config = {
        'method': 'POST',          # HTTP 方法
        'headers': {},             # 自訂 Headers
        'timeout': 30,             # 超時時間（秒）
        'max_retry': 3,            # 最大重試次數
        'retry_delay': 1,          # 重試延遲（秒）
        'batch_size': 1,           # 批次大小（0 表示一次全部發送）
    }

    def write(self, table: pw.Table) -> None:
        """將資料 POST 到 API。

        Args:
            table: 要寫入的 Pathway Table

        Raises:
            requests.RequestException: 當 API 請求失敗時
        """
        # Pathway 是流式處理，我們需要將資料輸出到暫存位置
        # 然後讀取並發送到 API

        import tempfile
        import json
        import os

        # 建立暫存檔案
        fd, temp_path = tempfile.mkstemp(suffix='.jsonl', text=True)
        os.close(fd)

        try:
            # 先寫入暫存檔案
            pw.io.jsonlines.write(table, temp_path)

            # 執行 Pathway 以確保資料寫入
            # 注意：這會在 Pipeline.run() 中執行

            # 讀取暫存檔案並發送到 API
            # 這部分在 teardown 中執行
            self._temp_path = temp_path

        except Exception as e:
            # 清理暫存檔案
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def teardown(self) -> None:
        """清理資源並發送資料到 API。"""
        import json
        import os

        if not hasattr(self, '_temp_path'):
            return

        temp_path = self._temp_path

        try:
            # 檢查暫存檔案是否存在
            if not os.path.exists(temp_path):
                return

            # 讀取資料
            data = []
            with open(temp_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))

            # 發送到 API
            if data:
                self._send_to_api(data)

        finally:
            # 清理暫存檔案
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _send_to_api(self, data: List[Dict[str, Any]]) -> None:
        """發送資料到 API。

        Args:
            data: 要發送的資料列表

        Raises:
            requests.RequestException: 當請求失敗且重試次數用盡時
        """
        url = self.config['url']
        method = self.config['method'].upper()
        headers = self.config['headers']
        timeout = self.config['timeout']
        max_retry = self.config['max_retry']
        retry_delay = self.config['retry_delay']
        batch_size = self.config['batch_size']

        # 確保 Content-Type 是 JSON
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'

        # 分批發送
        if batch_size > 0:
            batches = [
                data[i:i + batch_size]
                for i in range(0, len(data), batch_size)
            ]
        else:
            batches = [data]  # 一次全部發送

        # 發送每個批次
        for i, batch in enumerate(batches):
            self._send_batch(
                batch, url, method, headers, timeout, max_retry, retry_delay
            )

    def _send_batch(
        self,
        batch: List[Dict[str, Any]],
        url: str,
        method: str,
        headers: Dict[str, str],
        timeout: int,
        max_retry: int,
        retry_delay: int,
    ) -> None:
        """發送單一批次到 API。

        Args:
            batch: 要發送的資料批次
            url: API URL
            method: HTTP 方法
            headers: HTTP Headers
            timeout: 超時時間
            max_retry: 最大重試次數
            retry_delay: 重試延遲

        Raises:
            requests.RequestException: 當重試次數用盡後仍然失敗時
        """
        last_error = None

        for attempt in range(max_retry + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    json=batch,
                    headers=headers,
                    timeout=timeout,
                )
                response.raise_for_status()
                return  # 成功

            except requests.RequestException as e:
                last_error = e

                # 如果還有重試機會，等待後重試
                if attempt < max_retry:
                    time.sleep(retry_delay)
                    continue
                else:
                    # 重試次數用盡
                    raise RuntimeError(
                        f"API 請求失敗（已重試 {max_retry} 次）: {e}"
                    ) from e
