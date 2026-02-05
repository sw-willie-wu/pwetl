"""Command-line interface for pwetl."""
import argparse
import sys
from pathlib import Path

from pwetl.core.engine import ETLEngine
from pwetl.utils.logger import setup_logger


def cli_entry_point():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='pwetl',
        description='pwetl - A flexible ETL framework based on Pathway',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Basic execution
  pwetl --config config.yaml

  # Verbose mode
  pwetl --config config.yaml --verbose

  # Validate configuration only
  pwetl --config config.yaml --dry-run

  # Specify .env file
  pwetl --config config.yaml --env-file .env.production

For more information: https://github.com/yourusername/pwetl
        """,
    )

    # Required arguments
    parser.add_argument(
        '--config',
        required=True,
        type=str,
        help='Path to configuration file (YAML format)',
    )

    # Optional arguments
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show detailed output',
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration only, do not execute ETL',
    )

    parser.add_argument(
        '--env-file',
        type=str,
        default=None,
        help='Specify .env file path (default: .env)',
    )

    parser.add_argument(
        '--log-config',
        type=str,
        default=None,
        help='Path to logging configuration file (YAML or JSON format)',
    )

    parser.add_argument(
        '--version',
        action='version',
        version='pwetl 0.1.0',
        help='Show version information',
    )

    # Parse arguments
    args = parser.parse_args()

    # Setup logging
    logger = setup_logger(verbose=args.verbose, log_config=args.log_config)

    # Execute
    try:
        # Check if configuration file exists
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error("Configuration file not found: %s", args.config)
            sys.exit(1)

        # Create ETL Engine
        engine = ETLEngine(
            config_path=args.config,
            env_file=args.env_file,
            verbose=args.verbose,
        )

        # Execute or validate
        if args.dry_run:
            engine.dry_run()
        else:
            engine.execute()

    except KeyboardInterrupt:
        logger.warning("\nExecution interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error("Execution failed: %s", e)
        if args.verbose:
            logger.exception("Detailed error information:")
        sys.exit(1)


if __name__ == '__main__':
    cli_entry_point()
