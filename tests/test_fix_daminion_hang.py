
import unittest
from unittest.mock import MagicMock, patch
import queue
import logging

# Import the module to test
# We need to mock customtkinter before importing gui_main_modern if possible, 
# or patch it where it is used.
import sys
# Mock ctk module entirely to avoid GUI requirement
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

mock_ctk = MagicMock()
class DummyCTk:
    def __init__(self, *args, **kwargs): pass
    def title(self, *args): pass
    def geometry(self, *args): pass
    def resizable(self, *args): pass
    def after(self, *args): pass
    def mainloop(self): pass
    def protocol(self, *args): pass
    def destroy(self): pass
    
mock_ctk.CTk = DummyCTk
sys.modules['customtkinter'] = mock_ctk
sys.modules['gui_steps_modern'] = MagicMock()

# Now import the class to test
from gui_main_modern import ModernImageTaggerGUI

class TestDaminionHangFix(unittest.TestCase):
    def setUp(self):
        # Prevent __init__ from running full GUI setup which might fail
        with patch('gui_main_modern.ModernImageTaggerGUI.__init__', return_value=None):
            self.gui = ModernImageTaggerGUI()
            # Manually initialize the minimal attributes needed for the test
            self.gui.q = queue.Queue()
            self.gui.daminion_status_label = MagicMock()
            self.gui.status_label = MagicMock()
            self.gui.model_task = MagicMock()
            # Mock _create_widgets or similar if called, but we skipped init
            
    @patch('gui_handlers_modern.show_modern_messagebox')
    def test_daminion_error_handling(self, mock_mb):
        """Test that the 'daminion_error' message is correctly handled."""
        
        # 1. Simulate the worker sending an error message
        error_msg = "Connection timed out"
        message = {'type': 'daminion_error', 'error': error_msg}
        self.gui.q.put(message)
        
        # 2. Process the message using the dispatch logic
        # We call _handle_message directly to simulate the loop processing one item
        msg = self.gui.q.get()
        self.gui._handle_message(msg)
        
        # 3. Verify the handler was called
        # The handler should:
        # a) Update the status label to "❌ Connection Failed"
        self.gui.daminion_status_label.configure.assert_called_with(
            text="❌ Connection Failed", 
            text_color="red"
        )
        
        # b) Show the error messagebox
        mock_mb.assert_called_once()
        args, _ = mock_mb.call_args
        self.assertEqual(args[0], self.gui) # first arg is self
        self.assertEqual(args[1], "Connection Error")
        self.assertIn(error_msg, args[2])
        self.assertEqual(args[3], "error")
        
    def test_daminion_success_handling(self):
        """Test that 'daminion_connected' message updates the UI correctly."""
        
        # 1. Simulate success message
        message = {'type': 'daminion_connected', 'item_count': 123}
        self.gui.q.put(message)
        
        # 2. Process message
        msg = self.gui.q.get()
        
        # Mocking update_step_states since it's called by the handler
        with patch('gui_handlers_modern.update_step_states'):
            self.gui._handle_message(msg)
            
        # 3. Verify status label update
        self.gui.daminion_status_label.configure.assert_called_with(
            text="✅ Connected!",
            text_color="green"
        )
        
        self.gui.status_label.configure.assert_called_with(
            text="✅ Connected to Daminion: 123 items"
        )

if __name__ == '__main__':
    unittest.main()
