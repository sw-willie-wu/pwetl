"""Transform for database sink example."""

import uuid

from pwetl.transforms import BaseTransform
import pathway as pw

# Namespace for deterministic UUID5 generation
_UUID_NS = uuid.UUID('a1b2c3d4-e5f6-7890-abcd-ef1234567890')


class SalesTransform(BaseTransform):
    """Aggregate sales data by product."""

    def transform(self, tables):
        """Calculate sales summary per product.

        Demonstrates:
        - pw.apply() for UUID5 generation (Pathway reserves 'id')
        - dt.strptime() for string -> DateTimeNaive conversion
        - 'time' column collision with Pathway metadata

        Args:
            tables: Dict with 'sales' table

        Returns:
            Dict with 'db_output' table containing aggregated sales
        """
        sales = tables["sales"]

        # Calculate revenue per row; parse order_date to DateTimeNaive
        with_revenue = sales.select(
            product_id=pw.this.product_id,
            product_name=pw.this.product_name,
            category=pw.this.category,
            quantity=pw.this.quantity,
            revenue=pw.cast(float, pw.this.quantity) * pw.this.unit_price,
            unit_price=pw.this.unit_price,
            order_date=pw.this.order_date.dt.strptime("%Y-%m-%d"),
        )

        # Aggregate by product
        summary = with_revenue.groupby(pw.this.product_id).reduce(
            product_id=pw.this.product_id,
            product_name=pw.reducers.any(pw.this.product_name),
            category=pw.reducers.any(pw.this.category),
            total_sold=pw.reducers.sum(pw.this.quantity),
            revenue=pw.reducers.sum(pw.this.revenue),
            avg_price=pw.reducers.avg(pw.this.unit_price),
            # 'time' collides with Pathway metadata -- DatabaseSink handles it
            time=pw.reducers.max(pw.this.order_date),
        )

        # Add deterministic UUID5 PK from product_id
        # Pathway reserves 'id', so use '_pw_id' prefix —
        # DatabaseSink restores it to 'id' in DB output
        result = summary.select(
            _pw_id=pw.apply(
                lambda pid: str(uuid.uuid5(_UUID_NS, pid)),
                pw.this.product_id,
            ),
            product_id=pw.this.product_id,
            product_name=pw.this.product_name,
            category=pw.this.category,
            total_sold=pw.this.total_sold,
            revenue=pw.this.revenue,
            avg_price=pw.this.avg_price,
            time=pw.this.time,
        )

        return {
            "db_output": result,
            "output_csv": result,
        }
