
import unittest
from unittest.mock import MagicMock, ANY
import sys
import os

# Add parent directory to path to import gui_workers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gui_workers
import config

class TestFixTypeError(unittest.TestCase):
    def test_process_daminion_worker_classification_call(self):
        """
        Verify that process_daminion_worker calls the model correctly for IMAGE_CLASSIFICATION.
        It should NOT pass candidate_labels.
        """
        # Mock GUI instance
        mock_gui = MagicMock()
        mock_gui.stop_event.is_set.return_value = False
        
        # Mock Queue
        mock_gui.q = MagicMock()
        
        # Mock Daminion Client
        mock_gui.daminion_client = MagicMock()
        # Mock items to be returned (one item)
        mock_gui.daminion_client.get_all_items_paginated.return_value = [{'id': 1, 'fileName': 'test.jpg'}]
        # Mock thumbnail download
        mock_gui.daminion_client.download_thumbnail.return_value = MagicMock(exists=lambda: True)
        
        # Mock Model
        # The critical part: assert called args later
        mock_gui.model = MagicMock()
        mock_gui.model.return_value = [{'label': 'cat', 'score': 0.9}] # Mock output
        
        # Mock PIL Image
        gui_workers.Image = MagicMock()
        gui_workers.Image.open.return_value = MagicMock()

        # Set task to IMAGE_CLASSIFICATION
        mock_gui.model_task.get.return_value = config.TASK_DISPLAY_MAP[config.MODEL_TASK_IMAGE_CLASSIFICATION]
        
        # Run worker directly (it will run for one item and finish)
        categories = ["cat", "dog"]
        keywords = []
        
        # We need to simulate the worker logic.
        # Since I can't easily reproduce the crash without the actual transformers pipeline which enforces the args,
        # I will check HOW the mock was called.
        
        try:
            gui_workers.process_daminion_worker(
                mock_gui, 
                categories=categories, 
                keywords=keywords,
                items=[{'id': 1, 'fileName': 'test.jpg'}], # Pass explicit items to avoid fetching
                device=-1
            )
        except Exception as e:
            # If the code crashes (e.g. if we used a real pipeline), we'd catch it here.
            # But with a MagicMock model, it won't crash on extra args unless we configure it to.
            pass
            
        # ASSERTION
        # Check the call arguments to mock_gui.model()
        # We expect it to be called with JUST the image, and maybe some kwargs, 
        # BUT NOT candidate_labels.
        
        call_args = mock_gui.model.call_args
        if call_args:
            args, kwargs = call_args
            print(f"Model called with kwargs: {kwargs}")
            
            if 'candidate_labels' in kwargs:
                self.fail("Regression: process_daminion_worker passed 'candidate_labels' to IMAGE_CLASSIFICATION model!")
            else:
                 print("Success: candidate_labels NOT passed.")
        else:
             self.fail("Model was not called!")

if __name__ == '__main__':
    unittest.main()
