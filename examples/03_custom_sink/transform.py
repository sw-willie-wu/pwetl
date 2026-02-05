"""Transform for custom sink example."""

from pwetl.transforms import BaseTransform
import pathway as pw


class SummaryTransform(BaseTransform):
    """Add summary fields to the data."""

    def transform(self, tables):
        """Calculate summary statistics.

        Args:
            tables: Dict with 'products' table

        Returns:
            Dict with transformed tables for each sink
        """
        products = tables["products"]

        # Add a value_category field
        result = products.select(
            product_id=pw.this.product_id,
            name=pw.this.name,
            value=pw.this.value,
            category=pw.this.category,
            value_category=pw.apply(
                lambda v: "High" if v >= 100 else "Low", pw.this.value
            ),
        )

        return {
            "markdown_report": result,
            "jsonl_output": result,
        }
