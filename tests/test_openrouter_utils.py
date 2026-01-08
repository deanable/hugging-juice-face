import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure project root is importable like other tests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import openrouter_utils

class TestOpenRouterUtils(unittest.TestCase):
    @patch('openrouter_utils.requests.get')
    def test_find_models_by_task_filters_image_models(self, mock_get):
        sample = [
            {"id": "model-a", "modalities": ["text"]},
            {"id": "model-b", "modalities": ["image", "text"]},
            {"id": "model-c", "modalities": ["vision"]},
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = sample
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        ids, downloaded = openrouter_utils.find_models_by_task('image-classification', token=None, limit=10)
        self.assertIn('model-b', ids)
        self.assertIn('model-c', ids)
        self.assertNotIn('model-a', ids)
        self.assertEqual(downloaded, [])

if __name__ == '__main__':
    unittest.main()
