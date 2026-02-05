"""Custom exceptions for pwetl framework."""


class PWETLError(Exception):
    """Base exception for all pwetl errors."""


class ConfigurationError(PWETLError):
    """Raised when configuration is invalid or missing required fields."""


class ValidationError(PWETLError):
    """Raised when data validation fails."""


class SchemaError(PWETLError):
    """Raised when schema parsing or type conversion fails."""


class SourceError(PWETLError):
    """Raised when source creation or reading fails."""


class SinkError(PWETLError):
    """Raised when sink creation or writing fails."""


class TransformError(PWETLError):
    """Raised when transform loading or execution fails."""


class RegistryError(PWETLError):
    """Raised when registry operations fail (unknown type, missing module, etc.)."""


class LoaderError(PWETLError):
    """Raised when dynamic loading of modules or classes fails."""
