import unittest
import logging
import queue
import time
from unittest.mock import MagicMock
import customtkinter as ctk

# Import the class to test
# We need to hack the path to import from parent directory if needed, 
# but assuming we run from root `python -m tests.test_logging_performance`
import sys
import os
sys.path.append(os.getcwd())

from gui_main_modern import QueueHandler

class MockGUI:
    def __init__(self):
        self.log_queue = queue.Queue()
        self.log_box = MagicMock()
        self.after_calls = []
    
    def after(self, ms, func):
        self.after_calls.append((ms, func))

    def process_log_queue(self):
        # Copy-paste logic from gui_main_modern.py for unit testing in isolation
        # or we could import it if it were a standalone function.
        # optionally we can just assert on the handler behavior.
        
        # Testing the exact logic copied from implementation:
        try:
            messages = []
            while True:
                try:
                    msg = self.log_queue.get_nowait()
                    messages.append(msg)
                    if len(messages) >= 100:
                        break
                except queue.Empty:
                    break
            
            if messages and self.log_box:
                batch_msg = "\n".join(messages) + "\n"
                self.log_box.configure(state='normal')
                self.log_box.insert("end", batch_msg)
                self.log_box.see("end")
                self.log_box.configure(state='disabled')
                    
        except Exception as e:
            print(f"Log processing error: {e}")

class TestLoggingPerformance(unittest.TestCase):
    def test_queue_handler(self):
        """Test that QueueHandler puts messages into queue."""
        q = queue.Queue()
        handler = QueueHandler(q)
        logger = logging.getLogger("test_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        logger.info("Test message 1")
        logger.info("Test message 2")
        
        self.assertEqual(q.qsize(), 2)
        self.assertIn("Test message 1", q.get())
        self.assertIn("Test message 2", q.get())

    def test_batch_processing_performance(self):
        """Test performance of batch processing 1000 messages."""
        gui = MockGUI()
        
        # Fill queue with 1000 messages
        for i in range(1000):
            gui.log_queue.put(f"Log message {i}")
            
        start_time = time.time()
        
        # Process queue (should take 10 batches of 100)
        # We simulate the loop manually since 'after' is mocked
        batches_processed = 0
        while not gui.log_queue.empty():
            gui.process_log_queue()
            batches_processed += 1
            
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\nProcessed 1000 messages in {batches_processed} batches in {duration:.4f}s")
        
        # assertions
        self.assertEqual(batches_processed, 10) # 1000 / 100 = 10
        self.assertTrue(gui.log_box.insert.called)
        self.assertEqual(gui.log_box.insert.call_count, 10)
        
        # Ensure it's fast (arbitrary threshold, but 1000 in-memory ops should be < 0.1s)
        self.assertLess(duration, 0.5, "Batch processing is too slow!")

if __name__ == '__main__':
    unittest.main()
