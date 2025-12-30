"""
Configuration file manager for user preferences.
Enhanced with Pydantic validation.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional
from pydantic import ValidationError as PydanticValidationError

from config_schema import AppConfig, ValidationError

class ConfigManager:
    """Manages application configuration with validation.

    Now uses Pydantic for type-safe configuration validation.
    Maintains backward compatibility with existing config files.
    """

    DEFAULT_CONFIG = {
        "last_model_task": "image-classification",
        "last_model_id": None,
        "hf_token": None,
        "last_directory": None,
        "default_categories": "Scenery, Portrait, Document, Animal",
        "default_keywords": "beach, sunset, dog, car, winter",
        "zero_shot_threshold": 0.9,
        "max_concurrent_workers": 4
    }

    def __init__(self, config_path=None, validate: bool = True):
        """Initialize config manager.

        Args:
            config_path: Path to config file (default: ~/.image_tagger_config.json)
            validate: Whether to validate config with Pydantic (default: True)
        """
        if config_path is None:
            config_path = Path.home() / ".image_tagger_config.json"
        self.config_path = Path(config_path)
        self.validate = validate
        self._validated_config: Optional[AppConfig] = None
        self.config = self._load_config()

    def _load_config(self):
        """Load configuration from file with optional validation."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded_config)

                    # Validate with Pydantic if enabled
                    if self.validate:
                        try:
                            self._validated_config = AppConfig.from_legacy_dict(config)
                            # Update config with validated values
                            config = self._validated_config.to_legacy_dict()
                            logging.info(f"Configuration loaded and validated from {self.config_path}")
                        except PydanticValidationError as e:
                            logging.warning(f"Configuration validation failed: {e}")
                            logging.warning("Using default values for invalid fields")
                            # Use defaults for invalid fields
                            self._validated_config = AppConfig()
                            config = self._validated_config.to_legacy_dict()
                    else:
                        logging.info(f"Configuration loaded from {self.config_path} (validation disabled)")

                    return config
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON in config file: {e}")
                return self.DEFAULT_CONFIG.copy()
            except Exception as e:
                logging.exception(f"Failed to load config from {self.config_path}")
                return self.DEFAULT_CONFIG.copy()
        else:
            logging.info("No configuration file found, using defaults.")
            if self.validate:
                self._validated_config = AppConfig()
            return self.DEFAULT_CONFIG.copy()

    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            logging.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logging.exception(f"Failed to save config to {self.config_path}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value with optional validation.

        Args:
            key: Configuration key
            value: Value to set

        Raises:
            ValidationError: If validation is enabled and value is invalid
        """
        # If validation enabled, validate the change
        if self.validate and self._validated_config:
            try:
                # Create a temporary config with the change
                temp_config = self.config.copy()
                temp_config[key] = value
                validated = AppConfig.from_legacy_dict(temp_config)
                # Validation passed, update
                self._validated_config = validated
                self.config = validated.to_legacy_dict()
            except PydanticValidationError as e:
                logging.error(f"Validation failed for {key}={value}: {e}")
                raise ValidationError(e.errors())
        else:
            self.config[key] = value

    def get_validated(self) -> Optional[AppConfig]:
        """Get the validated configuration object.

        Returns:
            AppConfig instance if validation is enabled, None otherwise
        """
        return self._validated_config

    def reset_to_defaults(self):
        """Reset configuration to default values."""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save_config()
        logging.info("Configuration reset to defaults.")
