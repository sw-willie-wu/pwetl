"""Configuration model definitions (using Pydantic)."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class BaseSourceSchema(BaseModel):
    """Source configuration model."""

    name: str = Field(..., description="Source name")
    type: str = Field(..., description="Source type")
    # Other fields use dynamic configuration
    model_config = ConfigDict(extra="allow")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not empty."""
        if not v or not v.strip():
            raise ValueError("Source name cannot be empty")
        return v.strip()

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate that type is not empty."""
        if not v or not v.strip():
            raise ValueError("Source type cannot be empty")
        return v.strip()


class BaseSinkSchema(BaseModel):
    """Sink configuration model."""

    name: str = Field(..., description="Sink name")
    type: str = Field(..., description="Sink type")
    # Other fields use dynamic configuration
    model_config = ConfigDict(extra="allow")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not empty."""
        if not v or not v.strip():
            raise ValueError("Sink name cannot be empty")
        return v.strip()

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate that type is not empty."""
        if not v or not v.strip():
            raise ValueError("Sink type cannot be empty")
        return v.strip()


class BaseETLSchema(BaseModel):
    """ETL configuration model."""

    sources: List[BaseSourceSchema] = Field(
        ..., min_length=1, description="List of data sources"
    )
    transform: str = Field(..., description="Transform class")
    sinks: List[BaseSinkSchema] = Field(
        ..., min_length=1, description="List of outputs"
    )
    # Other optional fields
    model_config = ConfigDict(extra="allow")

    @field_validator("transform")
    @classmethod
    def validate_transform(cls, v: str) -> str:
        """Validate transform format."""
        if not v or not v.strip():
            raise ValueError("Transform cannot be empty")

        v = v.strip()
        if "." not in v:
            raise ValueError(
                f"Transform format error: '{v}'\n"
                f"Correct format: 'module.ClassName' or 'module.py.ClassName'"
            )
        return v

    @model_validator(mode="after")
    def validate_unique_names(self) -> "BaseETLSchema":
        """Validate that source and sink names are not duplicated."""
        # Check source names
        source_names = [s.name for s in self.sources]
        if len(source_names) != len(set(source_names)):
            duplicates = [name for name in source_names if source_names.count(name) > 1]
            raise ValueError(f"Duplicate Source names: {', '.join(set(duplicates))}")

        # Check sink names
        sink_names = [s.name for s in self.sinks]
        if len(sink_names) != len(set(sink_names)):
            duplicates = [name for name in sink_names if sink_names.count(name) > 1]
            raise ValueError(f"Duplicate Sink names: {', '.join(set(duplicates))}")

        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format (compatible with legacy API)."""
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
