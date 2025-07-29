"""Image migration logic for EOL Rebaser."""

import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

from .bootc import BootcManager
from .notifications import NotificationManager


logger = logging.getLogger(__name__)


class ImageMigrator:
    """Handles image migration logic and execution."""

    def __init__(
        self,
        bootc_manager: BootcManager,
        notification_manager: NotificationManager,
        config: Dict[str, Any],
    ):
        """Initialize image migrator.

        Args:
            bootc_manager: Bootc operations manager
            notification_manager: User notification manager
            config: Migration configuration
        """
        self.bootc_manager = bootc_manager
        self.notification_manager = notification_manager
        self.config = config

    def find_migration(self, current_image: str) -> Optional[Dict[str, Any]]:
        """Find applicable migration for the current image.

        Args:
            current_image: Current container image name

        Returns:
            Migration configuration if found, None otherwise
        """
        if "migrations" not in self.config:
            logger.warning("No migrations configured")
            return None

        migrations = self.config["migrations"]
        logger.debug(
            f"Checking {len(migrations)} migrations for image: {current_image}"
        )

        for migration in migrations:
            if self._is_migration_applicable(migration, current_image):
                logger.info(f"Found applicable migration: {migration['name']}")
                return migration

        logger.debug("No applicable migration found")
        return None

    def _is_migration_applicable(
        self, migration: Dict[str, Any], current_image: str
    ) -> bool:
        """Check if a migration applies to the current image.

        Args:
            migration: Migration configuration
            current_image: Current container image name

        Returns:
            True if migration applies, False otherwise
        """
        # Check if image matches the pattern
        pattern = migration.get("from_pattern", "")
        if not re.match(pattern, current_image):
            logger.debug(f"Image {current_image} does not match pattern {pattern}")
            return False

        # Check if migration is effective yet
        effective_date = migration.get("effective_date")
        if effective_date:
            try:
                effective_dt = datetime.strptime(effective_date, "%Y-%m-%d")
                if datetime.now() < effective_dt:
                    logger.debug(
                        f"Migration not yet effective (effective: {effective_date})"
                    )
                    return False
            except ValueError as e:
                logger.warning(f"Invalid effective_date format: {effective_date}: {e}")

        logger.debug(f"Migration {migration['name']} is applicable")
        return True

    def _resolve_target_image(
        self, migration: Dict[str, Any], current_image: str
    ) -> str:
        """Resolve target image using regex substitution if needed.

        Args:
            migration: Migration configuration
            current_image: Current container image name

        Returns:
            Resolved target image name
        """
        target_template = migration.get("to_image", "")
        from_pattern = migration.get("from_pattern", "")

        # Check if target template contains regex substitution patterns
        if "\\" in target_template and from_pattern:
            try:
                # Use regex substitution to transform the image name
                target_image = re.sub(from_pattern, target_template, current_image)
                logger.debug(
                    f"Resolved target image: {current_image} -> {target_image}"
                )
                return target_image
            except re.error as e:
                logger.error(f"Failed to resolve target image pattern: {e}")
                return target_template
        else:
            # Use target template as-is (legacy behavior)
            return target_template

    def perform_migration(self, migration: Dict[str, Any], force: bool = False) -> bool:
        """Perform the specified migration.

        Args:
            migration: Migration configuration to execute
            force: Force migration even if not normally applicable

        Returns:
            True if migration was successful, False otherwise
        """
        migration_name = migration.get("name", "Unknown")
        reason = migration.get("reason", "Image migration")

        # Get current image for target resolution
        current_image = self.bootc_manager.get_current_image()
        if not current_image:
            logger.error("Could not determine current image")
            return False

        # Resolve target image using regex substitution if needed
        target_image = self._resolve_target_image(migration, current_image)

        logger.info(f"Starting migration: {migration_name}")
        logger.info(f"Current image: {current_image}")
        logger.info(f"Target image: {target_image}")
        logger.info(f"Reason: {reason}")

        # Validate target image
        if not self.bootc_manager.validate_image_reference(target_image):
            logger.error(f"Invalid target image reference: {target_image}")
            return False

        # Check if we're already on the target image
        if current_image == target_image:
            logger.info("Already on target image, no migration needed")
            return True

        try:
            # Send pre-migration notification
            self.notification_manager.notify_migration_start(
                migration_name, current_image, target_image, reason
            )

            # Perform the rebase
            logger.info("Executing bootc rebase...")
            success = self.bootc_manager.rebase_to_image(target_image)

            if success:
                logger.info("Migration completed successfully")
                self.notification_manager.notify_migration_success(
                    migration_name, target_image
                )

                # Log migration for future reference
                self._log_migration(migration, current_image, target_image)

                return True
            else:
                logger.error("Migration failed during rebase")
                self.notification_manager.notify_migration_failure(
                    migration_name, "Rebase operation failed"
                )
                return False

        except Exception as e:
            logger.error(f"Unexpected error during migration: {e}")
            self.notification_manager.notify_migration_failure(migration_name, str(e))
            return False

    def _log_migration(
        self, migration: Dict[str, Any], from_image: str, to_image: str
    ) -> None:
        """Log completed migration for record keeping.

        Args:
            migration: Migration configuration that was executed
            from_image: Source image that was migrated from
            to_image: Target image that was migrated to
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "migration_name": migration.get("name"),
            "from_image": from_image,
            "to_image": to_image,
            "reason": migration.get("reason"),
            "effective_date": migration.get("effective_date"),
        }

        logger.info(f"Migration log: {log_entry}")

        # Could write to a migration log file here if needed
        # For now, just log to the main log

    def get_pending_migrations(
        self, current_image: str, include_future: bool = False
    ) -> List[Dict[str, Any]]:
        """Get list of pending migrations for the current image.

        Args:
            current_image: Current container image name
            include_future: Include migrations not yet effective

        Returns:
            List of pending migration configurations
        """
        pending = []

        if "migrations" not in self.config:
            return pending

        for migration in self.config["migrations"]:
            # Check pattern match
            pattern = migration.get("from_pattern", "")
            if not re.match(pattern, current_image):
                continue

            # Check effective date if not including future migrations
            if not include_future:
                effective_date = migration.get("effective_date")
                if effective_date:
                    try:
                        effective_dt = datetime.strptime(effective_date, "%Y-%m-%d")
                        if datetime.now() < effective_dt:
                            continue
                    except ValueError:
                        # Skip migrations with invalid dates
                        continue

            pending.append(migration)

        return pending

    def validate_migration_config(self, migration: Dict[str, Any]) -> List[str]:
        """Validate a migration configuration.

        Args:
            migration: Migration configuration to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check required fields
        required_fields = ["name", "from_pattern", "to_image", "reason"]
        for field in required_fields:
            if field not in migration:
                errors.append(f"Missing required field: {field}")

        # Validate regex pattern
        pattern = migration.get("from_pattern", "")
        if pattern:
            try:
                re.compile(pattern)
            except re.error as e:
                errors.append(f"Invalid regex pattern '{pattern}': {e}")

        # Validate target image
        target_image = migration.get("to_image", "")
        if target_image:
            # If target contains regex substitution patterns, validate differently
            if "\\" in target_image:
                # For regex substitution patterns, just check basic format
                if not target_image.strip():
                    errors.append("Target image template cannot be empty")
            else:
                # For literal target images, validate as normal image reference
                if not self.bootc_manager.validate_image_reference(target_image):
                    errors.append(f"Invalid target image reference: {target_image}")

        # Validate effective date
        effective_date = migration.get("effective_date")
        if effective_date:
            try:
                datetime.strptime(effective_date, "%Y-%m-%d")
            except ValueError as e:
                errors.append(f"Invalid effective_date format '{effective_date}': {e}")

        return errors
