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
        setup_logging()
        logging.info("Application starting.")

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