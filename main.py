"""
Main entry point for the Advanced Image Tagger application.
Now supports both original Tkinter and modern CustomTkinter GUI.
"""

import logging
import sys
import os
from logging_config import setup_logging

def main_original():
    """Run the original Tkinter GUI."""
    from gui_main import ImageTaggerGUI
    
    try:
        app = ImageTaggerGUI()
        app.mainloop()
    except Exception as e:
        logging.exception("Original GUI failed")
        raise

def main_modern():
    """Run the modern CustomTkinter GUI."""
    try:
        import customtkinter
        from gui_main_modern import ModernImageTaggerGUI
        
        app = ModernImageTaggerGUI()
        app.mainloop()
    except ImportError as e:
        logging.error(f"CustomTkinter not installed: {e}")
        print("Error: CustomTkinter not installed. Run: pip install customtkinter")
        sys.exit(1)
    except Exception as e:
        logging.exception("Modern GUI failed")
        raise

if __name__ == "__main__":
    try:
        # LOG CLEANUP: Remove old log files to keep the directory clean.
        # We delete all existing .log files before starting the new session.
        import glob
        for log_file in glob.glob("image_tagger_*.log"):
            try:
                os.remove(log_file)
            except Exception as e:
                print(f"Warning: Could not delete old log {log_file}: {e}")

        setup_logging()
        logging.info("Application starting.")

        # Log hardware diagnostics
        import huggingface_utils
        device_info = huggingface_utils.get_device_info()
        logging.info(f"Hardware Diagnostics: {device_info['debug_info']}")
        print(f"Hardware: {device_info['devices']} (Default: {device_info['default']})")

        # Check for PyTorch dependency
        try:
            import torch
        except ImportError:
            msg = "PyTorch is not installed. Models will not work.\nPlease run: pip install torch torchvision"
            logging.error(msg)
            print(f"CRITICAL: {msg}")
            try:
                import tkinter
                from tkinter import messagebox
                root = tkinter.Tk()
                root.withdraw()
                messagebox.showerror("Missing Dependency", msg)
            except Exception:
                pass
            sys.exit(1)
        
        # Default to modern GUI
        try:
            print("Starting modern CustomTkinter GUI...")
            main_modern()
        except Exception as e:
            print(f"Modern GUI failed: {e}")
            logging.error(f"Modern GUI failed: {e}")
            sys.exit(1)
            
        logging.info("Application closed.")
    except Exception as e:
        logging.exception("Fatal error in application")
        sys.exit(1)