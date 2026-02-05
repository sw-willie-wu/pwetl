"""Logging configuration module."""

import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Colored log formatter."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record."""
        # Get color for level only
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        # Format time
        asctime = self.formatTime(record, self.datefmt)

        # Format message with color only on level
        log_fmt = (
            f"{asctime} - {color}{record.levelname}{reset} - "
            f"{record.name} - {record.getMessage()}"
        )

        # If there's exception info, add it after the message
        if record.exc_info:
            log_fmt += "\n" + self.formatException(record.exc_info)

        return log_fmt


def setup_logger(
    name: str = "pwetl",
    level: int = logging.INFO,
    verbose: bool = False,
    log_config: Optional[str] = None,
) -> logging.Logger:
    """Set up logger.

    Args:
        name: Logger name
        level: Log level
        verbose: Whether to show detailed messages (will lower to DEBUG level)
        log_config: Path to logging configuration file (YAML or JSON format)

    Returns:
        Configured Logger instance
    """
    # If external log config is provided, load it
    if log_config:
        try:
            from pathlib import Path
            import logging.config as log_config_module
            
            config_path = Path(log_config)
            
            if not config_path.exists():
                raise FileNotFoundError(f"Log config file not found: {log_config}")
            
            if config_path.suffix in ('.yaml', '.yml'):
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    log_config_module.dictConfig(config)
            elif config_path.suffix == '.json':
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    log_config_module.dictConfig(config)
            else:
                raise ValueError(
                    f"Unsupported log config format: {config_path.suffix}. "
                    "Supported formats: .yaml, .yml, .json"
                )
            
            return logging.getLogger(name)
        except Exception as e:
            # If loading external config fails, fall back to default
            print(f"Warning: Failed to load log config from {log_config}: {e}", file=sys.stderr)
            print("Falling back to default logging configuration", file=sys.stderr)
    
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    # Set log level
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Set formatter
    formatter = ColoredFormatter()
    console_handler.setFormatter(formatter)

    # Add handler to pwetl logger
    logger.addHandler(console_handler)
    logger.propagate = False

    # Also configure Pathway logger with same format
    pathway_logger = logging.getLogger("pathway")
    if not pathway_logger.handlers:
        pathway_handler = logging.StreamHandler(sys.stdout)
        pathway_handler.setLevel(logging.DEBUG)
        pathway_handler.setFormatter(formatter)
        pathway_logger.addHandler(pathway_handler)
        pathway_logger.setLevel(logging.INFO)
        pathway_logger.propagate = False

    # Configure root logger to catch all other loggers (including Pathway internals)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # Remove any existing handlers
    root_logger.handlers = []
    # Add our formatter
    root_handler = logging.StreamHandler(sys.stdout)
    root_handler.setFormatter(formatter)
    root_logger.addHandler(root_handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get logger.

    Args:
        name: Logger name, default is 'pwetl'

    Returns:
        Logger instance
    """
    if name is None:
        name = "pwetl"
    return logging.getLogger(name)
