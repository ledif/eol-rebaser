#!/usr/bin/env python3
"""
EOL Rebaser - Main entry point

Automatically rebase bootc systems when images reach end of life.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .config import ConfigManager
from .migrator import ImageMigrator
from .bootc import BootcManager
from .notifications import NotificationManager


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=level, format=format_string, handlers=[logging.StreamHandler(sys.stdout)]
    )


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Automatically rebase bootc systems when images reach EOL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  eol-rebaser --check              Check if migration is needed
  eol-rebaser --migrate            Perform migration if needed
  eol-rebaser --dry-run            Show what would be done without executing
  eol-rebaser --config /path/to/config.yaml  Use custom config file
        """,
    )

    parser.add_argument(
        "--check", action="store_true", help="Check if current image needs migration"
    )

    parser.add_argument(
        "--migrate", action="store_true", help="Perform migration if needed"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (default: /usr/share/eol-rebaser/migrations.yaml)",
    )

    parser.add_argument(
        "--force", action="store_true", help="Force migration even if not scheduled yet"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    parser.add_argument(
        "--no-sudo",
        action="store_true",
        help="Don't use sudo for bootc commands (requires root)",
    )

    parser.add_argument("--version", action="version", version="%(prog)s 0.1.3")

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config_manager = ConfigManager(args.config)
        config = config_manager.load_config()

        # Initialize managers
        bootc_manager = BootcManager(use_sudo=not args.no_sudo)
        notification_manager = NotificationManager()
        migrator = ImageMigrator(bootc_manager, notification_manager, config)

        # Get current image
        current_image = bootc_manager.get_current_image()
        if not current_image:
            logger.error("Could not determine current bootc image")
            logger.error("This may be due to insufficient privileges.")
            logger.error("Try running with: sudo python -m eol_rebaser --check")
            return 1

        logger.info(f"Current image: {current_image}")

        # Find applicable migration
        migration = migrator.find_migration(current_image)

        if args.check:
            if migration:
                print(f"Migration available: {migration['name']}")
                print(f"From: {current_image}")
                print(f"To: {migration['to_image']}")
                print(f"Reason: {migration['reason']}")
                return 0
            else:
                print("No migration needed")
                return 0

        if args.migrate or (not args.check and migration):
            if not migration:
                logger.info("No migration needed")
                return 0

            if args.dry_run:
                print("DRY RUN - Would perform the following migration:")
                print(f"  Name: {migration['name']}")
                print(f"  From: {current_image}")
                print(f"  To: {migration['to_image']}")
                print(f"  Reason: {migration['reason']}")
                return 0

            # Perform migration
            success = migrator.perform_migration(migration, args.force)
            return 0 if success else 1

        # If no specific action requested, just check and report
        if migration:
            logger.info(f"Migration available but not requested: {migration['name']}")
            return 0
        else:
            logger.info("No migration needed")
            return 0

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
