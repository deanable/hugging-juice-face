"""
Pydantic schemas for configuration validation.
Provides type-safe configuration with validation.
"""

from typing import Optional, List
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import config


class ProcessingConfig(BaseModel):
    """Configuration for image processing settings."""

    max_concurrent_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum number of concurrent worker threads"
    )
    zero_shot_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for zero-shot classification"
    )
    max_image_size_mb: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum image file size in MB"
    )
    max_keywords_per_image: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum keywords to extract per image"
    )

    @field_validator('max_concurrent_workers')
    @classmethod
    def validate_workers(cls, v):
        """Ensure worker count is reasonable."""
        if v > 16:
            raise ValueError("Too many concurrent workers may cause system instability")
        return v


class ModelConfig(BaseModel):
    """Configuration for AI model settings."""

    last_model_task: str = Field(
        default=config.MODEL_TASK_IMAGE_CLASSIFICATION,
        description="Last used model task type"
    )
    last_model_id: Optional[str] = Field(
        default=None,
        description="Last used model identifier"
    )
    model_search_limit: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Maximum number of models to return in search"
    )
    hf_token: Optional[str] = Field(
        default=None,
        description="Hugging Face API Token"
    )

    @field_validator('last_model_task')
    @classmethod
    def validate_task(cls, v):
        """Ensure task is valid."""
        valid_tasks = [
            config.MODEL_TASK_IMAGE_CLASSIFICATION,
            config.MODEL_TASK_ZERO_SHOT,
            config.MODEL_TASK_IMAGE_TO_TEXT
        ]
        if v not in valid_tasks:
            raise ValueError(f"Invalid model task. Must be one of: {valid_tasks}")
        return v


class DaminionConfig(BaseModel):
    """Configuration for Daminion DAMS connection."""

    url: str = Field(
        default="https://interiors.daminion.net",
        description="Daminion server URL"
    )
    username: str = Field(
        default="",
        description="Daminion username"
    )
    rate_limit: float = Field(
        default=0.1,
        ge=0.0,
        le=5.0,
        description="Minimum seconds between API calls"
    )
    batch_size: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Number of items to process per batch"
    )
    timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Request timeout in seconds"
    )

    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        """Ensure URL is valid."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip('/')


class TaggingConfig(BaseModel):
    """Configuration for image tagging."""

    default_categories: str = Field(
        default="Scenery, Portrait, Document, Animal",
        min_length=1,
        description="Default categories for classification"
    )
    default_keywords: str = Field(
        default="beach, sunset, dog, car, winter",
        min_length=1,
        description="Default keywords for zero-shot"
    )

    @field_validator('default_categories', 'default_keywords')
    @classmethod
    def validate_comma_separated(cls, v):
        """Ensure value is comma-separated."""
        if ',' not in v and len(v.split()) == 1:
            # Single word is ok
            return v
        # Multiple values should have commas
        items = [x.strip() for x in v.split(',') if x.strip()]
        if len(items) == 0:
            raise ValueError("Must provide at least one value")
        return ', '.join(items)  # Normalize spacing


class DirectoryConfig(BaseModel):
    """Configuration for directory paths."""

    last_directory: Optional[Path] = Field(
        default=None,
        description="Last selected image directory"
    )

    @field_validator('last_directory')
    @classmethod
    def validate_directory(cls, v):
        """Validate directory exists if specified."""
        if v is not None:
            if not v.exists():
                # Don't fail, just warn and return None
                return None
            if not v.is_dir():
                raise ValueError(f"Path is not a directory: {v}")
        return v


class AppConfig(BaseModel):
    """Complete application configuration."""

    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    daminion: DaminionConfig = Field(default_factory=DaminionConfig)
    tagging: TaggingConfig = Field(default_factory=TaggingConfig)
    directory: DirectoryConfig = Field(default_factory=DirectoryConfig)

    @model_validator(mode='after')
    def validate_config(self):
        """Cross-field validation."""
        # Ensure reasonable settings
        if self.processing.max_concurrent_workers > 8 and self.processing.max_image_size_mb > 100:
            # Warn about high memory usage
            pass
        return self

    def to_legacy_dict(self) -> dict:
        """Convert to legacy config manager format for backward compatibility."""
        return {
            'max_concurrent_workers': self.processing.max_concurrent_workers,
            'zero_shot_threshold': self.processing.zero_shot_threshold,
            'last_model_task': self.model.last_model_task,
            'last_model_id': self.model.last_model_id,
            'hf_token': self.model.hf_token,
            'daminion_url': self.daminion.url,
            'daminion_username': self.daminion.username,
            'default_categories': self.tagging.default_categories,
            'default_keywords': self.tagging.default_keywords,
            'last_directory': str(self.directory.last_directory) if self.directory.last_directory else None,
        }

    @classmethod
    def from_legacy_dict(cls, data: dict) -> 'AppConfig':
        """Create from legacy config manager format."""
        return cls(
            processing=ProcessingConfig(
                max_concurrent_workers=data.get('max_concurrent_workers', 4),
                zero_shot_threshold=data.get('zero_shot_threshold', 0.9),
            ),
            model=ModelConfig(
                last_model_task=data.get('last_model_task', config.MODEL_TASK_IMAGE_CLASSIFICATION),
                last_model_id=data.get('last_model_id'),
                hf_token=data.get('hf_token'),
            ),
            daminion=DaminionConfig(
                url=data.get('daminion_url', 'https://interiors.daminion.net'),
                username=data.get('daminion_username', ''),
            ),
            tagging=TaggingConfig(
                default_categories=data.get('default_categories', 'Scenery, Portrait, Document, Animal'),
                default_keywords=data.get('default_keywords', 'beach, sunset, dog, car, winter'),
            ),
            directory=DirectoryConfig(
                last_directory=Path(data['last_directory']) if data.get('last_directory') else None,
            ),
        )


class ValidationError(Exception):
    """Custom validation error with detailed messages."""

    def __init__(self, errors: list):
        self.errors = errors
        messages = []
        for error in errors:
            field = ' -> '.join(str(loc) for loc in error['loc'])
            messages.append(f"{field}: {error['msg']}")
        super().__init__('\n'.join(messages))
