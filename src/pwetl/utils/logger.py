"""日誌配置模組。"""
import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """彩色日誌格式化器。"""

    # ANSI 顏色代碼
    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 綠色
        "WARNING": "\033[33m",  # 黃色
        "ERROR": "\033[31m",  # 紅色
        "CRITICAL": "\033[35m",  # 紫色
        "RESET": "\033[0m",  # 重置
    }

    # Emoji 對應
    EMOJIS = {
        "DEBUG": "🔍",
        "INFO": "ℹ️ ",
        "WARNING": "⚠️ ",
        "ERROR": "❌",
        "CRITICAL": "🔥",
    }

    def format(self, record: logging.LogRecord) -> str:
        """格式化日誌記錄。"""
        # 獲取顏色和 emoji
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        emoji = self.EMOJIS.get(record.levelname, "")
        reset = self.COLORS["RESET"]

        # 格式化訊息
        log_fmt = f"{color}{emoji} {record.getMessage()}{reset}"

        # 如果有異常資訊，添加到訊息後面
        if record.exc_info:
            log_fmt += "\n" + self.formatException(record.exc_info)

        return log_fmt


def setup_logger(
    name: str = "pwetl",
    level: int = logging.INFO,
    verbose: bool = False,
) -> logging.Logger:
    """設置日誌記錄器。

    Args:
        name: Logger 名稱
        level: 日誌級別
        verbose: 是否顯示詳細訊息（會降低到 DEBUG 級別）

    Returns:
        配置好的 Logger 實例
    """
    logger = logging.getLogger(name)

    # 避免重複添加 handler
    if logger.handlers:
        return logger

    # 設置日誌級別
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(level)

    # 創建 console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # 設置格式化器
    formatter = ColoredFormatter()
    console_handler.setFormatter(formatter)

    # 添加 handler
    logger.addHandler(console_handler)

    # 防止日誌傳播到根 logger
    logger.propagate = False

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """獲取日誌記錄器。

    Args:
        name: Logger 名稱，默認為 'pwetl'

    Returns:
        Logger 實例
    """
    if name is None:
        name = "pwetl"
    return logging.getLogger(name)
