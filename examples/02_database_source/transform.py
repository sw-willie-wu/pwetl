"""Transform for database source example."""

from pwetl.transforms import BaseTransform
import pathway as pw


class DepartmentSummaryTransform(BaseTransform):
    """Aggregate employee data by department."""

    def transform(self, tables):
        """Calculate department-level statistics.

        Args:
            tables: Dict with 'employees' table

        Returns:
            Dict with summary and detail outputs
        """
        employees = tables["employees"]

        # Department summary: headcount, avg/max salary
        summary = employees.groupby(pw.this.department).reduce(
            department=pw.this.department,
            headcount=pw.reducers.count(),
            avg_salary=pw.reducers.avg(pw.cast(float, pw.this.salary)),
            max_salary=pw.reducers.max(pw.this.salary),
        )

        return {
            "summary_csv": summary,
            "detail_jsonl": employees,
        }
