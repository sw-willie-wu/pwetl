"""Test schema parser utilities."""

import pytest
import pathway as pw
from pwetl.utils.schema import SchemaParser


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
        """Test parsing Pathway-specific types."""
        schema_config = {
            'created_at': 'datetime',
            'duration': 'duration',
            'data': 'json'
        }

        schema = SchemaParser.parse(schema_config)

        assert schema.__annotations__['created_at'] == pw.DateTimeNaive
        assert schema.__annotations__['duration'] == pw.Duration
        assert schema.__annotations__['data'] == pw.Json

    def test_parse_invalid_type(self):
        """Test that invalid type raises error."""
        schema_config = {
            'field': 'invalid_type'
        }

        with pytest.raises(ValueError, match="不支援的型態: 'invalid_type'"):
            SchemaParser.parse(schema_config)

    def test_parse_empty_schema(self):
        """Test parsing empty schema."""
        schema_config = {}
        schema = SchemaParser.parse(schema_config)

        assert issubclass(schema, pw.Schema)
        assert not hasattr(schema, '__annotations__') or len(schema.__annotations__) == 0

    def test_add_custom_type(self):
        """Test adding custom type (Pathway-supported types)."""
        # Add a Pathway-supported type with a custom name
        # Using pw.Json as an example of a valid Pathway type
        SchemaParser.add_custom_type('custom_json', pw.Json)

        # Parse schema with custom type
        schema_config = {
            'field': 'custom_json'
        }
        schema = SchemaParser.parse(schema_config)

        assert schema.__annotations__['field'] == pw.Json

        # Clean up: remove the custom type to avoid affecting other tests
        if 'custom_json' in SchemaParser.TYPE_MAP:
            del SchemaParser.TYPE_MAP['custom_json']

    def test_type_map_contains_expected_types(self):
        """Test that TYPE_MAP contains all expected types."""
        expected_types = ['str', 'int', 'float', 'bool', 'bytes', 'datetime', 'duration', 'json']

        for type_name in expected_types:
            assert type_name in SchemaParser.TYPE_MAP
