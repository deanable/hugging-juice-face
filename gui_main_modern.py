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

# Import enhanced progress tracking
from enhanced_progress_display import create_enhanced_progress_display, setup_enhanced_progress_monitoring
from enhanced_progress import get_progress_tracker, ProgressStage, set_progress_stage

# Import Settings Manager
from settings_manager import SettingsManager
import huggingface_utils


class QueueHandler(logging.Handler):
    """
    Thread-safe logging handler that pushes messages to a queue.
    The GUI main thread will poll this queue and update the text widget.
    """
    def __init__(self, log_queue):
        logging.Handler.__init__(self)
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)



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
        self.log_queue = queue.Queue()  # Separate queue for logs
        self.model = None
        self._dl_start_time = None
        self._dl_total_bytes = None
        self._dl_last_bytes = 0
        self._dl_last_time = None
        self.image_dir = None
        self.stop_event = threading.Event()
        self.config_manager = ConfigManager()
        self.settings_manager = SettingsManager() # Initialize persistence
        self.progress_tracker = ProgressTracker()
        self.daminion_client: Optional[DaminionClient] = None
        self.processing_mode = "local"
        self.report = ProcessingReport()
        self.processing_start_time = None

        self.all_models = set()
        self.downloaded_models = set()
        self.all_models_with_tasks = {}  # Dict mapping task -> set of model IDs
        
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
        self.selected_model_var: Optional[ctk.StringVar] = None
        
        # Theme toggle button
        self.theme_button: Optional[ctk.CTkButton] = None
        
        # New Config Widgets
        self.device_var: Optional[ctk.StringVar] = None
        self.device_selector: Optional[ctk.CTkSegmentedButton] = None
        self.batch_size_slider: Optional[ctk.CTkSlider] = None
        self.batch_size_label: Optional[ctk.CTkLabel] = None
        self.truncation_var: Optional[ctk.BooleanVar] = None
        self.truncation_check: Optional[ctk.CTkCheckBox] = None
        self.threshold_slider: Optional[ctk.CTkSlider] = None
        
        # New Log Widget
        self.log_box: Optional[ctk.CTkTextbox] = None
        self.log_handler: Optional[QueueHandler] = None

        self._create_widgets()
        self._create_menu()
        gui_handlers.update_step_states(self)

        # Set initial Step 3 visibility based on default task
        try:
            gui_handlers.update_step3_visibility(self)
        except Exception as e:
            logging.warning(f"Could not set initial Step 3 visibility: {e}")

        try:
            gui_handlers.on_scope_change(self)
        except Exception:
            pass

        self.after(100, self.process_queue)
        self.after(100, self.process_log_queue)  # Start log processing loop
        self.after(200, self.scan_local_models)  # Scan for local models on startup
        
        # Setup logging handler for UI
        if self.log_box:
            self.log_handler = QueueHandler(self.log_queue)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
            self.log_handler.setFormatter(formatter)
            logging.getLogger().addHandler(self.log_handler)
            logging.info("GUI Logging initialized.")
            
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

        # Enhanced Progress section at bottom
        self.enhanced_progress_display = create_enhanced_progress_display(main_container)
        self.enhanced_progress_display.pack(fill="x", pady=(0, 20))
        
        # Setup enhanced progress monitoring
        setup_enhanced_progress_monitoring(self, self.enhanced_progress_display)
        
        # Add legacy progress section to ensure status_label and other widgets exist
        gui_steps.create_progress_section(main_container, self)
        
        # Hide legacy progress widgets that are duplicated by enhanced progress display
        if self.progress_bar:
            self.progress_bar.pack_forget()
        if self.progress_label:
            self.progress_label.pack_forget()
        if self.time_label:
            self.time_label.pack_forget()

    def _toggle_theme(self):
        """Toggle between light and dark mode."""
        current_mode = ctk.get_appearance_mode()
        if self.theme_button is None:
            return
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

    def on_inference_mode_change(self, mode_value=None):
        gui_handlers.on_inference_mode_change(self, mode_value)

    def on_test_api_connection(self):
        gui_handlers.on_test_api_connection(self)

    def on_scope_change(self, event=None):
        gui_handlers.on_scope_change(self, event)

    def on_daminion_connect(self):
        gui_handlers.on_daminion_connect(self)

    def on_find_models(self):
        gui_handlers.on_find_models(self)

    def on_set_hf_token(self):
        gui_handlers.set_hf_token(self)

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
        """Scan for locally cached models across all supported tasks (Async)."""
        try:
            logging.info("Starting async background scan for local models...")
            # We don't want to block startup, so we launch a thread.
            thread = threading.Thread(
                target=gui_workers.find_local_models_worker,
                args=(self,),
                daemon=True
            )
            thread.start()
            
        except Exception as e:
            logging.error(f"Error starting local model scan: {e}")

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

    def process_log_queue(self):
        """Process log messages from the log queue in batches."""
        try:
            messages = []
            while True:
                try:
                    msg = self.log_queue.get_nowait()
                    messages.append(msg)
                    # Limit batch size to prevent freezing if queue is huge
                    if len(messages) >= 100:
                        break
                except queue.Empty:
                    break
            
            if messages and self.log_box:
                batch_msg = "\n".join(messages) + "\n"
                try:
                    self.log_box.configure(state='normal')
                    self.log_box.insert("end", batch_msg)
                    self.log_box.see("end")
                    self.log_box.configure(state='disabled')
                except Exception as e:
                    # Fallback print if widget fails
                    print(f"Log widget error: {e}")
                    
        except Exception as e:
            print(f"Log processing error: {e}")
        finally:
            # Check again soon
            self.after(100, self.process_log_queue)

    def _normalize_message(self, message):
        """Normalize message to standard format (type, data).

        Args:
            message: Message from worker thread (dict, tuple, or other)

        Returns:
            Tuple of (message_type, data_dict)
        """
        if isinstance(message, dict):
            message_type = message.get('type', 'unknown')
            data = message
        elif isinstance(message, tuple) and len(message) == 2:
            message_type, data = message
        else:
            logging.warning(f"Unknown message format: {type(message)}")
            return 'unknown', {}

        return message_type, data

    def _normalize_model_loaded_data(self, data):
        """Normalize model_loaded message data."""
        if isinstance(data, dict) and 'model' in data:
            return data

        model_name = 'Unknown'
        if not isinstance(data, dict) and hasattr(data, 'model'):
            model_name = getattr(data.model, 'name_or_path', 'Unknown Model')

        return {'model': data, 'model_name': model_name}

    def _normalize_download_progress_data(self, data):
        """Normalize model_download_progress message data."""
        if isinstance(data, dict):
            return data

        current, total = data
        return {
            'progress': (current / total) if total else 0,
            'bytes_downloaded': current,
            'total_bytes': total,
            'status': "Downloading..."
        }

    def _handle_message(self, message):
        """Handle messages from worker threads."""
        message_type, data = self._normalize_message(message)

        # Message handler dispatch table
        handlers = {
            'model_loaded': lambda d: self._on_model_loaded(self._normalize_model_loaded_data(d)),
            'model_download_progress': lambda d: self._on_model_download_progress(self._normalize_download_progress_data(d)),
            'progress': lambda d: self._on_progress_update(d if isinstance(d, dict) else {'progress': 0, 'current': d, 'total': 0}),
            'progress_max': self._handle_progress_max,
            'status_update': lambda d: self._on_status_update(d if isinstance(d, dict) else {'status': d}),
            'error': lambda d: self._on_error(d if isinstance(d, dict) else {'error': str(d)}),
            'daminion_error': self._on_daminion_error,
            'daminion_connected': lambda d: self._on_daminion_connected(d if isinstance(d, dict) and 'item_count' in d else {'item_count': d.get('total_items', 0) if isinstance(d, dict) else 0}),
            'daminion_collections': self._on_daminion_collections,
            'models_found': self._on_models_found,
            'progress_done': lambda d: self._on_processing_done(d if isinstance(d, dict) else {'processed_count': 0, 'error_count': 0}),
            'api_test_result': self._on_api_test_result
        }

        handler = handlers.get(message_type)
        if handler:
            handler(data)
        else:
            logging.warning(f"Unknown message type: {message_type}")

    def _on_api_test_result(self, data):
        """Handle API test result message."""
        success = data.get('success', False)
        msg = data.get('msg', 'Unknown result')
        
        if self.test_api_button:
            self.test_api_button.configure(state="normal", text="📡 Test API Connection")
            
        if success:
            if self.api_status_label:
                self.api_status_label.configure(text="✅ Connection Valid", text_color="green")
            gui_handlers.show_modern_messagebox(self, "Success", f"API Connection Successful!\n\n{msg}", "success")
        else:
            if self.api_status_label:
                self.api_status_label.configure(text="❌ Connection Failed", text_color="red")
            gui_handlers.show_modern_messagebox(self, "Connection Failed", f"Could not connect to HF API:\n{msg}", "error")

    def _handle_progress_max(self, data):
        """Handle progress_max message."""
        tracker = get_progress_tracker()
        if isinstance(data, dict):
            val = data.get('total', data.get('value', 0))
        else:
            val = data
        tracker.total_items = int(val) if val else 0

    def _on_daminion_error(self, message):
        """Handle Daminion connection error message methods."""
        error_msg = message.get('error', 'Unknown Daminion Error')
        logging.error(f"Daminion Connection Error: {error_msg}")
        
        if self.daminion_status_label:
            self.daminion_status_label.configure(text="❌ Connection Failed", text_color="red")
            
        gui_handlers.show_modern_messagebox(self, "Connection Error", f"Failed to connect to Daminion:\n{error_msg}", "error")

    def _on_model_loaded(self, message):
        """Handle model loaded message."""
        self.model = message['model']
        if self.status_label:
            self.status_label.configure(text=f"✅ Model loaded: {message['model_name']}")
        
        # Reset load button state so user can switch models if desired
        if self.load_model_button:
            self.load_model_button.configure(
                text="📥 Load Selected Model",
                state="normal"
            )
            
        logging.info(f"Model loaded successfully: {message['model_name']}")
        
        # Log supported labels (requested by user)
        try:
            # Pipeline -> Model -> Config
            if hasattr(self.model, 'model') and hasattr(self.model.model, 'config'):
                config = self.model.model.config
                if hasattr(config, 'id2label') and config.id2label:
                    labels = list(config.id2label.values())
                    logging.info(f"Model supports {len(labels)} labels. First 50: {labels[:50]}")
                    if len(labels) > 50:
                        logging.info(f"... and {len(labels)-50} more.")
        except Exception as e:
            logging.debug(f"Could not extract label list from model: {e}")

        gui_handlers.update_step_states(self)

    def _on_model_download_progress(self, message):
        """Handle model download progress with enhanced tracking."""
        progress = message.get('progress', 0.0)
        status = message.get('status', '')
        bytes_downloaded = message.get('bytes_downloaded', 0)
        total_bytes = message.get('total_bytes', 0)
        current_file = message.get('current_file', '')
        
        # Update enhanced progress tracker
        tracker = get_progress_tracker()
        tracker.update_download_progress(bytes_downloaded, total_bytes, current_file)
        
        # Update legacy UI elements if they exist
        if self.model_progress_bar:
            self.model_progress_bar.set(progress)
        if self.model_progress_label and status:
            self.model_progress_label.configure(text=status)

    def _on_progress_update(self, message):
        """Handle progress update message with enhanced tracking."""
        progress = message.get('progress', 0.0)
        current = message.get('current', 0)
        total = message.get('total', 0)
        processed = message.get('processed', [])
        current_image = message.get('current_image', '')
        sub_stage = message.get('sub_stage', '')
        sub_stage_progress = message.get('sub_stage_progress', 0.0)
        
        # Update enhanced progress tracker
        tracker = get_progress_tracker()
        tracker.update_processing_progress(current, sub_stage, sub_stage_progress)
        
        if total == 0 and tracker.total_items > 0:
            total = tracker.total_items
            
        # Update legacy UI elements if they exist
        if self.progress_bar:
            self.progress_bar.set(progress)
        
        status_text = f"Processing: {current}/{total} images"
        if current_image:
            status_text += f" | {current_image}"
        
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
        """Handle status update message with enhanced stage tracking."""
        status_text = message.get('status', '')
        
        # Update enhanced progress tracker with stage information
        if status_text:
            if "downloading" in status_text.lower():
                set_progress_stage(ProgressStage.DOWNLOADING_MODEL, sub_stage=status_text)
            elif "connecting" in status_text.lower():
                set_progress_stage(ProgressStage.CONNECTING, sub_stage=status_text)
            elif "loading model" in status_text.lower():
                set_progress_stage(ProgressStage.LOADING_MODEL, sub_stage=status_text)
            elif "processing" in status_text.lower():
                set_progress_stage(ProgressStage.PROCESSING_IMAGES, sub_stage=status_text)
            elif "analyzing" in status_text.lower():
                set_progress_stage(ProgressStage.ANALYZING_IMAGE, sub_stage=status_text)
            elif "updating metadata" in status_text.lower():
                set_progress_stage(ProgressStage.UPDATING_METADATA, sub_stage=status_text)
        
        if self.status_label:
            self.status_label.configure(text=f"ℹ️ {status_text}")
        logging.info(f"Status: {status_text}")

    def _on_error(self, message):
        """Handle error message."""
        error_text = message.get('error', 'Unknown error')
        logging.error(f"Processing error: {error_text}")

        # Reset UI element states if error occurred during processing/loading
        if self.start_button:
            self.start_button.configure(
                text="🚀 Start Processing",
                state="normal",
                fg_color="green"
            )
        if self.stop_button:
            self.stop_button.configure(state="disabled", fg_color="red")
            
        if self.load_model_button:
            self.load_model_button.configure(
                text="📥 Load Selected Model",
                state="normal"
            )

        if self.refresh_collections_btn:
            self.refresh_collections_btn.configure(state="normal", text="🔄 Refresh")
        
        gui_handlers.show_modern_messagebox(self, "Error Occurred", error_text, "error")

    def _on_daminion_connected(self, message):
        """Handle Daminion connection message."""
        item_count = message.get('item_count', 0)
        if self.daminion_status_label:
             self.daminion_status_label.configure(text="✅ Connected!", text_color="green")
             
        if self.status_label:
            self.status_label.configure(text=f"✅ Connected to Daminion: {item_count} items")
            
        logging.info(f"Daminion connected: {item_count} items available")
        gui_handlers.update_step_states(self)

    def _on_daminion_collections(self, collections):
        """Handle Daminion collections update."""
        self.daminion_collections = collections
        if self.daminion_collection_combo:
            names = []
            for c in collections:
                if isinstance(c, dict):
                    title = c.get('name') or c.get('title') or c.get('code') or str(c.get('id') or '')
                    idx = c.get('id') or c.get('code') or c.get('collectionId') or ''
                    names.append(f"{title} ({idx})" if idx else title)
            
            self.daminion_collection_combo.configure(values=names)
            if names:
                self.daminion_collection_combo.set(names[0])
            
        if self.refresh_collections_btn:
            self.refresh_collections_btn.configure(state="normal", text="🔄 Refresh")

    def _on_models_found(self, data):
        """Handle models found message.

        Stores models organized by task type for efficient filtering.
        """
        # Robust unpacking
        model_ids = []
        downloaded = []
        
        if isinstance(data, (tuple, list)) and len(data) >= 2:
            model_ids, downloaded = data[0], data[1]
        elif isinstance(data, dict):
            # Handle dictionary format (e.g. from gui_workers.py)
            # data = {'type': 'models_found', 'models': (ids, down)}
            payload = data.get('models')
            if isinstance(payload, (tuple, list)) and len(payload) >= 2:
                model_ids, downloaded = payload[0], payload[1]
            else:
                # Fallback purely for backward compatibility or direct list usage
                model_ids = data.get('models', [])
                downloaded = data.get('downloaded', [])
        else:
            logging.error(f"Invalid models_found data format: {type(data)}")
            return

        current_task = self.model_task.get() if self.model_task else config.MODEL_TASK_IMAGE_CLASSIFICATION
        if current_task not in self.all_models_with_tasks:
            self.all_models_with_tasks[current_task] = set()
        # Update set with robust error handling
        if model_ids:
            # Flatten or filter if needed? No, likely model_ids is list of strings
            # But just in case any item is unhashable, use a safeguard
            valid_ids = []
            for m_id in model_ids:
                if isinstance(m_id, str):
                    valid_ids.append(m_id)
                else:
                    logging.warning(f"Skipping unhashable model_id of type {type(m_id)}: {m_id}")
            
            self.all_models_with_tasks[current_task].update(valid_ids)

        # Use the centralized update function
        gui_handlers.update_model_list(self, list(model_ids), downloaded)

        if self.find_models_button:
            self.find_models_button.configure(state="normal", text="🔍 Find Models")

        cached_count = len([m for m in model_ids if m in downloaded])
        cloud_count = len(model_ids) - cached_count

        if self.status_label:
            self.status_label.configure(
                text=f"Found {len(model_ids)} models for {current_task} ({cached_count} cached, {cloud_count} cloud)"
            )

    def _on_processing_done(self, message):
        """Handle processing completion message."""
        start_time = self.processing_start_time or time.time()
        total_time = time.time() - start_time
        processed_count = message.get('processed_count', 0)
        error_count = message.get('error_count', 0)
        
        # Reset UI state
        if self.start_button:
            self.start_button.configure(text="Start Processing", command=self.on_start_processing)
            self.stop_button.configure(state="disabled", fg_color="red")
            gui_handlers.toggle_input_state(self, "normal")
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
        try:
             # Save Settings
             if self.settings_manager:
                 self.settings_manager.update_from_gui(self)
        except Exception as e:
             logging.error(f"Failed to save settings on close: {e}")

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