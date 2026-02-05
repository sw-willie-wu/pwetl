"""Test schema parser utilities."""

import pytest
import pathway as pw
from pwetl.utils.schema import SchemaParser
from pwetl.core.exceptions import SchemaError


class TestSchemaParser:
    """Test SchemaParser class."""

    def test_parse_basic_types(self):
        """Test parsing basic types."""
        schema_config = {
            'id': 'int',
            'name': 'str',
            'price': 'float',
            'active': 'bool'
        }

        schema = SchemaParser.parse(schema_config)

        # Check that schema is a subclass of pw.Schema
        assert issubclass(schema, pw.Schema)

        # Check annotations
        assert schema.__annotations__['id'] == int
        assert schema.__annotations__['name'] == str
        assert schema.__annotations__['price'] == float
        assert schema.__annotations__['active'] == bool

    def test_parse_pathway_types(self):
        """Test parsing types that convert to Pathway types."""
        schema_config = {
            'created_at': 'datetime',  # Pydantic datetime -> Pathway DateTimeNaive
            'data': 'dict',            # Pydantic dict -> Pathway Json
            'tags': 'list'             # Pydantic list -> Pathway Json
        }

        schema = SchemaParser.parse(schema_config)

        assert schema.__annotations__['created_at'] == pw.DateTimeNaive
        assert schema.__annotations__['data'] == pw.Json
        assert schema.__annotations__['tags'] == pw.Json

    def test_parse_invalid_type(self):
        """Test that invalid type raises error."""
        schema_config = {
            'field': 'invalid_type'
        }

        with pytest.raises(SchemaError):
            SchemaParser.parse(schema_config)

    def test_parse_empty_schema(self):
        """Test parsing empty schema."""
        schema_config = {}
        schema = SchemaParser.parse(schema_config)

        assert issubclass(schema, pw.Schema)
        assert not hasattr(schema, '__annotations__') or len(schema.__annotations__) == 0

    def test_add_custom_type(self):
        """Test adding custom type to Pydantic type map."""
        # 在新設計中，我們擴展 PYDANTIC_TYPE_MAP
        SchemaParser.PYDANTIC_TYPE_MAP['custom_str'] = str
        SchemaParser.PYDANTIC_TO_PATHWAY[str] = str  # str -> str

        # Parse schema with custom type
        schema_config = {
            'field': 'custom_str'
        }
        schema = SchemaParser.parse(schema_config)

        assert schema.__annotations__['field'] == str

        # Clean up: remove the custom type to avoid affecting other tests
        if 'custom_str' in SchemaParser.PYDANTIC_TYPE_MAP:
            del SchemaParser.PYDANTIC_TYPE_MAP['custom_str']

    def test_type_map_contains_expected_types(self):
        """Test that PYDANTIC_TYPE_MAP contains all expected types."""
        expected_types = ['str', 'int', 'float', 'bool', 'bytes', 'datetime', 'dict', 'list']

        for type_name in expected_types:
            assert type_name in SchemaParser.PYDANTIC_TYPE_MAP
