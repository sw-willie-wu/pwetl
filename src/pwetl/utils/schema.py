"""Schema parsing utilities.

Design Philosophy:
1. Users can only write Pydantic-compatible types in YAML
2. SchemaParser first creates a Pydantic Model for data validation
3. Then converts Pydantic types to Pathway Schema types
"""

import datetime
from types import UnionType
from typing import Dict, Type, Optional, Union, get_origin, get_args

import pathway as pw
import pydantic
from pydantic import BaseModel, create_model
from pwetl.core.exceptions import SchemaError


class SchemaParser:
    """Schema parser based on Pydantic types."""

    # Pydantic type mapping: YAML string -> Pydantic type (common abbreviations)
    PYDANTIC_TYPE_MAP: Dict[str, Type] = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "bytes": bytes,
        "datetime": datetime.datetime,
        "dict": dict,
        "list": list,
    }

    # Pydantic modules for dynamic type lookup (try in order)
    PYDANTIC_MODULES = [pydantic]  # EmailStr, HttpUrl, UUID4, etc.

    # Pydantic special type mappings
    PYDANTIC_STR_TYPES = (
        "EmailStr",
        "HttpUrl",
        "AnyUrl",
        "UUID4",
        "UUID1",
        "IPvAnyAddress",
        "NameEmail",
    )
    PYDANTIC_FLOAT_TYPES = ("Decimal", "condecimal")

    # Pydantic type → Pathway type mapping
    PYDANTIC_TO_PATHWAY: Dict[Type, Type] = {
        str: str,
        int: int,
        float: float,
        bool: bool,
        bytes: bytes,
        datetime.datetime: pw.DateTimeNaive,
        dict: pw.Json,
        list: pw.Json,
        # Pydantic special types (essentially string validation)
        type(None): type(None),  # for Optional
    }

    # Common type modules
    @classmethod
    def _get_common_type_modules(cls):
        """Get list of common type modules."""
        return [
            __builtins__ if isinstance(__builtins__, dict) else vars(__builtins__),
            datetime,
        ]

    @classmethod
    def parse(cls, schema_config: Dict[str, Union[str, Dict]]) -> Type[pw.Schema]:
        """Create Pathway Schema from configuration.

        Process:
        1. First parse into Pydantic types
        2. Then convert to Pathway Schema types

        Args:
            schema_config: Schema configuration in format {field_name: type_string or nested_dict}
                Examples:
                - Simple types: {'id': 'int', 'name': 'str'}
                - Optional: {'address': 'str?', 'age': 'int?'}
                - Nested objects: {'Point': {'Latitude': 'float', 'Longitude': 'float'}}

        Returns:
            Pathway Schema class

        Raises:
            ValueError: When type is not supported

        Example:
            >>> schema_config = {
            ...     'id': 'int',
            ...     'name': 'str',
            ...     'address': 'str?',  # Optional[str]
            ...     'Point': {'Latitude': 'float', 'Longitude': 'float'}
            ... }
            >>> schema = SchemaParser.parse(schema_config)
        """
        # 1. First parse into Pydantic types
        pydantic_annotations = {}
        for field_name, type_def in schema_config.items():
            pydantic_annotations[field_name] = cls._parse_pydantic_type(
                type_def, field_name
            )

        # 2. Convert to Pathway types
        pathway_annotations = {}
        for field_name, pydantic_type in pydantic_annotations.items():
            pathway_annotations[field_name] = cls._convert_pydantic_to_pathway(
                pydantic_type
            )

        # 3. Create Pathway Schema
        schema_dict = {"__annotations__": pathway_annotations}
        return type("DynamicSchema", (pw.Schema,), schema_dict)

    @classmethod
    def _convert_pydantic_to_pathway(
        cls, pydantic_type: Type | UnionType
    ) -> Type | UnionType:
        """Convert Pydantic type to Pathway type.

        Args:
            pydantic_type: Pydantic type

        Returns:
            Pathway type
        """
        # Handle Optional[T] (Union[T, None])
        origin = get_origin(pydantic_type)
        if origin is Union:
            args = get_args(pydantic_type)
            # Optional[T] case
            if len(args) == 2 and type(None) in args:
                non_none_type = args[0] if args[1] is type(None) else args[1]
                converted = cls._convert_pydantic_to_pathway(non_none_type)
                return Optional[converted]

        # Handle BaseModel (nested models)
        if isinstance(pydantic_type, type) and issubclass(pydantic_type, BaseModel):
            return pw.Json

        # Look up in mapping table
        if pydantic_type in cls.PYDANTIC_TO_PATHWAY:
            return cls.PYDANTIC_TO_PATHWAY[pydantic_type]

        # Pydantic special types (EmailStr, HttpUrl, etc.) -> str
        if isinstance(pydantic_type, type):
            for base in pydantic_type.mro():
                if base.__name__ in cls.PYDANTIC_STR_TYPES:
                    return str
                if base.__name__ in cls.PYDANTIC_FLOAT_TYPES:
                    return float

        # Default: keep as-is (might be a basic type)
        return pydantic_type

    @classmethod
    def create_pydantic_model(
        cls, schema_config: Dict[str, Union[str, Dict]], model_name: str = "DataModel"
    ) -> Type[BaseModel]:
        """Create Pydantic model from configuration for validation.

        Args:
            schema_config: Schema configuration
            model_name: Model name

        Returns:
            Pydantic BaseModel class
        """
        fields = {}

        for field_name, type_def in schema_config.items():
            field_type = cls._parse_pydantic_type(type_def, field_name)

            # If Optional type, allow None
            if get_origin(field_type) is Union:
                fields[field_name] = (field_type, None)
            else:
                fields[field_name] = (field_type, ...)

        return create_model(model_name, **fields)

    @classmethod
    def _dynamic_type_lookup(cls, type_name: str, search_modules: list) -> Type | None:
        """Dynamically look up type from specified modules.

        Args:
            type_name: Type name (e.g., 'EmailStr', 'HttpUrl', 'UUID')
            search_modules: List of modules to search

        Returns:
            Found type class, or None if not found
        """
        for module in search_modules:
            # Handle dict-type __builtins__
            if isinstance(module, dict):
                if type_name in module:
                    return module[type_name]
            else:
                # Normal module
                try:
                    type_class = getattr(module, type_name, None)
                    if type_class is not None:
                        return type_class
                except AttributeError:
                    continue
        return None

    @classmethod
    def _parse_pydantic_type(
        cls, type_def: Union[str, Dict], field_name: str = "Field"
    ) -> Type | UnionType:
        """Parse Pydantic type definition (only accepts Pydantic types).

        Args:
            type_def: Type definition
            field_name: Field name (for nested model naming)

        Returns:
            Pydantic-compatible type (can be Type or UnionType)

        Raises:
            ValueError: When type is not a Pydantic-supported type
        """
        # Handle nested schema (dict) - recursively create Pydantic model
        if isinstance(type_def, dict):
            nested_model_name = f"{field_name}Model"
            return cls.create_pydantic_model(type_def, nested_model_name)

        type_str = type_def

        # Handle ? syntax (e.g., str?, int?) -> Optional
        if type_str.endswith("?"):
            base_type_str = type_str[:-1]
            base_type = cls._resolve_pydantic_type(base_type_str)
            return Optional[base_type]

        # Handle general types
        return cls._resolve_pydantic_type(type_str)

    @classmethod
    def _resolve_pydantic_type(cls, type_str: str) -> Type:
        """Resolve type string to Pydantic type.

        Args:
            type_str: Type string

        Returns:
            Pydantic type

        Raises:
            ValueError: When type is not supported
        """
        # 1. First check common abbreviations
        if type_str in cls.PYDANTIC_TYPE_MAP:
            return cls.PYDANTIC_TYPE_MAP[type_str]

        # 2. Dynamically look up type in Pydantic modules
        found_type = cls._dynamic_type_lookup(
            type_str, cls.PYDANTIC_MODULES + cls._get_common_type_modules()
        )
        if found_type:
            return found_type

        # 3. Not found, raise error
        raise SchemaError(
            f"Unsupported type: '{type_str}'\n"
            f"Please use Pydantic-supported types:\n"
            f"  - Built-in abbreviations: {', '.join(cls.PYDANTIC_TYPE_MAP.keys())}\n"
            f"  - Pydantic special types: EmailStr, HttpUrl, UUID4, constr, condecimal, etc.\n"
            f"  - Or use nested dict to define complex objects"
        )
