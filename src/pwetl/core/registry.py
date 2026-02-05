"""Registry and factory for sources and sinks."""

from typing import Dict, Type, Any
from pwetl.sources.base import BaseSource
from pwetl.sinks.base import BaseSink
from pwetl.utils.loader import DynamicLoader
from pwetl.core.exceptions import RegistryError


# Global Registry: Stores built-in and user-registered Source/Sink classes
SOURCE_REGISTRY: Dict[str, Type[BaseSource]] = {}
SINK_REGISTRY: Dict[str, Type[BaseSink]] = {}


class SourceFactory:
    """Source factory class.

    Responsible for creating Source instances based on configuration.
    """

    @staticmethod
    def create(name: str, config: Dict[str, Any]) -> BaseSource:
        """Create Source instance.

        Args:
            name: Source name
            config: Source configuration, must contain 'type' field

        Returns:
            BaseSource instance

        Raises:
            RegistryError: When configuration is missing 'type' field or type does not exist
            TypeError: When custom class is not a subclass of BaseSource
        """
        if "type" not in config:
            raise RegistryError(
                f"Source '{name}' configuration is missing 'type' field"
            )

        source_type = config["type"]

        # Handle custom Source (dynamic loading)
        if source_type == "custom":
            return SourceFactory._create_custom(name, config)

        # Handle built-in Source (load from Registry)
        if source_type not in SOURCE_REGISTRY:
            raise RegistryError(
                f"Unknown Source type: '{source_type}'\n"
                f"Available types: {', '.join(SOURCE_REGISTRY.keys())}\n"
                f"Or use 'custom' type and specify 'module' and 'class'"
            )

        source_class = SOURCE_REGISTRY[source_type]
        return source_class(name=name, config=config)

    @staticmethod
    def _create_custom(name: str, config: Dict[str, Any]) -> BaseSource:
        """Create custom Source.

        Args:
            name: Source name
            config: Must contain 'module' field in format 'module_path.ClassName'

        Returns:
            BaseSource instance

        Raises:
            RegistryError: When configuration is missing required fields or format is invalid
            TypeError: When class is not a subclass of BaseSource
        """
        if "module" not in config:
            raise RegistryError(
                f"Custom Source '{name}' configuration is missing 'module' field"
            )

        module_spec = config["module"]

        # Parse module.ClassName format
        if "." not in module_spec:
            raise RegistryError(
                f"Custom Source '{name}' 'module' must be in 'module_path.ClassName' format"
            )

        parts = module_spec.rsplit(".", 1)
        module_path = parts[0]
        class_name = parts[1]

        # Dynamically load class
        source_class = DynamicLoader.load_class(module_path, class_name)

        # Validate that it's a subclass of BaseSource
        if not issubclass(source_class, BaseSource):
            raise TypeError(f"Class '{class_name}' must inherit from BaseSource")

        return source_class(name=name, config=config)


class SinkFactory:
    """Sink factory class.

    Responsible for creating Sink instances based on configuration.
    """

    @staticmethod
    def create(name: str, config: Dict[str, Any]) -> BaseSink:
        """Create Sink instance.

        Args:
            name: Sink name
            config: Sink configuration, must contain 'type' field

        Returns:
            BaseSink instance

        Raises:
            RegistryError: When configuration is missing 'type' field or type does not exist
            TypeError: When custom class is not a subclass of BaseSink
        """
        if "type" not in config:
            raise RegistryError(f"Sink '{name}' configuration is missing 'type' field")

        sink_type = config["type"]

        # Handle custom Sink (dynamic loading)
        if sink_type == "custom":
            return SinkFactory._create_custom(name, config)

        # Handle built-in Sink (load from Registry)
        if sink_type not in SINK_REGISTRY:
            raise RegistryError(
                f"Unknown Sink type: '{sink_type}'\n"
                f"Available types: {', '.join(SINK_REGISTRY.keys())}\n"
                f"Or use 'custom' type and specify 'module' and 'class'"
            )

        sink_class = SINK_REGISTRY[sink_type]
        return sink_class(name=name, config=config)

    @staticmethod
    def _create_custom(name: str, config: Dict[str, Any]) -> BaseSink:
        """Create custom Sink.

        Args:
            name: Sink name
            config: Must contain 'module' field in format 'module_path.ClassName'

        Returns:
            BaseSink instance

        Raises:
            RegistryError: When configuration is missing required fields or format is invalid
            TypeError: When class is not a subclass of BaseSink
        """
        if "module" not in config:
            raise RegistryError(
                f"Custom Sink '{name}' configuration is missing 'module' field"
            )

        module_spec = config["module"]

        # Parse module.ClassName format
        if "." not in module_spec:
            raise RegistryError(
                f"Custom Sink '{name}' 'module' must be in 'module_path.ClassName' format"
            )

        parts = module_spec.rsplit(".", 1)
        module_path = parts[0]
        class_name = parts[1]

        # Dynamically load class
        sink_class = DynamicLoader.load_class(module_path, class_name)

        # Validate that it's a subclass of BaseSink
        if not issubclass(sink_class, BaseSink):
            raise TypeError(f"Class '{class_name}' must inherit from BaseSink")

        return sink_class(name=name, config=config)
