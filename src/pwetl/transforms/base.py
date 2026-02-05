"""Base class for all transforms."""
from abc import ABC, abstractmethod
from typing import Dict
import pathway as pw


class BaseTransform(ABC):
    """Abstract base class for all Transforms.

    All custom Transforms must inherit this class and implement the transform() method.
    """

    @abstractmethod
    def transform(self, tables: Dict[str, pw.Table]) -> Dict[str, pw.Table]:
        """Transform data.

        Args:
            tables: Input tables in format Dict[source_name, pw.Table]

        Returns:
            Dict[sink_name, pw.Table]: Output tables

        Raises:
            Exception: When transformation fails
        """

    def setup(self) -> None:
        """Initialize resources (optional).

        Called before transform(), used to load models, establish connections, etc.
        Subclasses can override this method.
        """

    def teardown(self) -> None:
        """Clean up resources (optional).

        Called after transform(), used to release resources, close connections, etc.
        Subclasses can override this method.
        """
