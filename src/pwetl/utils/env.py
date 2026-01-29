"""環境變數替換工具。"""
import os
import re
from pathlib import Path
from typing import Any, Union


class EnvVarSubstitution:
    """環境變數替換工具。

    支援兩種語法：
    - ${VAR_NAME}: 必須存在的環境變數
    - ${VAR_NAME:default}: 有預設值的環境變數
    """

    ENV_VAR_PATTERN = re.compile(r'\$\{([^}:]+)(?::([^}]*))?\}')

    @classmethod
    def substitute(cls, value: Any) -> Any:
        """遞迴替換環境變數。

        Args:
            value: 要處理的值，可以是 str, dict, list 或其他類型

        Returns:
            替換後的值

        Raises:
            ValueError: 當必要的環境變數不存在時
        """
        if isinstance(value, str):
            return cls._substitute_string(value)
        if isinstance(value, dict):
            return {k: cls.substitute(v) for k, v in value.items()}
        if isinstance(value, list):
            return [cls.substitute(item) for item in value]
        return value

    @classmethod
    def _substitute_string(cls, value: str) -> str:
        """替換字串中的環境變數。

        Args:
            value: 要處理的字串

        Returns:
            替換後的字串

        Raises:
            ValueError: 當必要的環境變數不存在時
        """
        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(2)

            env_value = os.getenv(var_name)

            if env_value is None:
                if default_value is not None:
                    return default_value
                raise ValueError(
                    f"環境變數 '{var_name}' 不存在且沒有預設值"
                )

            return env_value

        return cls.ENV_VAR_PATTERN.sub(replace_var, value)


def load_env_file(env_file: Union[str, Path] = '.env') -> None:
    """載入 .env 檔案。

    Args:
        env_file: .env 檔案的路徑，預設為當前目錄下的 .env
    """
    env_path = Path(env_file)

    if not env_path.exists():
        return

    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # 跳過空行和註解
            if not line or line.startswith('#'):
                continue

            # 解析 KEY=VALUE 格式
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # 移除引號
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                # 只有在環境變數不存在時才設定
                if key not in os.environ:
                    os.environ[key] = value
