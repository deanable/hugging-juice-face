
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gui_workers
import config

class TestDaminionLogicBug(unittest.TestCase):
    def setUp(self):
        self.mock_gui = MagicMock()
        self.mock_gui.stop_event.is_set.return_value = False
        self.mock_gui.q = MagicMock()
        self.mock_gui.daminion_client = MagicMock()
        self.mock_gui.daminion_client.download_thumbnail.return_value = MagicMock(exists=lambda: True)
        self.mock_gui.model = MagicMock()
        
        # Mock Image.open
        self.image_patcher = patch('gui_workers.Image')
        self.mock_image = self.image_patcher.start()
        self.mock_image.open.return_value = MagicMock()

        # Mock image_processing
        self.img_proc_patcher = patch('gui_workers.image_processing')
        self.mock_img_proc = self.img_proc_patcher.start()

    def tearDown(self):
        self.image_patcher.stop()
        self.img_proc_patcher.stop()

    def test_image_classification_uses_keywords(self):
        """
        FAIL CASE: Image Classification returns (cat="", kws=["tag"], desc="")
        Worker must use 'kws'.
        Current Bug: Worker uses 'cat' (empty) -> Does nothing.
        """
        self.mock_gui.model_task.get.return_value = config.TASK_DISPLAY_MAP[config.MODEL_TASK_IMAGE_CLASSIFICATION]
        
        # Mock extract_tags to return keywords only
        self.mock_img_proc.extract_tags_from_result.return_value = ("", ["tag1", "tag2"], "")
        
        gui_workers.process_daminion_worker(
            self.mock_gui, categories=[], keywords=[], items=[{'id': 1, 'fileName': 'test.jpg'}], device=-1
        )
        
        # Assert update_item_metadata was called with keywords
        # If bug exists, this will NOT be called or called with wrong args
        self.mock_gui.daminion_client.update_item_metadata.assert_called_with('1', keywords=["tag1", "tag2"])

    def test_zero_shot_uses_category(self):
        """
        FAIL CASE: Zero Shot returns (cat="Subject", kws=[], desc="")
        Worker must use 'cat'.
        Current Bug: Worker uses 'kws' (empty) -> Updates keywords=[].
        """
        self.mock_gui.model_task.get.return_value = config.TASK_DISPLAY_MAP[config.MODEL_TASK_ZERO_SHOT]
        
        # Mock extract_tags to return category only
        self.mock_img_proc.extract_tags_from_result.return_value = ("MySubject", [], "")
        
        gui_workers.process_daminion_worker(
            self.mock_gui, categories=[], keywords=["MySubject"], items=[{'id': 2, 'fileName': 'test.jpg'}], device=-1
        )
        
        # Assert update_item_metadata was called with category
        self.mock_gui.daminion_client.update_item_metadata.assert_called_with('2', category="MySubject")

if __name__ == '__main__':
    unittest.main()
