"""YouBike 2.0 即時站點資訊轉換。"""
from pwetl.transforms import BaseTransform
import pathway as pw


class YouBikeTransform(BaseTransform):
    """處理 YouBike 即時站點資訊。

    從 API 讀取 YouBike 2.0 即時站點資料，進行資料清理和格式化。
    """

    def transform(self, tables):
        """轉換 YouBike 站點資料。

        Args:
            tables: 輸入的資料表 {'youbike': pw.Table}

        Returns:
            輸出的資料表，包含三種格式的輸出
        """
        youbike = tables['youbike']

        # 選擇並重新命名欄位，使用中文更易閱讀
        result = youbike.select(
            站點代碼=pw.this.sno,
            站點名稱=pw.this.sna,
            行政區=pw.this.sarea,
            地址=pw.this.ar,
            可借車輛=pw.this.available_rent_bikes,
            可還空位=pw.this.available_return_bikes,
            緯度=pw.this.latitude,
            經度=pw.this.longitude,
            更新時間=pw.this.updateTime,
        )

        # 所有 sink 使用相同的轉換結果
        return {
            'output_csv': result,
            'output_json': result,
            'output_jsonl': result,
        }
