import os
import sys
import types
import unittest

# Ensure project root is importable like other tests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui_main_modern import ModernImageTaggerGUI
from tests.settings_manager import SettingsManager


class DummyDropdown:
    def __init__(self):
        self.values = []
        self._selected = ""

    def configure(self, values=None):
        if values is not None:
            self.values = list(values)

    def set(self, value):
        self._selected = value

    def get(self):
        return self._selected


class DummyButton:
    def configure(self, **kwargs):
        self._cfg = kwargs


class DummyLabel:
    def configure(self, **kwargs):
        self._cfg = kwargs


class TestCloudModelSelection(unittest.TestCase):
    def test_saved_openrouter_model_is_selected_when_available(self):
        # Prepare fake GUI 'self'
        fake = types.SimpleNamespace()
        fake.model_task = types.SimpleNamespace(get=lambda: 'image-classification')
        fake.settings_manager = SettingsManager()
        fake.settings_manager.set('model_provider', 'OpenRouter')
        fake.settings_manager.set('openrouter_selected_model', 'open/router-model-2')
        fake.cloud_model_dropdown = DummyDropdown()
        fake.find_models_button = DummyButton()
        fake.status_label = DummyLabel()
        fake.all_models_with_tasks = {}

        # Call the unbound method with prepared data
        data = {
            'models': (['open/router-model-1', 'open/router-model-2'], [])
        }

        # Use the function directly from ModernImageTaggerGUI class
        ModernImageTaggerGUI._on_models_found(fake, data)

        # Assert the dropdown selected the saved model
        self.assertEqual(fake.cloud_model_dropdown.get(), 'open/router-model-2')


if __name__ == '__main__':
    unittest.main()
