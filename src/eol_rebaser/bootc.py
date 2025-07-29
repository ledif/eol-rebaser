"""Bootc integration for EOL Rebaser."""

import json
import logging
import os
import subprocess
from typing import Optional, Dict, Any, List


logger = logging.getLogger(__name__)


class BootcManager:
    """Manages bootc operations."""

    def __init__(self, use_sudo: bool = True):
        """Initialize bootc manager.

        Args:
            use_sudo: Whether to use sudo for bootc commands (default: True)
        """
        self.use_sudo = use_sudo
        self.bootc_cmd = ["sudo", "bootc"] if use_sudo else ["bootc"]

    def get_current_image(self) -> Optional[str]:
        """Get the currently booted container image.

        Returns:
            Current container image name or None if not found
        """
        try:
            # Get bootc status
            result = subprocess.run(
                self.bootc_cmd + ["status", "--json"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )

            status_data = json.loads(result.stdout)

            # Extract current image from status
            if "spec" in status_data and "image" in status_data["spec"]:
                image = status_data["spec"]["image"]["image"]
                logger.info(f"Current bootc image: {image}")
                return image
            else:
                logger.warning("Could not find image in bootc status output")
                return None

        except subprocess.CalledProcessError as e:
            if "root user" in str(e.stderr) or "root privilege" in str(e.stderr):
                logger.error(
                    "bootc requires root privileges. Make sure you have sudo access or run as root."
                )
            else:
                logger.error(f"Failed to get bootc status: {e}")
                logger.error(f"Command output: {e.stderr}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse bootc status JSON: {e}")
            return None
        except subprocess.TimeoutExpired:
            logger.error("Bootc status command timed out")
            return None
        except FileNotFoundError:
            logger.error("bootc command not found - is bootc installed?")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting current image: {e}")
            return None

    def rebase_to_image(self, new_image: str, dry_run: bool = False) -> bool:
        """Rebase the system to a new container image.

        Args:
            new_image: Target container image to rebase to
            dry_run: If True, only show what would be done

        Returns:
            True if successful, False otherwise
        """
        if dry_run:
            logger.info(f"DRY RUN: Would rebase to {new_image}")
            return True

        try:
            logger.info(f"Rebasing to image: {new_image}")

            # Use bootc switch for rebasing to a different image
            result = subprocess.run(
                self.bootc_cmd + ["switch", new_image],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout for rebase
            )

            if result.returncode == 0:
                logger.info("Rebase completed successfully")
                logger.info(f"stdout: {result.stdout}")
                return True
            else:
                if "root user" in str(result.stderr) or "root privilege" in str(
                    result.stderr
                ):
                    logger.error(
                        "bootc requires root privileges. Make sure you have sudo access or run as root."
                    )
                else:
                    logger.error(f"Rebase failed with return code {result.returncode}")
                    logger.error(f"stderr: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Rebase operation timed out")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during rebase: {e}")
            return False

    def get_available_images(self) -> List[str]:
        """Get list of available container images.

        Returns:
            List of available image names
        """
        # This is a placeholder - bootc doesn't have a direct way to list available images
        # In practice, this would need to query container registries or use other methods
        logger.debug("Getting available images (placeholder implementation)")
        return []

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information relevant to bootc operations.

        Returns:
            Dictionary containing system information
        """
        info = {}

        try:
            # Get bootc status for comprehensive system info
            result = subprocess.run(
                self.bootc_cmd + ["status", "--json"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )

            status_data = json.loads(result.stdout)
            info["bootc_status"] = status_data

            # Extract key information
            if "spec" in status_data:
                info["current_image"] = (
                    status_data["spec"].get("image", {}).get("image")
                )

            if "status" in status_data:
                info["booted"] = status_data["status"].get("booted")
                info["staged"] = status_data["status"].get("staged")
                info["rollback"] = status_data["status"].get("rollback")

        except Exception as e:
            logger.warning(f"Could not get comprehensive bootc status: {e}")

        # Get OS release information
        try:
            with open("/etc/os-release", "r") as f:
                os_release = {}
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        os_release[key] = value.strip('"')
                info["os_release"] = os_release
        except Exception as e:
            logger.warning(f"Could not read OS release information: {e}")

        return info

    def is_bootc_system(self) -> bool:
        """Check if this is a bootc-managed system.

        Returns:
            True if system is managed by bootc, False otherwise
        """
        try:
            # Try to run bootc status to see if it works
            result = subprocess.run(
                self.bootc_cmd + ["status"], capture_output=True, text=True, timeout=10
            )

            return result.returncode == 0

        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False

    def validate_image_reference(self, image: str) -> bool:
        """Validate that an image reference is properly formatted.

        Args:
            image: Container image reference to validate

        Returns:
            True if image reference appears valid, False otherwise
        """
        # Basic validation - ensure it looks like a container image reference
        if not image:
            return False

        # Should contain at least a registry/name or name:tag format
        if "/" in image or ":" in image:
            return True

        # Simple name might be valid too
        return len(image.strip()) > 0

    def check_privileges(self) -> bool:
        """Check if we have the necessary privileges to run bootc commands.

        Returns:
            True if we can run bootc commands, False otherwise
        """
        if os.geteuid() == 0:
            logger.debug("Running as root - bootc commands should work")
            return True

        if self.use_sudo:
            try:
                # Check if sudo is available (don't use -n to allow password prompts)
                result = subprocess.run(
                    ["which", "sudo"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    logger.debug(
                        "sudo command found - will use sudo for bootc operations"
                    )
                    return True
                else:
                    logger.warning("sudo command not found")
                    return False
            except Exception as e:
                logger.warning(f"Could not check for sudo availability: {e}")
                return False
        else:
            logger.warning(
                "Not running as root and sudo disabled - bootc commands may fail"
            )
            return False
