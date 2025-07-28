"""Tests for EOL Rebaser."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os
import subprocess

# Import modules to test
from eol_rebaser.config import ConfigManager
from eol_rebaser.bootc import BootcManager
from eol_rebaser.migrator import ImageMigrator
from eol_rebaser.notifications import NotificationManager


class TestConfigManager(unittest.TestCase):
    """Test configuration management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        config_content = """
migrations:
  - name: "Test Migration"
    from_pattern: "test/image:.*"
    to_image: "test/new-image:latest"
    reason: "Test migration"
    effective_date: "2024-01-01"
"""
        self.config_path.write_text(config_content)
        
        config_manager = ConfigManager(self.config_path)
        config = config_manager.load_config()
        
        self.assertIn("migrations", config)
        self.assertEqual(len(config["migrations"]), 1)
        self.assertEqual(config["migrations"][0]["name"], "Test Migration")
        
    def test_invalid_config_raises_error(self):
        """Test that invalid configuration raises appropriate error."""
        # Test missing file
        config_manager = ConfigManager(Path("/nonexistent/config.yaml"))
        with self.assertRaises(FileNotFoundError):
            config_manager.load_config()
            
    def test_validate_migration_config(self):
        """Test migration configuration validation."""
        config_manager = ConfigManager()
        
        # Test valid migration
        valid_migration = {
            "name": "Test",
            "from_pattern": "test:.*",
            "to_image": "test:new", 
            "reason": "Testing"
        }
        config_manager._validate_migration(valid_migration, 0)  # Should not raise
        
        # Test invalid migration (missing required field)
        invalid_migration = {
            "name": "Test",
            "from_pattern": "test:.*"
            # Missing to_image and reason
        }
        with self.assertRaises(ValueError):
            config_manager._validate_migration(invalid_migration, 0)


class TestBootcManager(unittest.TestCase):
    """Test bootc operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bootc_manager = BootcManager()
        
    @patch('subprocess.run')
    def test_get_current_image_success(self, mock_run):
        """Test successful retrieval of current image."""
        # Mock successful bootc status output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '{"spec": {"image": {"image": "test/image:latest"}}}'
        mock_run.return_value = mock_result
        
        current_image = self.bootc_manager.get_current_image()
        self.assertEqual(current_image, "test/image:latest")
        
    @patch('subprocess.run')
    def test_get_current_image_failure(self, mock_run):
        """Test handling of bootc command failure."""
        # Mock failed bootc status
        mock_run.side_effect = subprocess.CalledProcessError(1, 'bootc')
        
        current_image = self.bootc_manager.get_current_image()
        self.assertIsNone(current_image)
        
    def test_validate_image_reference(self):
        """Test image reference validation."""
        # Valid references
        self.assertTrue(self.bootc_manager.validate_image_reference("registry.io/image:tag"))
        self.assertTrue(self.bootc_manager.validate_image_reference("image:tag"))
        self.assertTrue(self.bootc_manager.validate_image_reference("registry/image"))
        
        # Invalid references
        self.assertFalse(self.bootc_manager.validate_image_reference(""))
        self.assertFalse(self.bootc_manager.validate_image_reference(None))
        
    @patch('subprocess.run')
    def test_rebase_to_image_success(self, mock_run):
        """Test successful image rebase."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Rebase completed"
        mock_run.return_value = mock_result
        
        success = self.bootc_manager.rebase_to_image("test/image:new")
        self.assertTrue(success)
        
    @patch('subprocess.run')
    def test_rebase_to_image_failure(self, mock_run):
        """Test handling of rebase failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Rebase failed"
        mock_run.return_value = mock_result
        
        success = self.bootc_manager.rebase_to_image("test/image:new")
        self.assertFalse(success)


class TestImageMigrator(unittest.TestCase):
    """Test image migration logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_bootc = Mock(spec=BootcManager)
        self.mock_notifications = Mock(spec=NotificationManager)
        
        self.test_config = {
            "migrations": [
                {
                    "name": "Test Migration",
                    "from_pattern": "old/image:.*",
                    "to_image": "new/image:latest",
                    "reason": "Test migration",
                    "effective_date": "2020-01-01"  # Past date
                }
            ]
        }
        
        self.migrator = ImageMigrator(
            self.mock_bootc, 
            self.mock_notifications,
            self.test_config
        )
        
    def test_find_migration_match(self):
        """Test finding applicable migration."""
        migration = self.migrator.find_migration("old/image:v1.0")
        self.assertIsNotNone(migration)
        self.assertEqual(migration["name"], "Test Migration")
        
    def test_find_migration_no_match(self):
        """Test no migration found for non-matching image."""
        migration = self.migrator.find_migration("different/image:v1.0")
        self.assertIsNone(migration)
        
    def test_perform_migration_success(self):
        """Test successful migration execution."""
        self.mock_bootc.validate_image_reference.return_value = True
        self.mock_bootc.get_current_image.return_value = "old/image:v1.0"
        self.mock_bootc.rebase_to_image.return_value = True
        
        migration = self.test_config["migrations"][0]
        success = self.migrator.perform_migration(migration)
        
        self.assertTrue(success)
        self.mock_bootc.rebase_to_image.assert_called_once_with("new/image:latest")
        self.mock_notifications.notify_migration_success.assert_called_once()
        
    def test_perform_migration_failure(self):
        """Test migration failure handling."""
        self.mock_bootc.validate_image_reference.return_value = True
        self.mock_bootc.get_current_image.return_value = "old/image:v1.0"
        self.mock_bootc.rebase_to_image.return_value = False
        
        migration = self.test_config["migrations"][0]
        success = self.migrator.perform_migration(migration)
        
        self.assertFalse(success)
        self.mock_notifications.notify_migration_failure.assert_called_once()


class TestNotificationManager(unittest.TestCase):
    """Test notification system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.notification_manager = NotificationManager()
        
    @patch('subprocess.run')
    def test_check_desktop_environment(self, mock_run):
        """Test desktop environment detection."""
        # Mock successful desktop detection
        mock_result = Mock()
        mock_result.stdout = "x11"
        mock_run.return_value = mock_result
        
        # Create new instance to trigger detection
        nm = NotificationManager()
        # The actual detection result depends on the mocked subprocess calls
        
    @patch('subprocess.run')
    def test_send_desktop_notification(self, mock_run):
        """Test desktop notification sending."""
        self.notification_manager.desktop_available = True
        self.notification_manager._send_desktop_notification(
            "Test Title", 
            "Test Message"
        )
        
        # Should attempt to run notify-send
        mock_run.assert_called()
        
    def test_notify_migration_start(self):
        """Test migration start notification."""
        # Should not raise exception
        self.notification_manager.notify_migration_start(
            "Test Migration",
            "old/image:v1.0", 
            "new/image:latest",
            "Test reason"
        )

if __name__ == '__main__':
    unittest.main()
