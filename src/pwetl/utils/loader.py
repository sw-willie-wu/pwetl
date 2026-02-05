"""Dynamic loading utilities."""
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Type
from pwetl.core.exceptions import LoaderError


class DynamicLoader:
    """Utility for dynamically loading classes.

    Supports loading classes from file paths or package paths.
    """

    @staticmethod
    def load_class(module_path: str, class_name: str) -> Type:
        """Load class from module.

        Args:
            module_path: Module path, can be:
                - File path: 'my_sources.py' or 'path/to/my_sources.py'
                - Package path: 'my_package.sources'
            class_name: Class name

        Returns:
            The loaded class

        Raises:
            LoaderError: When module or class does not exist or path format is invalid
        """
        if module_path.endswith('.py'):
            return DynamicLoader._load_from_file(module_path, class_name)
        return DynamicLoader._load_from_package(module_path, class_name)

    @staticmethod
    def _load_from_file(file_path: str, class_name: str) -> Type:
        """Load class from file.

        Args:
            file_path: Python file path
            class_name: Class name

        Returns:
            The loaded class

        Raises:
            LoaderError: When file or class does not exist
        """
        path = Path(file_path)

        if not path.exists():
            raise LoaderError(f"File does not exist: {file_path}")

        # Create module name (remove .py suffix)
        module_name = path.stem

        # Load module
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise LoaderError(f"Cannot load module: {file_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Get class
        if not hasattr(module, class_name):
            raise LoaderError(
                f"Class '{class_name}' not found in module '{module_name}'"
            )

        return getattr(module, class_name)

    @staticmethod
    def _load_from_package(module_path: str, class_name: str) -> Type:
        """Load class from package.

        Args:
            module_path: Package path, e.g., 'my_package.sources'
            class_name: Class name

        Returns:
            The loaded class

        Raises:
            LoaderError: When module or class does not exist
        """
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError as exc:
            raise LoaderError(f"Module not found: {module_path}") from exc

        if not hasattr(module, class_name):
            raise LoaderError(
                f"Class '{class_name}' not found in module '{module_path}'"
            )

        return getattr(module, class_name)


class TransformLoader:
    """Transform loading utility."""

    @staticmethod
    def load(transform_config: str):
        """Load Transform from configuration.

        Args:
            transform_config: Transform configuration in format 'module.ClassName'
                e.g., 'transforms.MyTransform' or 'my_transforms.py.MyTransform'

        Returns:
            BaseTransform instance

        Raises:
            LoaderError: When configuration format is invalid, module or class does not exist
            TypeError: When class is not a subclass of BaseTransform
        """
        from pwetl.transforms import BaseTransform

        if '.' not in transform_config:
            raise LoaderError(
                f"Invalid Transform configuration format: '{transform_config}'\n"
                f"Correct format: 'module.ClassName' or 'module.py.ClassName'"
            )

        # Split module path and class name
        parts = transform_config.rsplit('.', 1)
        if len(parts) != 2:
            raise LoaderError(
                f"Invalid Transform configuration format: '{transform_config}'\n"
                f"Correct format: 'module.ClassName' or 'module.py.ClassName'"
            )

        module_path, class_name = parts

        # Load class
        transform_class = DynamicLoader.load_class(module_path, class_name)

        # Validate that it's a subclass of BaseTransform
        if not issubclass(transform_class, BaseTransform):
            raise TypeError(
                f"Class '{class_name}' must inherit from BaseTransform"
            )

        # Create instance
        return transform_class()
