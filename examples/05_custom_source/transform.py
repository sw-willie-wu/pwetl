"""Transform for custom source example."""

from pwetl.transforms import BaseTransform
import pathway as pw


class FilterTransform(BaseTransform):
    """Split data into high and low value categories."""

    def transform(self, tables):
        """Split data based on value threshold.

        Args:
            tables: Dict with 'random_data' table

        Returns:
            Dict with 'high_value' and 'low_value' tables
        """
        data = tables["random_data"]

        # Split by value threshold (100)
        high_value = data.filter(pw.this.value >= 100)
        low_value = data.filter(pw.this.value < 100)

        return {
            "high_value": high_value,
            "low_value": low_value,
        }
