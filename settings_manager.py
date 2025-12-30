import json
import logging
from pathlib import Path
from typing import Dict, Any

SETTINGS_FILE = "user_settings.json"

class SettingsManager:
    DEFAULT_SETTINGS = {
        "device": "CPU",
        "batch_size": 1,
        "model_task": "image-classification",
        "selected_model": "",
        "truncation": True,
        "confidence_threshold": 0.0,
        "categories": "",
        "keywords": ""
    }

    def __init__(self, filename: str = SETTINGS_FILE):
        self.filepath = Path(filename)
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        """Load settings from JSON file."""
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r') as f:
                    loaded = json.load(f)
                    # Update defaults with loaded values (preserves new keys if defaults change)
                    self.settings.update(loaded)
                logging.info(f"Loaded settings from {self.filepath}")
            except Exception as e:
                logging.error(f"Failed to load settings: {e}")

    def save(self):
        """Save current settings to JSON file."""
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self.settings, f, indent=4)
            logging.info(f"Saved settings to {self.filepath}")
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        self.settings[key] = value

    def update_from_gui(self, gui_instance):
        """Capture values from GUI variables and save."""
        try:
            # Device
            if hasattr(gui_instance, 'device_var'):
                self.settings['device'] = gui_instance.device_var.get()
            
            # Batch Size
            if hasattr(gui_instance, 'batch_size_slider'):
                self.settings['batch_size'] = int(gui_instance.batch_size_slider.get())
            
            # Task
            if hasattr(gui_instance, 'model_task'):
                self.settings['model_task'] = gui_instance.model_task.get()
            
            # Model ID (from current selection or variable)
            if hasattr(gui_instance, 'model_dropdown'):
                self.settings['selected_model'] = gui_instance.model_dropdown.get()

            # Parameters
            if hasattr(gui_instance, 'truncation_var'):
                self.settings['truncation'] = gui_instance.truncation_var.get()
            if hasattr(gui_instance, 'threshold_slider'):
                self.settings['confidence_threshold'] = gui_instance.threshold_slider.get()
            
            # Text inputs
            if hasattr(gui_instance, 'categories_input'):
                 self.settings['categories'] = gui_instance.categories_input.get("1.0", "end-1c")
            if hasattr(gui_instance, 'keywords_input'):
                 self.settings['keywords'] = gui_instance.keywords_input.get("1.0", "end-1c")

            self.save()
        except Exception as e:
            logging.error(f"Error updating settings from GUI: {e}")
