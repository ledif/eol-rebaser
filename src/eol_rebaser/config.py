"""Configuration management for EOL Rebaser."""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration loading and validation."""

    DEFAULT_CONFIG_PATH = Path("/usr/share/eol-rebaser/migrations.conf")
    DEFAULT_CONFIG_DIR = Path("/usr/share/eol-rebaser/migrations.conf.d")

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager.

        Args:
            config_path: Optional custom path to configuration file
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config_dir = self.DEFAULT_CONFIG_DIR

    def load_config(self) -> Dict[str, Any]:
        """Load and merge configuration from main file and drop-ins.

        Returns:
            Merged configuration dictionary

        Raises:
            FileNotFoundError: If main config file doesn't exist
            ValueError: If configuration is invalid
        """
        # Load main configuration
        if not self.config_path.exists():
            logger.error(f"Configuration file not found: {self.config_path}")
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        logger.info(f"Loading configuration from {self.config_path}")
        config = self._load_yaml_file(self.config_path)

        # Load drop-in configurations
        if self.config_dir.exists():
            logger.info(f"Loading drop-in configurations from {self.config_dir}")
            drop_ins = []
            for conf_file in sorted(self.config_dir.glob("*.conf")):
                logger.debug(f"Loading drop-in: {conf_file}")
                drop_in_config = self._load_yaml_file(conf_file)
                drop_ins.append(drop_in_config)

            # Merge drop-ins into main config
            config = self._merge_configs(config, drop_ins)

        # Validate configuration
        self._validate_config(config)

        return config

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file.

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed configuration dictionary

        Raises:
            ValueError: If file cannot be parsed
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                return content or {}

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML from {file_path}: {e}")
            raise ValueError(f"Invalid YAML configuration file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to load configuration from {file_path}: {e}")
            raise ValueError(f"Invalid configuration file {file_path}: {e}")

    def _merge_configs(
        self, base_config: Dict[str, Any], drop_ins: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge drop-in configurations into base configuration.

        Args:
            base_config: Base configuration dictionary
            drop_ins: List of drop-in configuration dictionaries

        Returns:
            Merged configuration dictionary
        """
        merged = base_config.copy()

        for drop_in in drop_ins:
            if "migrations" in drop_in:
                merged.setdefault("migrations", []).extend(drop_in["migrations"])

        return merged

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration structure and content.

        Args:
            config: Configuration dictionary to validate

        Raises:
            ValueError: If configuration is invalid
        """
        if "migrations" not in config:
            raise ValueError("Configuration must contain 'migrations' section")

        migrations = config["migrations"]
        if not isinstance(migrations, list):
            raise ValueError("'migrations' must be a list")

        for i, migration in enumerate(migrations):
            self._validate_migration(migration, i)

    def _validate_migration(self, migration: Dict[str, Any], index: int) -> None:
        """Validate a single migration configuration.

        Args:
            migration: Migration configuration dictionary
            index: Migration index for error reporting

        Raises:
            ValueError: If migration configuration is invalid
        """
        required_fields = ["name", "from_pattern", "to_image", "reason"]

        for field in required_fields:
            if field not in migration:
                raise ValueError(f"Migration {index}: missing required field '{field}'")

        # Validate regex pattern
        try:
            re.compile(migration["from_pattern"])
        except re.error as e:
            raise ValueError(
                f"Migration {index}: invalid regex pattern '{migration['from_pattern']}': {e}"
            )

        # Validate effective_date if present
        if "effective_date" in migration:
            try:
                datetime.strptime(migration["effective_date"], "%Y-%m-%d")
            except ValueError as e:
                raise ValueError(
                    f"Migration {index}: invalid date format '{migration['effective_date']}': {e}"
                )

        logger.debug(f"Validated migration: {migration['name']}")

    def get_migrations_for_image(self, image: str) -> List[Dict[str, Any]]:
        """Get all migrations applicable to the given image.

        Args:
            image: Container image name to check

        Returns:
            List of applicable migration configurations
        """
        config = self.load_config()
        applicable_migrations = []

        for migration in config["migrations"]:
            pattern = migration["from_pattern"]
            if re.match(pattern, image):
                applicable_migrations.append(migration)

        return applicable_migrations
