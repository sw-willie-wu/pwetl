"""配置模型定義（使用 Pydantic）。"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class BaseSourceSchema(BaseModel):
    """Source 配置模型。"""

    name: str = Field(..., description="Source 的名稱")
    type: str = Field(..., description="Source 的類型")
    # 其他欄位使用動態配置
    model_config = ConfigDict(extra="allow")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """驗證 name 不為空。"""
        if not v or not v.strip():
            raise ValueError("Source name 不能為空")
        return v.strip()

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """驗證 type 不為空。"""
        if not v or not v.strip():
            raise ValueError("Source type 不能為空")
        return v.strip()


class BaseSinkSchema(BaseModel):
    """Sink 配置模型。"""

    name: str = Field(..., description="Sink 的名稱")
    type: str = Field(..., description="Sink 的類型")
    # 其他欄位使用動態配置
    model_config = ConfigDict(extra="allow")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """驗證 name 不為空。"""
        if not v or not v.strip():
            raise ValueError("Sink name 不能為空")
        return v.strip()

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """驗證 type 不為空。"""
        if not v or not v.strip():
            raise ValueError("Sink type 不能為空")
        return v.strip()


class BaseETLSchema(BaseModel):
    """ETL 配置模型。"""

    sources: List[BaseSourceSchema] = Field(..., min_length=1, description="資料源列表")
    transform: str = Field(..., description="Transform 類別")
    sinks: List[BaseSinkSchema] = Field(..., min_length=1, description="輸出列表")
    # 其他可選欄位
    model_config = ConfigDict(extra="allow")

    @field_validator("transform")
    @classmethod
    def validate_transform(cls, v: str) -> str:
        """驗證 transform 格式。"""
        if not v or not v.strip():
            raise ValueError("Transform 不能為空")

        v = v.strip()
        if "." not in v:
            raise ValueError(
                f"Transform 格式錯誤: '{v}'\n"
                f"正確格式: 'module.ClassName' 或 'module.py.ClassName'"
            )
        return v

    @model_validator(mode="after")
    def validate_unique_names(self) -> "BaseETLSchema":
        """驗證 source 和 sink 的名稱不重複。"""
        # 檢查 source names
        source_names = [s.name for s in self.sources]
        if len(source_names) != len(set(source_names)):
            duplicates = [name for name in source_names if source_names.count(name) > 1]
            raise ValueError(f"Source name 重複: {', '.join(set(duplicates))}")

        # 檢查 sink names
        sink_names = [s.name for s in self.sinks]
        if len(sink_names) != len(set(sink_names)):
            duplicates = [name for name in sink_names if sink_names.count(name) > 1]
            raise ValueError(f"Sink name 重複: {', '.join(set(duplicates))}")

        return self

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式（兼容舊版 API）。"""
        return {
            "sources": [s.model_dump() for s in self.sources],
            "transform": self.transform,
            "sinks": [s.model_dump() for s in self.sinks],
            **{
                k: v
                for k, v in self.model_dump().items()
                if k not in ["sources", "transform", "sinks"]
            },
        }
