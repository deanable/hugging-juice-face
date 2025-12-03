"""
Unit tests for Pydantic configuration schemas.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from config_schema import (
    ProcessingConfig,
    ModelConfig,
    DaminionConfig,
    TaggingConfig,
    DirectoryConfig,
    AppConfig,
    ValidationError
)
import config


class TestProcessingConfig:
    """Test processing configuration validation."""

    def test_valid_config(self):
        """Test valid configuration."""
        cfg = ProcessingConfig(
            max_concurrent_workers=8,
            zero_shot_threshold=0.85,
            max_image_size_mb=100,
            max_keywords_per_image=15
        )
        assert cfg.max_concurrent_workers == 8
        assert cfg.zero_shot_threshold == 0.85

    def test_workers_validation(self):
        """Test worker count validation."""
        # Valid range
        cfg = ProcessingConfig(max_concurrent_workers=16)
        assert cfg.max_concurrent_workers == 16

        # Out of range
        with pytest.raises(PydanticValidationError):
            ProcessingConfig(max_concurrent_workers=20)

        with pytest.raises(PydanticValidationError):
            ProcessingConfig(max_concurrent_workers=0)

    def test_threshold_validation(self):
        """Test threshold validation."""
        # Valid
        cfg = ProcessingConfig(zero_shot_threshold=0.5)
        assert cfg.zero_shot_threshold == 0.5

        # Out of range
        with pytest.raises(PydanticValidationError):
            ProcessingConfig(zero_shot_threshold=1.5)

        with pytest.raises(PydanticValidationError):
            ProcessingConfig(zero_shot_threshold=-0.1)

    def test_defaults(self):
        """Test default values."""
        cfg = ProcessingConfig()
        assert cfg.max_concurrent_workers == 4
        assert cfg.zero_shot_threshold == 0.9
        assert cfg.max_image_size_mb == 50
        assert cfg.max_keywords_per_image == 20


class TestModelConfig:
    """Test model configuration validation."""

    def test_valid_config(self):
        """Test valid model configuration."""
        cfg = ModelConfig(
            last_model_task=config.MODEL_TASK_IMAGE_CLASSIFICATION,
            last_model_id="google/vit-base-patch16-224"
        )
        assert cfg.last_model_task == config.MODEL_TASK_IMAGE_CLASSIFICATION
        assert cfg.last_model_id == "google/vit-base-patch16-224"

    def test_invalid_task(self):
        """Test invalid task validation."""
        with pytest.raises(PydanticValidationError):
            ModelConfig(last_model_task="invalid-task")

    def test_search_limit(self):
        """Test search limit validation."""
        cfg = ModelConfig(model_search_limit=50)
        assert cfg.model_search_limit == 50

        # Out of range
        with pytest.raises(PydanticValidationError):
            ModelConfig(model_search_limit=5)  # < 10

        with pytest.raises(PydanticValidationError):
            ModelConfig(model_search_limit=600)  # > 500


class TestDaminionConfig:
    """Test Daminion configuration validation."""

    def test_valid_config(self):
        """Test valid Daminion config."""
        cfg = DaminionConfig(
            url="https://example.daminion.net",
            username="testuser",
            rate_limit=0.2,
            batch_size=100
        )
        assert cfg.url == "https://example.daminion.net"
        assert cfg.username == "testuser"

    def test_url_validation(self):
        """Test URL validation."""
        # Valid
        cfg = DaminionConfig(url="https://test.com")
        assert cfg.url == "https://test.com"

        cfg = DaminionConfig(url="http://test.com")
        assert cfg.url == "http://test.com"

        # Invalid
        with pytest.raises(PydanticValidationError):
            DaminionConfig(url="ftp://test.com")

        with pytest.raises(PydanticValidationError):
            DaminionConfig(url="test.com")  # No protocol

    def test_rate_limit_validation(self):
        """Test rate limit validation."""
        cfg = DaminionConfig(rate_limit=2.0)
        assert cfg.rate_limit == 2.0

        # Out of range
        with pytest.raises(PydanticValidationError):
            DaminionConfig(rate_limit=-0.1)

        with pytest.raises(PydanticValidationError):
            DaminionConfig(rate_limit=10.0)

    def test_batch_size_validation(self):
        """Test batch size validation."""
        cfg = DaminionConfig(batch_size=75)
        assert cfg.batch_size == 75

        with pytest.raises(PydanticValidationError):
            DaminionConfig(batch_size=0)

        with pytest.raises(PydanticValidationError):
            DaminionConfig(batch_size=300)


class TestTaggingConfig:
    """Test tagging configuration validation."""

    def test_valid_config(self):
        """Test valid tagging config."""
        cfg = TaggingConfig(
            default_categories="Cat1, Cat2, Cat3",
            default_keywords="key1, key2, key3"
        )
        assert "Cat1" in cfg.default_categories
        assert "key1" in cfg.default_keywords

    def test_comma_separated_validation(self):
        """Test comma-separated value validation."""
        # Valid with commas
        cfg = TaggingConfig(default_categories="A, B, C")
        assert cfg.default_categories == "A, B, C"

        # Valid single word
        cfg = TaggingConfig(default_categories="Single")
        assert cfg.default_categories == "Single"

        # Empty string
        with pytest.raises(PydanticValidationError):
            TaggingConfig(default_categories="")


class TestAppConfig:
    """Test complete application configuration."""

    def test_valid_config(self):
        """Test valid complete configuration."""
        cfg = AppConfig(
            processing=ProcessingConfig(max_concurrent_workers=8),
            model=ModelConfig(last_model_task=config.MODEL_TASK_ZERO_SHOT),
            daminion=DaminionConfig(url="https://test.com"),
            tagging=TaggingConfig(default_categories="A, B"),
            directory=DirectoryConfig()
        )
        assert cfg.processing.max_concurrent_workers == 8
        assert cfg.model.last_model_task == config.MODEL_TASK_ZERO_SHOT

    def test_defaults(self):
        """Test default configuration."""
        cfg = AppConfig()
        assert cfg.processing.max_concurrent_workers == 4
        assert cfg.model.last_model_task == config.MODEL_TASK_IMAGE_CLASSIFICATION
        assert cfg.daminion.batch_size == 50

    def test_legacy_conversion(self):
        """Test conversion to/from legacy format."""
        # Create config
        cfg = AppConfig()
        cfg.processing.max_concurrent_workers = 6
        cfg.model.last_model_id = "test-model"

        # Convert to legacy
        legacy = cfg.to_legacy_dict()
        assert legacy['max_concurrent_workers'] == 6
        assert legacy['last_model_id'] == "test-model"
        assert 'zero_shot_threshold' in legacy

        # Convert back
        cfg2 = AppConfig.from_legacy_dict(legacy)
        assert cfg2.processing.max_concurrent_workers == 6
        assert cfg2.model.last_model_id == "test-model"

    def test_partial_legacy_data(self):
        """Test loading with missing legacy fields."""
        legacy = {
            "max_concurrent_workers": 8,
            # Other fields missing - should use defaults
        }

        cfg = AppConfig.from_legacy_dict(legacy)
        assert cfg.processing.max_concurrent_workers == 8
        assert cfg.processing.zero_shot_threshold == 0.9  # Default


class TestValidationError:
    """Test custom validation error."""

    def test_error_message_formatting(self):
        """Test error message formatting."""
        try:
            ProcessingConfig(max_concurrent_workers=100)
        except PydanticValidationError as e:
            error = ValidationError(e.errors())
            message = str(error)
            assert "max_concurrent_workers" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
