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
        
        # Check for --gui flag or CUSTOM_GUI environment variable
        gui_mode = os.environ.get('CUSTOM_GUI', '').lower()
        
        if len(sys.argv) > 1:
            if sys.argv[1] == '--modern':
                gui_mode = 'modern'
            elif sys.argv[1] == '--original':
                gui_mode = 'original'
        
        # Default to modern GUI, fallback to original if issues
        if gui_mode == 'original':
            print("Starting with original Tkinter GUI...")
            main_original()
        elif gui_mode == 'modern' or not gui_mode:
            try:
                print("Starting with modern CustomTkinter GUI...")
                main_modern()
            except Exception as e:
                print(f"Modern GUI failed: {e}")
                print("Falling back to original Tkinter GUI...")
                logging.warning(f"Modern GUI failed, falling back: {e}")
                main_original()
        else:
            print("Usage: python main.py [--modern|--original]")
            sys.exit(1)
            
        logging.info("Application closed.")
    except Exception as e:
        logging.exception("Fatal error in application")
        sys.exit(1)