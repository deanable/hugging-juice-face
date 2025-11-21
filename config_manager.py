"""
Configuration file manager for user preferences.
"""

import json
import logging
from pathlib import Path

class ConfigManager:
    """Manages application configuration stored in a JSON file."""

    DEFAULT_CONFIG = {
        "last_model_task": "image-classification",
        "last_model_id": None,
        "last_directory": None,
        "default_categories": "Scenery, Portrait, Document, Animal",
        "default_keywords": "beach, sunset, dog, car, winter",
        "zero_shot_threshold": 0.9,
        "max_concurrent_workers": 4
    }

    def __init__(self, config_path=None):
        if config_path is None:
            config_path = Path.home() / ".image_tagger_config.json"
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self):
        """Load configuration from file, or create with defaults if not exists."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded_config)
                    logging.info(f"Configuration loaded from {self.config_path}")
                    return config
            except Exception as e:
                logging.exception(f"Failed to load config from {self.config_path}")
                return self.DEFAULT_CONFIG.copy()
        else:
            logging.info("No configuration file found, using defaults.")
            return self.DEFAULT_CONFIG.copy()

    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            logging.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logging.exception(f"Failed to save config to {self.config_path}")

    def get(self, key, default=None):
        """Get a configuration value."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Set a configuration value."""
        self.config[key] = value

    def reset_to_defaults(self):
        """Reset configuration to default values."""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save_config()
        logging.info("Configuration reset to defaults.")
