"""User notification system for EOL Rebaser."""

import logging
import subprocess
from typing import Optional


logger = logging.getLogger(__name__)


class NotificationManager:
    """Manages user notifications during migration process."""
    
    def __init__(self):
        """Initialize notification manager."""
        self.desktop_available = self._check_desktop_environment()
        
    def _check_desktop_environment(self) -> bool:
        """Check if desktop environment is available for notifications.
        
        Returns:
            True if desktop notifications are available, False otherwise
        """
        try:
            # Check if we're running in a desktop session
            result = subprocess.run(
                ["loginctl", "show-session", "self", "-p", "Type", "--value"],
                capture_output=True,
                text=True,
                timeout=5
            )
            session_type = result.stdout.strip()
            
            # Check for graphical session types
            if session_type in ("x11", "wayland"):
                # Verify notify-send is available
                subprocess.run(
                    ["which", "notify-send"],
                    capture_output=True,
                    check=True,
                    timeout=5
                )
                logger.debug("Desktop notifications available")
                return True
                
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
            
        logger.debug("Desktop notifications not available")
        return False

    def notify_migration_start(self, migration_name: str, from_image: str, 
                             to_image: str, reason: str) -> None:
        """Notify user that migration is starting.
        
        Args:
            migration_name: Name of the migration being performed
            from_image: Source image being migrated from
            to_image: Target image being migrated to  
            reason: Reason for the migration
        """
        title = "System Image Migration Starting"
        message = (
            f"Migration: {migration_name}\n"
            f"From: {from_image}\n" 
            f"To: {to_image}\n"
            f"Reason: {reason}\n\n"
            f"Your system will reboot after the migration completes."
        )
    
        logger.info(f"Migration starting: {migration_name}")

        # Send desktop notification if available
        if self.desktop_available:
            self._send_desktop_notification(title, message, "system-software-update")

        # Always log to journal/console
        self._log_notification(title, message)

        # Send wall message to all users if we can
        self._send_wall_message(f"{title}: {message}")
        
    def notify_migration_success(self, migration_name: str, target_image: str) -> None:
        """Notify user that migration completed successfully.
        
        Args:
            migration_name: Name of the completed migration
            target_image: Target image that was migrated to
        """
        title = "System Image Migration Completed"
        message = (
            f"Migration '{migration_name}' completed successfully.\n"
            f"New image: {target_image}\n\n"
            f"Please reboot your system to use the new image."
        )

        logger.info(f"Migration completed successfully: {migration_name}")
        
        if self.desktop_available:
            self._send_desktop_notification(title, message, "system-software-update")

        self._log_notification(title, message)
        self._send_wall_message(f"{title}: {message}")
        
    def notify_migration_failure(self, migration_name: str, error: str) -> None:
        """Notify user that migration failed.
        
        Args:
            migration_name: Name of the failed migration
            error: Error message describing the failure
        """
        title = "System Image Migration Failed"
        message = (
            f"Migration '{migration_name}' failed.\n"
            f"Error: {error}\n\n"
            f"Your system remains on the current image. "
            f"Check system logs for more details."
        )
        
        logger.error(f"Migration failed: {migration_name} - {error}")
        
        if self.desktop_available:
            self._send_desktop_notification(title, message, "dialog-error", urgent=True)
            
        self._log_notification(title, message)
        self._send_wall_message(f"{title}: {message}")
        
    def notify_reboot_required(self, migration_name: str) -> None:
        """Notify user that a reboot is required to complete migration.
        
        Args:
            migration_name: Name of the migration requiring reboot
        """
        title = "Reboot Required"
        message = (
            f"Migration '{migration_name}' is complete but requires a reboot.\n"
            f"Please restart your system when convenient to use the new image."
        )
        
        logger.info(f"Reboot required for migration: {migration_name}")
        
        if self.desktop_available:
            self._send_desktop_notification(title, message, "system-reboot")
            
        self._log_notification(title, message)
        
    def _send_desktop_notification(self, title: str, message: str, 
                                 icon: str = "dialog-information",
                                 urgent: bool = False) -> None:
        """Send desktop notification using notify-send.
        
        Args:
            title: Notification title
            message: Notification message body
            icon: Icon name to display
            urgent: Whether notification should be marked urgent
        """
        try:
            cmd = [
                "notify-send",
                "--app-name=EOL Rebaser",
                "--icon=" + icon,
                title,
                message
            ]
            
            if urgent:
                cmd.extend(["--urgency=critical"])
            else:
                cmd.extend(["--urgency=normal"])
                
            subprocess.run(
                cmd,
                capture_output=True,
                timeout=10
            )
            
            logger.debug(f"Desktop notification sent: {title}")
            
        except Exception as e:
            logger.warning(f"Failed to send desktop notification: {e}")
            
    def _log_notification(self, title: str, message: str) -> None:
        """Log notification to system journal.
        
        Args:
            title: Notification title
            message: Notification message body
        """
        full_message = f"{title}: {message}"
        logger.info(full_message)
        
        # Also try to log to systemd journal if available
        try:
            subprocess.run(
                ["systemd-cat", "--identifier=eol-rebaser", "--priority=info"],
                input=full_message,
                text=True,
                timeout=5
            )
        except Exception:
            # Journal logging is optional
            pass
            
    def _send_wall_message(self, message: str) -> None:
        """Send wall message to all logged-in users.
        
        Args:
            message: Message to broadcast
        """
        try:
            subprocess.run(
                ["wall"],
                input=f"[EOL Rebaser] {message}",
                text=True,
                timeout=10
            )
            logger.debug("Wall message sent")
        except Exception as e:
            logger.debug(f"Could not send wall message: {e}")
            
    def prompt_user_confirmation(self, message: str) -> bool:
        """Prompt user for confirmation (when running interactively).
        
        Args:
            message: Message to display to user
            
        Returns:
            True if user confirmed, False otherwise
        """
        try:
            response = input(f"{message} (y/N): ").strip().lower()
            return response in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False
