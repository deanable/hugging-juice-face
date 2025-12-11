"""
Modern GUI for the Advanced Image Tagger application using CustomTkinter.
Migration from Tkinter to modern, professional appearance.
"""

import logging
import tkinter as tk
import threading
import queue
import shutil
import time
from pathlib import Path
from functools import partial
from typing import Optional, List, Dict

# Import CustomTkinter
import customtkinter as ctk

# Import application modules
import config
from config_manager import ConfigManager
from progress_tracker import ProgressTracker
from daminion_client import DaminionClient
from report_generator import ProcessingReport

# Import modular components (will update these too)
import gui_steps_modern as gui_steps
import gui_handlers_modern as gui_handlers
import gui_workers


class ModernImageTaggerGUI(ctk.CTk):
    """Main application window with step-by-step workflow using CustomTkinter."""

    def __init__(self):
        super().__init__()
        
        # Configure CustomTkinter appearance
        ctk.set_appearance_mode("light")  # Options: "light", "dark", "system"
        ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"
        
        self.title(config.APP_NAME)
        self.geometry("1000x900")
        self.resizable(True, True)

        # Initialize state
        self.q = queue.Queue()
        self.model = None
        self._dl_start_time = None
        self._dl_total_bytes = None
        self._dl_last_bytes = 0
        self._dl_last_time = None
        self.image_dir = None
        self.stop_event = threading.Event()
        self.config_manager = ConfigManager()
        self.progress_tracker = ProgressTracker()
        self.daminion_client: Optional[DaminionClient] = None
        self.processing_mode = "local"
        self.report = ProcessingReport()
        self.processing_start_time = None

        self.all_models = set()
        self.downloaded_models = set()
        
        # Initialize attributes for modern GUI
        self.daminion_url_entry: Optional[ctk.CTkEntry] = None
        self.daminion_username_entry: Optional[ctk.CTkEntry] = None
        self.daminion_password_entry: Optional[ctk.CTkEntry] = None
        self.daminion_status_label: Optional[ctk.CTkLabel] = None
        self.daminion_connect_button: Optional[ctk.CTkButton] = None
        self.find_models_button: Optional[ctk.CTkButton] = None
        self.status_label: Optional[ctk.CTkLabel] = None
        self.model_listbox: Optional[ctk.CTkScrollableFrame] = None
        self.load_model_button: Optional[ctk.CTkButton] = None
        self.model_task: Optional[ctk.CTkOptionMenu] = None
        self.categories_entry: Optional[ctk.CTkEntry] = None
        self.keywords_entry: Optional[ctk.CTkEntry] = None
        self.scope_var: Optional[ctk.CTkOptionMenu] = None
        self.collection_path: Optional[ctk.CTkEntry] = None
        self.start_button: Optional[ctk.CTkButton] = None
        self.progress_bar: Optional[ctk.CTkProgressBar] = None
        self.progress_label: Optional[ctk.CTkLabel] = None
        self.time_label: Optional[ctk.CTkLabel] = None
        self.daminion_collection_combo: Optional[ctk.CTkComboBox] = None
        self.refresh_collections_btn: Optional[ctk.CTkButton] = None
        self.model_info_text: Optional[ctk.CTkTextbox] = None
        self.model_progress_bar: Optional[ctk.CTkProgressBar] = None
        self.model_progress_label: Optional[ctk.CTkLabel] = None
        self.daminion_collections: List[Dict] = []
        
        # Theme toggle button
        self.theme_button: Optional[ctk.CTkButton] = None

        self._create_widgets()
        self._create_menu()
        gui_handlers.update_step_states(self)

        try:
            gui_handlers.on_scope_change(self)
        except Exception:
            pass

        self.after(100, self.process_queue)
        self.after(200, self.scan_local_models)  # Scan for local models on startup
        logging.info("Modern GUI initialized with step-by-step workflow.")

    def _create_menu(self):
        """Create application menu bar with modern styling."""
        # CustomTkinter doesn't have built-in menu bar like tkinter
        # We'll create a custom menu system
        pass

    def _create_widgets(self):
        """Create main UI widgets using CustomTkinter."""
        # Create main container with padding
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Title section with modern styling
        title_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 20))

        title_label = ctk.CTkLabel(
            title_frame, 
            text="🤖 AI-Powered Image Tagger",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack()

        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="Modern AI tagging for local files and Daminion DAMS",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        subtitle_label.pack(pady=(5, 0))

        # Theme toggle
        self.theme_button = ctk.CTkButton(
            title_frame,
            text="🌙 Dark Mode",
            width=100,
            height=30,
            command=self._toggle_theme,
            fg_color="gray",
            hover_color="darkgray"
        )
        self.theme_button.pack(anchor="e", pady=(10, 0))

        # Create tabbed interface for steps
        self.tab_view = ctk.CTkTabview(main_container)
        self.tab_view.pack(fill="both", expand=True, pady=(0, 20))

        # Add tabs for each step
        self.tab_view.add("📁 Step 1: Source")
        self.tab_view.add("🤖 Step 2: Model") 
        self.tab_view.add("⚙️ Step 3: Config")
        self.tab_view.add("▶️ Step 4: Process")

        # Create step content
        gui_steps.create_step1_source(self.tab_view.tab("📁 Step 1: Source"), self)
        gui_steps.create_step2_model(self.tab_view.tab("🤖 Step 2: Model"), self)
        gui_steps.create_step3_config(self.tab_view.tab("⚙️ Step 3: Config"), self)
        gui_steps.create_step4_process(self.tab_view.tab("▶️ Step 4: Process"), self)

        # Progress section at bottom
        gui_steps.create_progress_section(main_container, self)

    def _toggle_theme(self):
        """Toggle between light and dark mode."""
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Light":
            ctk.set_appearance_mode("dark")
            self.theme_button.configure(text="☀️ Light Mode")
        else:
            ctk.set_appearance_mode("light")
            self.theme_button.configure(text="🌙 Dark Mode")

    # Event handlers (delegate to gui_handlers module)
    def on_model_task_change(self, event=None):
        gui_handlers.on_model_task_change(self, event)

    def on_mode_change(self, mode):
        gui_handlers.on_mode_change(self, mode)

    def on_scope_change(self, event=None):
        gui_handlers.on_scope_change(self, event)

    def on_daminion_connect(self):
        gui_handlers.on_daminion_connect(self)

    def on_find_models(self):
        gui_handlers.on_find_models(self)

    def on_load_model(self):
        gui_handlers.on_load_model(self)

    def on_start_processing(self):
        gui_handlers.on_start_processing(self)

    def on_stop_processing(self):
        gui_handlers.on_stop_processing(self)

    def on_select_directory(self):
        gui_handlers.on_select_directory(self)

    def on_refresh_collections(self):
        gui_handlers.on_refresh_collections(self)

    # Menu methods
    def show_cache_path(self):
        gui_handlers.show_cache_path(self)

    def clear_cache(self):
        gui_handlers.clear_cache(self)

    def export_report_csv(self):
        gui_handlers.export_report_csv(self)

    def export_report_json(self):
        gui_handlers.export_report_json(self)

    def show_report_summary(self):
        gui_handlers.show_report_summary(self)

    def scan_local_models(self):
        gui_handlers.scan_local_models(self)

    # Queue processing
    def process_queue(self):
        """Process messages from worker threads."""
        try:
            while True:
                message = self.q.get_nowait()
                self._handle_message(message)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue)

    def _handle_message(self, message):
        """Handle messages from worker threads."""
        message_type = message.get('type', 'unknown')
        
        if message_type == 'model_loaded':
            self._on_model_loaded(message)
        elif message_type == 'model_download_progress':
            self._on_model_download_progress(message)
        elif message_type == 'progress':
            self._on_progress_update(message)
        elif message_type == 'status_update':
            self._on_status_update(message)
        elif message_type == 'error':
            self._on_error(message)
        elif message_type == 'daminion_connected':
            self._on_daminion_connected(message)
        elif message_type == 'progress_done':
            self._on_processing_done(message)
        else:
            logging.warning(f"Unknown message type: {message_type}")

    def _on_model_loaded(self, message):
        """Handle model loaded message."""
        self.model = message['model']
        self.status_label.configure(text=f"✅ Model loaded: {message['model_name']}")
        logging.info(f"Model loaded successfully: {message['model_name']}")

    def _on_model_download_progress(self, message):
        """Handle model download progress."""
        if self.model_progress_bar:
            progress = message.get('progress', 0.0)
            self.model_progress_bar.set(progress)
            if message.get('status'):
                self.model_progress_label.configure(text=message['status'])

    def _on_progress_update(self, message):
        """Handle progress update message."""
        progress = message.get('progress', 0.0)
        current = message.get('current', 0)
        total = message.get('total', 0)
        processed = message.get('processed', [])
        
        if self.progress_bar:
            self.progress_bar.set(progress)
        
        status_text = f"Processing: {current}/{total} images"
        if message.get('current_image'):
            status_text += f" | {message['current_image']}"
        
        if self.progress_label:
            self.progress_label.configure(text=status_text)

        # Update elapsed time
        if self.processing_start_time:
            elapsed = time.time() - self.processing_start_time
            if self.time_label:
                self.time_label.configure(text=f"⏱️ Elapsed: {elapsed:.1f}s")

        # Log some processed items
        if processed and len(processed) % 10 == 0:  # Log every 10 items
            latest = processed[-1]
            logging.info(f"Processed: {latest.get('filename', 'Unknown')} -> {latest.get('category', 'N/A')}")

    def _on_status_update(self, message):
        """Handle status update message."""
        status_text = message.get('status', '')
        if self.status_label:
            self.status_label.configure(text=f"ℹ️ {status_text}")
        logging.info(f"Status: {status_text}")

    def _on_error(self, message):
        """Handle error message."""
        error_text = message.get('error', 'Unknown error')
        logging.error(f"Processing error: {error_text}")
        
        # Show error in modern dialog
        error_dialog = ctk.CTkToplevel(self)
        error_dialog.title("Error")
        error_dialog.geometry("400x200")
        error_dialog.transient(self)
        error_dialog.grab_set()
        
        error_label = ctk.CTkLabel(
            error_dialog,
            text="❌ Error Occurred",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        error_label.pack(pady=20)
        
        error_message = ctk.CTkLabel(
            error_dialog,
            text=error_text,
            wraplength=350
        )
        error_message.pack(pady=10)
        
        close_button = ctk.CTkButton(
            error_dialog,
            text="Close",
            command=error_dialog.destroy
        )
        close_button.pack(pady=20)

    def _on_daminion_connected(self, message):
        """Handle Daminion connection message."""
        item_count = message.get('item_count', 0)
        self.status_label.configure(text=f"✅ Connected to Daminion: {item_count} items")
        logging.info(f"Daminion connected: {item_count} items available")

    def _on_processing_done(self, message):
        """Handle processing completion message."""
        total_time = time.time() - self.processing_start_time
        processed_count = message.get('processed_count', 0)
        error_count = message.get('error_count', 0)
        
        # Reset UI state
        self.start_button.configure(text="Start Processing", command=self.on_start_processing)
        self.stop_event.clear()
        self.processing_start_time = None
        
        # Show completion message
        completion_dialog = ctk.CTkToplevel(self)
        completion_dialog.title("Processing Complete")
        completion_dialog.geometry("500x300")
        completion_dialog.transient(self)
        completion_dialog.grab_set()
        
        title_label = ctk.CTkLabel(
            completion_dialog,
            text="🎉 Processing Complete!",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=20)
        
        stats_text = f"""📊 Processing Summary:
        
• Total images processed: {processed_count}
• Errors encountered: {error_count}
• Total time: {total_time:.1f} seconds
• Average: {total_time/max(processed_count, 1):.2f} seconds per image"""
        
        stats_label = ctk.CTkLabel(
            completion_dialog,
            text=stats_text,
            justify="left"
        )
        stats_label.pack(pady=10)
        
        close_button = ctk.CTkButton(
            completion_dialog,
            text="Close",
            command=completion_dialog.destroy
        )
        close_button.pack(pady=20)

    def on_closing(self):
        """Handle application closing."""
        if self.daminion_client:
            self.daminion_client.cleanup_temp_files()
        self.destroy()

    def destroy(self):
        """Custom cleanup on application close."""
        # Stop any running processing
        self.stop_event.set()
        
        # Clean up Daminion client
        if self.daminion_client:
            self.daminion_client.cleanup_temp_files()
        
        super().destroy()


# Entry point for the modern GUI
def main():
    """Main entry point for modern GUI."""
    app = ModernImageTaggerGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()