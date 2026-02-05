"""Transform for API sink example."""

from pwetl.transforms import BaseTransform
import pathway as pw


class SensorTransform(BaseTransform):
    """Process sensor data and prepare for API submission."""

    def transform(self, tables):
        """Calculate averages by location and format for API.

        Args:
            tables: Dict with 'sensors' table

        Returns:
            Dict with processed data for API sink
        """
        sensors = tables["sensors"]

        # Calculate average temperature and humidity by location
        result = sensors.groupby(pw.this.location).reduce(
            location=pw.this.location,
            avg_temperature=pw.reducers.avg(pw.this.temperature),
            avg_humidity=pw.reducers.avg(pw.this.humidity),
            sample_count=pw.reducers.count(),
        )

        # Send same data to both JSON and form endpoints
        return {
            "api_json": result,
            "api_form": result,
        }
