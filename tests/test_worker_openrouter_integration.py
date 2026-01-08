import os
import sys
import queue
import threading
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui_workers import process_images_worker
import config

class DummyProgressTracker:
    def __init__(self):
        self.completed = False
    def complete_job(self):
        self.completed = True

class TestWorkerOpenRouterIntegration(unittest.TestCase):
    @patch('openrouter_utils.run_inference_api')
    @patch('image_processing.validate_image')
    @patch('image_processing.extract_tags_from_result')
    @patch('image_processing.write_metadata_with_retry')
    def test_process_images_with_openrouter_cloud(self, mock_write_meta, mock_extract, mock_validate, mock_api):
        # Prepare mocks
        mock_validate.return_value = (True, None)
        mock_api.return_value = [{'label': 'Cat', 'score': 0.95}]
        mock_extract.return_value = ("Animal", ["Cat"], "A cat on a mat.")
        mock_write_meta.return_value = True

        # Create a temporary image file
        from tempfile import NamedTemporaryFile
        from PIL import Image
        tmp = NamedTemporaryFile(suffix='.jpg', delete=False)
        try:
            img = Image.new('RGB', (16,16), color=(255,0,0))
            img.save(tmp.name, format='JPEG')

            # Fake GUI instance
            fake = type('F', (), {})()
            fake.q = queue.Queue()
            fake.stop_event = threading.Event()
            # Set display task to the UI label that maps to image-classification
            fake.model_task = type('T', (), {'get': lambda self=None: config.TASK_DISPLAY_MAP[config.MODEL_TASK_IMAGE_CLASSIFICATION]})()
            fake.progress_tracker = DummyProgressTracker()

            from pathlib import Path
            # Call worker with Path objects
            process_images_worker(fake, [Path(tmp.name)], [], [], device=-1, batch_size=1, truncation=True, threshold=0.0, mode='cloud', token='tok', cloud_model_id='open/router-model', provider='OpenRouter')

            # Collect messages
            msgs = []
            while not fake.q.empty():
                msgs.append(fake.q.get())

            # Find progress_done message
            done_msgs = [m for m in msgs if m.get('type') == 'progress_done']
            self.assertTrue(len(done_msgs) == 1)
            done = done_msgs[0]
            self.assertEqual(done.get('processed_count'), 1)
            self.assertEqual(done.get('error_count'), 0)
            self.assertTrue(fake.progress_tracker.completed)

            # Ensure API was called with expected args
            mock_api.assert_called()
            mock_write_meta.assert_called()

        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

if __name__ == '__main__':
    unittest.main()
