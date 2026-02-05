"""Custom Source Example - Random Data Generator.

This example demonstrates how to create a custom data source that generates
random data using Python's random module.
"""

import random
import pathway as pw
from pwetl.sources import BaseSource


class RandomDataSource(BaseSource):
    """Generate random data for testing purposes.

    This source generates a specified number of random records with
    id, name, and value fields.
    """

    required_config = ["count"]
    optional_config = {
        "seed": None,
        "min_value": 0,
        "max_value": 100,
    }

    def setup(self) -> None:
        """Setup random seed if provided."""
        if self.config.get("seed"):
            random.seed(self.config["seed"])

    def read(self) -> pw.Table:
        """Generate random data and return as Pathway table.

        Returns:
            pw.Table: Table with random data
        """
        count = self.config["count"]
        min_value = self.config.get("min_value", 0)
        max_value = self.config.get("max_value", 100)

        # Generate random data as tuples (required by table_from_rows)
        data = []
        for i in range(count):
            row = (
                i + 1,  # id
                f"Item_{i + 1:03d}",  # name
                random.randint(min_value, max_value),  # value
                random.choice(["A", "B", "C"]),  # category
            )
            data.append(row)

        # Get schema and create Pathway table from list
        schema = self._get_schema()
        if schema is None:
            raise ValueError(
                f"Source '{self.name}' requires a schema configuration. "
                "Please specify 'schema' in your config.yaml"
            )

        table = pw.debug.table_from_rows(schema=schema, rows=data)

        return table

    def _get_schema(self):
        """Get Pathway schema from config.

        Returns:
            Pathway Schema class, or None if not specified
        """
        from pwetl.utils.schema import SchemaParser

        schema_config = self.config.get("schema")
        if schema_config:
            return SchemaParser.parse(schema_config)
        return None
