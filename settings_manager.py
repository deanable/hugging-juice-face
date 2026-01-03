import json
import logging
import winreg
from pathlib import Path
from typing import Dict, Any

SETTINGS_FILE = "user_settings.json"
REGISTRY_PATH = r"Software\HuggingJuiceFace"

class SettingsManager:
    DEFAULT_SETTINGS = {
        "device": "CPU",
        "batch_size": 1,
        "model_task": "image-classification",
        "selected_model": "",
        "truncation": True,
        "confidence_threshold": 0.0,
        "categories": "",
        "keywords": "",
        "hf_api_token": "" # Loaded from registry
    }

    def __init__(self, filename: str = SETTINGS_FILE):
        self.filepath = Path(filename)
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        """Load settings from JSON file and Registry."""
        # 1. Load JSON file (General Settings)
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
                logging.info(f"Loaded settings from {self.filepath}")
            except Exception as e:
                logging.error(f"Failed to load settings: {e}")

        # 2. Load API Key from Registry (Security/System-wide)
        registry_key = self.load_api_key_from_registry()
        if registry_key:
            self.settings['hf_api_token'] = registry_key

    def save(self):
        """Save current settings to JSON file."""
        try:
            # Exclude sensitivity from JSON if desired? 
            # For now, we keep them distinct. 
            # We don't save 'hf_api_token' to JSON to prefer Registry.
            data_to_save = self.settings.copy()
            if 'hf_api_token' in data_to_save:
                del data_to_save['hf_api_token']

            with open(self.filepath, 'w') as f:
                json.dump(data_to_save, f, indent=4)
            logging.info(f"Saved settings to {self.filepath}")
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")

    def load_api_key_from_registry(self) -> str:
        """Load HF API Token from Windows Registry."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
                value, _ = winreg.QueryValueEx(key, "HFApiToken")
                return str(value)
        except FileNotFoundError:
            return ""
        except Exception as e:
            logging.error(f"Registry Load Error: {e}")
            return ""

    def save_api_key_to_registry(self, token: str):
        """Save HF API Token to Windows Registry."""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
                winreg.SetValueEx(key, "HFApiToken", 0, winreg.REG_SZ, token)
            # Update local memory too
            self.settings['hf_api_token'] = token
            logging.info("Saved API Token to Registry.")
        except Exception as e:
            logging.error(f"Registry Save Error: {e}")

    def load_daminion_password_from_registry(self) -> str:
        """Load Daminion Password from Windows Registry."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
                value, _ = winreg.QueryValueEx(key, "DaminionPassword")
                return str(value)
        except FileNotFoundError:
            return ""
        except Exception as e:
            logging.error(f"Registry Load Error (Daminion): {e}")
            return ""

    def save_daminion_password_to_registry(self, password: str):
        """Save Daminion Password to Windows Registry."""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
                winreg.SetValueEx(key, "DaminionPassword", 0, winreg.REG_SZ, password)
            logging.info("Saved Daminion Password to Registry.")
        except Exception as e:
            logging.error(f"Registry Save Error (Daminion): {e}")

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
            
            # Model ID (Local)
            if hasattr(gui_instance, 'model_dropdown'):
                self.settings['selected_model'] = gui_instance.model_dropdown.get()

            # Parameters
            if hasattr(gui_instance, 'truncation_var'):
                self.settings['truncation'] = gui_instance.truncation_var.get()
            if hasattr(gui_instance, 'threshold_slider'):
                self.settings['confidence_threshold'] = gui_instance.threshold_slider.get()
            
            # Text inputs
            if hasattr(gui_instance, 'categories_entry'): # NOTE: Corrected name from 'categories_input' to 'categories_entry' match gui_main attributes
                 self.settings['categories'] = gui_instance.categories_entry.get()
            if hasattr(gui_instance, 'keywords_entry'): # Corrected name
                 self.settings['keywords'] = gui_instance.keywords_entry.get()

            self.save()
        except Exception as e:
            logging.error(f"Error updating settings from GUI: {e}")
