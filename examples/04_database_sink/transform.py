"""Transform for database sink example."""

from pwetl.transforms import BaseTransform
import pathway as pw


class SalesTransform(BaseTransform):
    """Aggregate sales data by product."""

    def transform(self, tables):
        """Calculate sales summary per product.

        Args:
            tables: Dict with 'sales' table

        Returns:
            Dict with 'db_output' table containing aggregated sales
        """
        sales = tables["sales"]

        # Calculate revenue per row first
        with_revenue = sales.select(
            product_id=pw.this.product_id,
            product_name=pw.this.product_name,
            category=pw.this.category,
            quantity=pw.this.quantity,
            revenue=pw.cast(float, pw.this.quantity) * pw.this.unit_price,
            unit_price=pw.this.unit_price,
        )

        # Aggregate by product
        summary = with_revenue.groupby(pw.this.product_id).reduce(
            product_id=pw.this.product_id,
            product_name=pw.reducers.any(pw.this.product_name),
            category=pw.reducers.any(pw.this.category),
            total_sold=pw.reducers.sum(pw.this.quantity),
            revenue=pw.reducers.sum(pw.this.revenue),
            avg_price=pw.reducers.avg(pw.this.unit_price),
        )

        return {
            "db_output": summary,
            "output_csv": summary,
        }
