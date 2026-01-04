import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
import huggingface_utils

class TestAPIIntegration(unittest.TestCase):
    def setUp(self):
        self.image_path = "test_image.jpg"
        # Create dummy image
        with open(self.image_path, "w") as f:
            f.write("dummy content")

    def tearDown(self):
        if os.path.exists(self.image_path):
            os.remove(self.image_path)

    @patch('huggingface_utils.InferenceClient')
    def test_image_classification(self, MockClient):
        # Setup mock
        mock_instance = MockClient.return_value
        expected_response = [{"label": "cat", "score": 0.9}]
        mock_instance.image_classification.return_value = expected_response
        
        # Run
        result = huggingface_utils.run_inference_api(
            "test/model", 
            self.image_path, 
            config.MODEL_TASK_IMAGE_CLASSIFICATION, 
            "hf_token"
        )
        
        # Verify
        mock_instance.image_classification.assert_called_with(self.image_path, model="test/model")
        self.assertEqual(result, expected_response)

    @patch('huggingface_utils.InferenceClient')
    def test_zero_shot(self, MockClient):
        # Setup mock
        mock_instance = MockClient.return_value
        expected_response = [{"label": "cat", "score": 0.9}]
        mock_instance.zero_shot_image_classification.return_value = expected_response
        
        # Run
        params = {"candidate_labels": ["cat", "dog"]}
        result = huggingface_utils.run_inference_api(
            "test/model", 
            self.image_path, 
            config.MODEL_TASK_ZERO_SHOT, 
            "hf_token",
            parameters=params
        )
        
        # Verify
        mock_instance.zero_shot_image_classification.assert_called_with(
            self.image_path, 
            model="test/model", 
            candidate_labels=["cat", "dog"]
        )
        self.assertEqual(result, expected_response)

    @patch('requests.post')
    def test_image_to_text(self, mock_post):
        # Setup mock
        expected_response = [{"generated_text": "a cat"}]
        mock_response = MagicMock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Run
        params = {"generate_kwargs": {"max_new_tokens": 10}}
        result = huggingface_utils.run_inference_api(
            "test/model", 
            self.image_path, 
            config.MODEL_TASK_IMAGE_TO_TEXT, 
            "hf_token",
            parameters=params
        )
        
        # Verify
        mock_post.assert_called()
        call_args = mock_post.call_args
        self.assertIn("https://router.huggingface.co/hf-inference/models/test/model", call_args[0][0])
        self.assertEqual(call_args[1]['json']['parameters']['max_new_tokens'], 10)
        self.assertEqual(result, expected_response)

if __name__ == '__main__':
    unittest.main()
