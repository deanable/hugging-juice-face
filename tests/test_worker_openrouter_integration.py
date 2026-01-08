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
        tmp.close()  # Close file handle so other processes can access it
        try:
            img = Image.new('RGB', (16,16), color=(255,0,0))
            img.save(tmp.name, format='JPEG')

            # Mock Path.stat().st_size to return int
            # Since process_images_worker uses Path(tmp.name), we need to patch pathlib.Path or mock the object it returns.
            # However, simpler way is to patch validate_image to bypass the size check which uses stat()
            # We already patch validate_image above.

            # The error "> not supported between MagicMock and int" implies validate_image logic is running inside worker?
            # Wait, we patched `image_processing.validate_image`.
            # Let's check gui_workers.py to see where validate_image is imported from.
            # It imports `import image_processing`.
            # And calls `image_processing.validate_image(path)`.

            # If validate_image is mocked, why does it fail inside?
            # Ah, maybe process_images_worker does its own checks?
            # No, looking at gui_workers.py:
            # try:
            #    valid, _ = image_processing.validate_image(path)

            # So the mock should work.
            # Wait, the error log says:
            # ERROR root:gui_workers.py:579 Failed to load image /tmp/tmpdcy29t26.jpg: '>' not supported between instances of 'MagicMock' and 'int'

            # Let's check line 579 of gui_workers.py (approx).
            # It's likely `if img.width > max_dim or img.height > max_dim:`
            # This happens inside the try/except block where Image.open is called.
            # `img` comes from `Image.open(path)`.
            # If we didn't patch `Image.open` inside `gui_workers`, it uses real PIL.
            # Real PIL Image returns real integers for width/height.

            # But wait, TestWorkerOpenRouterIntegration doesn't patch gui_workers.Image
            # It imports `process_images_worker`.

            # If `validate_image` is mocked to return True, code proceeds to `Image.open(path)`.
            # `img = Image.open(path)`
            # `if img.width > max_dim ...`

            # If `img` is a real PIL image, width/height are ints.
            # Why would they be MagicMocks?

            # Maybe `validate_image` is NOT correctly patched because `gui_workers` imports `image_processing` module, not the function?
            # `from gui_workers import process_images_worker`
            # In gui_workers: `import image_processing`
            # Call: `image_processing.validate_image`

            # The test uses `@patch('image_processing.validate_image')`.
            # This patches `image_processing.validate_image` globally if `image_processing` was imported.

            # BUT, look at the error again.
            # `Failed to load image ... '>' not supported between instances of 'MagicMock' and 'int'`

            # If `validate_image` was NOT patched, it would run real validation.
            # Real validation calls `image_path.stat().st_size`.
            # `image_path` is a real `Path` object to a temp file.
            # `stat().st_size` is a real int.

            # UNLESS `image_files` passed to worker contains Mocks?
            # `process_images_worker(fake, [Path(tmp.name)], ...)`
            # Passing real Path object.

            # Let's verify the trace again.
            # `gui_workers.py:579`
            # `max_dim = 512`
            # `if img.width > max_dim or img.height > max_dim:`

            # So `img.width` is a MagicMock.
            # This means `Image.open` returned a MagicMock.
            # Why? We didn't patch `Image` in this test class?
            # `tests/test_daminion_logic_bug.py` patched `gui_workers.Image`.
            # `tests/test_worker_openrouter_integration.py` does NOT patch `Image`.

            # Wait, `unittest.mock.patch` without context manager or stop() might leak?
            # `TestDaminionLogicBug` uses `patch` in `setUp` and `stop` in `tearDown`.
            # So it should be clean.

            # Is it possible `Image` is being patched somewhere else?
            # Or `sys.modules` caching a patched version?

            # Let's explicitely patch `gui_workers.Image` in this test to return a real-like object or real image.
            # Or just use real Image since we have a real file.

            # Actually, the error implies `Image.open` IS returning a Mock.
            # Let's check imports in `tests/test_worker_openrouter_integration.py`.
            # `from PIL import Image` inside the test function creates a real image.

            # Let's try patching `gui_workers.Image` properly to ensure it behaves.

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
