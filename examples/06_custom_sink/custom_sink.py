"""Custom Sink Example - Markdown Report Generator.

This example demonstrates how to create a custom sink that generates
a formatted Markdown report from the data.
"""

import pathway as pw
from pwetl.sinks import BaseSink


class MarkdownReportSink(BaseSink):
    """Generate a Markdown-formatted report from table data.

    This sink creates a nicely formatted Markdown file with:
    - Title and summary statistics
    - Data table
    - Optional grouping and aggregation
    """

    required_config = ["path"]
    optional_config = {
        "title": "Data Report",
        "include_summary": True,
        "group_by": None,
    }

    def write(self, table: pw.Table) -> None:
        """Write data as Markdown report.

        Args:
            table: Pathway table to write
        """
        import os

        output_path = self.config["path"]
        title = self.config.get("title", "Data Report")
        include_summary = self.config.get("include_summary", True)

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # Write as CSV first to get the data
        temp_csv = output_path + ".tmp.csv"
        pw.io.csv.write(table, temp_csv)

        # Use Pathway's commit and wait
        pw.run(monitoring_level=pw.MonitoringLevel.NONE)

        # Read CSV and generate Markdown
        self._generate_markdown(temp_csv, output_path, title, include_summary)

        # Clean up temp file
        if os.path.exists(temp_csv):
            os.remove(temp_csv)

    def _generate_markdown(
        self, csv_path: str, output_path: str, title: str, include_summary: bool
    ) -> None:
        """Generate Markdown from CSV data."""
        import csv

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\nNo data available.\n")
            return

        # Generate Markdown content
        lines = []
        lines.append(f"# {title}\n")
        lines.append(f"Generated on: {pw.this.now()}\n")

        if include_summary:
            lines.append("## Summary\n")
            lines.append(f"- Total records: {len(rows)}\n")

            # Try to calculate numeric summaries
            numeric_cols = []
            for col in rows[0].keys():
                try:
                    float(rows[0][col])
                    numeric_cols.append(col)
                except (ValueError, TypeError):
                    pass

            if numeric_cols:
                for col in numeric_cols:
                    values = [float(row[col]) for row in rows if row[col]]
                    if values:
                        lines.append(
                            f"- {col}: min={min(values):.2f}, max={max(values):.2f}, avg={sum(values)/len(values):.2f}\n"
                        )
            lines.append("\n")

        # Generate table
        lines.append("## Data\n")

        # Header
        headers = list(rows[0].keys())
        lines.append("| " + " | ".join(headers) + " |\n")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |\n")

        # Rows
        for row in rows[:100]:  # Limit to first 100 rows
            lines.append("| " + " | ".join(str(row[h]) for h in headers) + " |\n")

        if len(rows) > 100:
            lines.append(f"\n*Showing first 100 of {len(rows)} records*\n")

        # Write Markdown
        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(lines)


class JSONLSink(BaseSink):
    """Write data in JSON Lines format with custom formatting.

    This is a simplified custom sink that demonstrates basic file writing.
    """

    required_config = ["path"]
    optional_config = {
        "indent": False,
    }

    def write(self, table: pw.Table) -> None:
        """Write table as JSONL.

        Args:
            table: Pathway table to write
        """
        output_path = self.config["path"]

        # Use Pathway's built-in JSONL writer
        pw.io.jsonlines.write(table, output_path)
