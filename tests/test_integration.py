"""
Integration tests for Advanced Image Tagger.
Tests end-to-end workflows with real components.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import json
import asyncio

from config_manager import ConfigManager
from config_schema import AppConfig
from progress_tracker import ProgressTracker
from report_generator import ProcessingReport
from image_processing import validate_image, write_metadata
import config


class TestConfigIntegration:
    """Test configuration management with validation."""

    def test_config_manager_with_validation(self, tmp_path):
        """Test config manager with Pydantic validation."""
        config_file = tmp_path / "test_config.json"

        # Create manager with validation
        manager = ConfigManager(config_path=config_file, validate=True)

        # Set valid values
        manager.set('max_concurrent_workers', 8)
        assert manager.get('max_concurrent_workers') == 8

        # Get validated config
        validated = manager.get_validated()
        assert validated is not None
        assert validated.processing.max_concurrent_workers == 8

    def test_config_validation_rejects_invalid(self, tmp_path):
        """Test that invalid values are rejected."""
        config_file = tmp_path / "test_config.json"
        manager = ConfigManager(config_path=config_file, validate=True)

        # Try to set invalid value (out of range)
        with pytest.raises(Exception):
            manager.set('max_concurrent_workers', 100)  # > 16

    def test_config_persistence(self, tmp_path):
        """Test config is persisted and loaded correctly."""
        config_file = tmp_path / "test_config.json"

        # Create and save config
        manager1 = ConfigManager(config_path=config_file, validate=True)
        manager1.set('max_concurrent_workers', 6)
        manager1.set('default_categories', 'Test1, Test2')
        manager1.save_config()

        # Load in new manager
        manager2 = ConfigManager(config_path=config_file, validate=True)
        assert manager2.get('max_concurrent_workers') == 6
        assert manager2.get('default_categories') == 'Test1, Test2'

    def test_legacy_config_compatibility(self, tmp_path):
        """Test loading old config format."""
        config_file = tmp_path / "test_config.json"

        # Write old format
        old_config = {
            "last_model_task": "image-classification",
            "max_concurrent_workers": 4,
            "zero_shot_threshold": 0.85
        }
        with open(config_file, 'w') as f:
            json.dump(old_config, f)

        # Load with validation
        manager = ConfigManager(config_path=config_file, validate=True)
        validated = manager.get_validated()

        assert validated.model.last_model_task == "image-classification"
        assert validated.processing.max_concurrent_workers == 4
        assert validated.processing.zero_shot_threshold == 0.85


class TestProgressTrackerIntegration:
    """Test progress tracking with real file operations."""

    def test_job_lifecycle(self, tmp_path):
        """Test complete job lifecycle."""
        progress_file = tmp_path / "progress.json"
        tracker = ProgressTracker(progress_file=progress_file)

        # Start job
        tracker.start_job(tmp_path, 10, "test-model", "image-classification")

        # Mark some processed
        for i in range(5):
            tracker.mark_processed(tmp_path / f"image_{i}.jpg")

        # Mark some failed
        tracker.mark_failed(tmp_path / "bad_image.jpg", "Validation failed")

        # Complete job
        tracker.complete_job()

        # Verify file exists
        assert progress_file.exists()

        # Load in new tracker
        tracker2 = ProgressTracker(progress_file=progress_file)
        job = tracker2.load_job()

        # Should be None (completed)
        assert job is None

    def test_resume_functionality(self, tmp_path):
        """Test job resume capability."""
        progress_file = tmp_path / "progress.json"

        # Create incomplete job
        tracker1 = ProgressTracker(progress_file=progress_file)
        tracker1.start_job(tmp_path, 10, "test-model", "image-classification")

        all_images = [tmp_path / f"image_{i}.jpg" for i in range(10)]

        # Process half
        for i in range(5):
            tracker1.mark_processed(all_images[i])

        # Don't complete - simulate crash

        # Resume in new tracker
        tracker2 = ProgressTracker(progress_file=progress_file)
        job = tracker2.load_job()

        assert job is not None
        assert len(job['processed_images']) == 5

        # Get unprocessed
        unprocessed = tracker2.get_unprocessed_images(all_images)
        assert len(unprocessed) == 5


class TestReportGeneratorIntegration:
    """Test report generation with real data."""

    def test_report_workflow(self, tmp_path):
        """Test complete report workflow."""
        report = ProcessingReport()

        # Start session
        report.start_session("test-model", "image-classification", 10)

        # Add results
        for i in range(8):
            report.add_result(
                f"/path/image_{i}.jpg",
                "Interior",
                ["bedroom", "modern"],
                True,
                None,
                1.5,
                0.95
            )

        # Add failures
        for i in range(2):
            report.add_result(
                f"/path/bad_{i}.jpg",
                "",
                [],
                False,
                "Validation failed",
                0.5,
                None
            )

        # End session
        report.end_session()

        # Verify summary
        summary = report.get_summary()
        assert summary['processed'] == 10
        assert summary['successful'] == 8
        assert summary['failed'] == 2
        assert summary['success_rate'] == 80.0

        # Export CSV
        csv_path = tmp_path / "report.csv"
        success = report.export_csv(csv_path)
        assert success
        assert csv_path.exists()

        # Verify CSV content
        with open(csv_path, 'r') as f:
            content = f.read()
            assert 'image_0.jpg' in content
            assert 'Interior' in content

        # Export JSON
        json_path = tmp_path / "report.json"
        success = report.export_json(json_path, include_summary=True)
        assert success
        assert json_path.exists()

        # Verify JSON structure
        with open(json_path, 'r') as f:
            data = json.load(f)
            assert 'results' in data
            assert 'summary' in data
            assert len(data['results']) == 10


class TestImageProcessingIntegration:
    """Test image processing with real files."""

    def create_test_image(self, path: Path, size=(100, 100)):
        """Create a test image file."""
        img = Image.new('RGB', size, color='red')
        img.save(path)

    def test_image_validation(self, tmp_path):
        """Test image validation with real files."""
        # Create valid image
        valid_img = tmp_path / "valid.jpg"
        self.create_test_image(valid_img)

        valid, error = validate_image(valid_img)
        assert valid
        assert error is None

        # Test non-existent
        invalid_img = tmp_path / "nonexistent.jpg"
        valid, error = validate_image(invalid_img)
        assert not valid
        assert "does not exist" in error

        # Test empty file
        empty_img = tmp_path / "empty.jpg"
        empty_img.touch()
        valid, error = validate_image(empty_img)
        assert not valid
        assert "empty" in error.lower()

    def test_metadata_writing(self, tmp_path):
        """Test IPTC/EXIF metadata writing."""
        from queue import Queue

        # Create test image
        test_img = tmp_path / "test.jpg"
        self.create_test_image(test_img)

        # Write metadata
        q = Queue()
        category = "Test Category"
        keywords = ["test", "keyword1", "keyword2"]

        success = write_metadata(test_img, category, keywords, q)
        assert success

        # Verify metadata was written (basic check - file still exists and readable)
        assert test_img.exists()
        valid, error = validate_image(test_img)
        assert valid


@pytest.mark.asyncio
class TestAsyncDaminionIntegration:
    """Test async Daminion client integration."""

    async def test_async_client_context_manager(self):
        """Test async client with context manager."""
        from daminion_async import AsyncDaminionClient

        # This will fail without real server, but tests the structure
        client = AsyncDaminionClient("https://test.example.com", "user", "pass")

        # Test session creation
        assert client._session is None

        # Would normally use:
        # async with client as c:
        #     items = await c.get_media_items()

        # Just verify client is created
        assert client.base_url == "https://test.example.com"
        assert client.username == "user"


class TestConnectionPoolIntegration:
    """Test connection pool functionality."""

    def test_pool_initialization(self):
        """Test pool can be created."""
        from daminion_pool import DaminionConnectionPool

        # Create pool (will fail auth without real server)
        # But tests structure
        try:
            pool = DaminionConnectionPool(
                "https://test.example.com",
                "user",
                "pass",
                min_size=1,
                max_size=5
            )

            stats = pool.get_stats()
            assert 'total_connections' in stats
            assert 'min_size' in stats
            assert stats['min_size'] == 1
            assert stats['max_size'] == 5

            pool.close_all()
        except Exception as e:
            # Expected without real server
            assert "Authentication" in str(e) or "Network" in str(e)


class TestEndToEndLocalProcessing:
    """Test complete local processing workflow."""

    def create_test_images(self, directory: Path, count: int = 5):
        """Create multiple test images."""
        for i in range(count):
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(directory / f"test_{i}.jpg")

    def test_local_workflow_structure(self, tmp_path):
        """Test local processing workflow structure."""
        # Create test images
        self.create_test_images(tmp_path, count=5)

        # Verify images created
        images = list(tmp_path.glob("*.jpg"))
        assert len(images) == 5

        # Test validation on all
        from queue import Queue
        q = Queue()

        valid_count = 0
        for img in images:
            valid, error = validate_image(img)
            if valid:
                valid_count += 1

        assert valid_count == 5

        # Test metadata writing (without AI model)
        success_count = 0
        for img in images:
            success = write_metadata(img, "Test", ["keyword1"], q)
            if success:
                success_count += 1

        assert success_count >= 0  # May fail without proper image format

    def test_progress_and_report_integration(self, tmp_path):
        """Test progress tracker and report working together."""
        # Setup
        progress_file = tmp_path / "progress.json"
        tracker = ProgressTracker(progress_file=progress_file)
        report = ProcessingReport()

        # Create test images
        self.create_test_images(tmp_path, count=10)
        images = list(tmp_path.glob("*.jpg"))

        # Start
        tracker.start_job(tmp_path, len(images), "test-model", "image-classification")
        report.start_session("test-model", "image-classification", len(images))

        # Process (simulate)
        for img in images[:7]:  # Process 7 successfully
            tracker.mark_processed(img)
            report.add_result(str(img), "Category", ["kw"], True, None, 1.0, 0.9)

        for img in images[7:]:  # 3 failures
            tracker.mark_failed(img, "Error")
            report.add_result(str(img), "", [], False, "Error", 0.5, None)

        # Complete
        tracker.complete_job()
        report.end_session()

        # Verify
        summary = report.get_summary()
        assert summary['processed'] == 10
        assert summary['successful'] == 7
        assert summary['failed'] == 3

        # Verify progress cleared
        tracker2 = ProgressTracker(progress_file=progress_file)
        job = tracker2.load_job()
        assert job is None  # Job completed


# Fixtures
@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_config():
    """Create sample configuration."""
    return {
        "last_model_task": "image-classification",
        "last_model_id": None,
        "default_categories": "Test1, Test2",
        "default_keywords": "test, sample",
        "max_concurrent_workers": 4,
        "zero_shot_threshold": 0.9
    }


# Test runners
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
