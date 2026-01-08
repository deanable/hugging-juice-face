import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Make project importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import openrouter_utils
import config
import requests
import os

class TestOpenRouterInference(unittest.TestCase):
    @patch('openrouter_utils.requests.post')
    def test_image_classification_list_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = [{'label': 'Cat', 'score': 0.92}, {'label': 'Dog', 'score': 0.05}]
        mock_post.return_value = mock_resp

        # Create a temporary file
        from tempfile import NamedTemporaryFile
        tmp = NamedTemporaryFile(suffix='.jpg', delete=False)
        try:
            tmp.write(b'fakejpeg')
            tmp.flush()
            tmp.close()
            res = openrouter_utils.run_inference_api('open/router-model', str(tmp.name), config.MODEL_TASK_IMAGE_CLASSIFICATION, token='tok')
            self.assertIsInstance(res, list)
            self.assertEqual(res[0]['label'], 'Cat')
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

    @patch('openrouter_utils.requests.post')
    def test_image_to_text_normalization(self, mock_post):
        # Simulate chat/completions style response first
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {'choices': [{'message': {'content': 'A cat on a mat.'}}]}
        mock_post.return_value = mock_resp

        from tempfile import NamedTemporaryFile
        tmp = NamedTemporaryFile(suffix='.jpg', delete=False)
        try:
            tmp.write(b'fakejpeg')
            tmp.flush()
            tmp.close()
            res = openrouter_utils.run_inference_api('open/router-model', str(tmp.name), config.MODEL_TASK_IMAGE_TO_TEXT, token='tok')
            self.assertIsInstance(res, list)
            self.assertEqual(res[0]['generated_text'], 'A cat on a mat.')
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

    @patch('openrouter_utils.requests.post')
    def test_zero_shot_labels_scores_format(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {'labels': ['A','B'], 'scores': [0.7, 0.3]}
        mock_post.return_value = mock_resp

        from tempfile import NamedTemporaryFile
        tmp = NamedTemporaryFile(suffix='.jpg', delete=False)
        try:
            tmp.write(b'fakejpeg')
            tmp.flush()
            tmp.close()
            res = openrouter_utils.run_inference_api('open/router-model', str(tmp.name), config.MODEL_TASK_ZERO_SHOT, token='tok')
            self.assertIsInstance(res, dict)
            self.assertIn('labels', res)
            self.assertIn('scores', res)
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

    @patch('openrouter_utils.requests.post')
    def test_404_raises_value_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=MagicMock(status_code=404))
        mock_post.return_value = mock_resp

        from tempfile import NamedTemporaryFile
        tmp = NamedTemporaryFile(suffix='.jpg', delete=False)
        try:
            tmp.write(b'fakejpeg')
            tmp.flush()
            tmp.close()
            with self.assertRaises(ValueError):
                openrouter_utils.run_inference_api('open/router-model', str(tmp.name), config.MODEL_TASK_IMAGE_CLASSIFICATION, token='tok')
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

if __name__ == '__main__':
    unittest.main()
