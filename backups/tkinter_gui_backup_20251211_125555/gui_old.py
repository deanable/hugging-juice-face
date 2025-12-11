"""
Main GUI for the Advanced Image Tagger application.
Redesigned with intuitive step-by-step workflow.
"""

import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
import huggingface_utils
import image_processing
from config_manager import ConfigManager
from progress_tracker import ProgressTracker
from daminion_client import DaminionClient, DaminionAPIError
from report_generator import ProcessingReport
import time


def filter_local_images(all_images, scope: str, collection_path: Path | None = None):
    """Return a filtered list of local image Path objects according to scope.

    scope: 'collection' | 'flagged' | 'untagged' (untagged -> returns all_images unchanged)
    collection_path: Path object pointing to a sub-folder when scope == 'collection'
    """
    if scope == 'collection':
        if collection_path is None:
            return []
        return [p for p in all_images if collection_path in p.parents or str(p).startswith(str(collection_path))]

    if scope == 'flagged':
        def is_flagged(p: Path) -> bool:
            name = p.name.lower()
            if 'flag' in name or 'reject' in name or 'rejected' in name:
                return True
            for part in p.parents:
                pn = part.name.lower()
                if 'flag' in pn or 'reject' in pn or 'rejected' in pn:
                    return True
            return False

        return [p for p in all_images if is_flagged(p)]

    # default or 'untagged' -> return everything; the resume/unprocessed behavior is handled elsewhere
    return list(all_images)


def filter_daminion_items(items, scope: str, collection_name: str | None = None):
    """Return a filtered list of Daminion item dicts according to scope.

    items: list of dicts from Daminion API
    scope: 'collection' | 'flagged' | 'untagged' (untagged -> return items unchanged)
    collection_name: substring to match when scope == 'collection'
    """
    if scope == 'collection':
        if not collection_name:
            return []
        cn = collection_name.lower()
        return [it for it in items if cn in (it.get('fileName') or '').lower() or cn in str(it.get('id', '')).lower()]

    if scope == 'flagged':
        def is_flagged_item(it: dict) -> bool:
            fname = (it.get('fileName') or '').lower()
            if any(tok in fname for tok in ['flag', 'reject', 'rejected']):
                return True
            for k in ('status', 'tags', 'keywords', 'description'):
                v = it.get(k)
                if isinstance(v, str) and any(tok in v.lower() for tok in ['flag', 'reject', 'rejected']):
                    return True
                if isinstance(v, list) and any(isinstance(x, str) and any(tok in x.lower() for tok in ['flag', 'reject', 'rejected']) for x in v):
                    return True
            return False

        return [it for it in items if is_flagged_item(it)]

    return list(items)

class ImageTaggerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(config.APP_NAME)
        self.geometry("900x800")

        self.q = queue.Queue()
        self.model = None
        # Download progress tracking
        self._dl_start_time = None
        self._dl_total_bytes = None
        self._dl_last_bytes = 0
        self._dl_last_time = None
        self.image_dir = None
        self.stop_event = threading.Event()
        self.config_manager = ConfigManager()
        self.progress_tracker = ProgressTracker()
        self.daminion_client = None
        self.processing_mode = "local"
        self.report = ProcessingReport()
        self.processing_start_time = None

        self._create_widgets()
        self._create_menu()
        self._update_step_states()
        # ensure scope-related controls update to the new mode (local vs daminion)
        try:
            self.on_scope_change()
        except Exception:
            pass

        self.after(100, self.process_queue)
        logging.info("GUI initialized with step-by-step workflow.")

    def _create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        cache_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Cache", menu=cache_menu)
        cache_menu.add_command(label="View Cache Path", command=self.show_cache_path)
        cache_menu.add_command(label="Clear Model Cache", command=self.clear_cache)

        report_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Reports", menu=report_menu)
        report_menu.add_command(label="Export Report (CSV)", command=self.export_report_csv)
        report_menu.add_command(label="Export Report (JSON)", command=self.export_report_json)
        report_menu.add_command(label="View Report Summary", command=self.show_report_summary)

    # Small reusable collapsible container to reduce UI overflow on small screens
    class CollapsiblePane(ttk.Frame):
        def __init__(self, parent, title="", *args, **kwargs):
            super().__init__(parent)
            self.title = title
            header = ttk.Frame(self)
            header.pack(fill="x")
            self._btn = ttk.Button(header, text=f"▾ {self.title}", width=40, command=self._toggle)
            self._btn.pack(side="left", anchor="w")
            # content frame where callers can pack their widgets
            self.content = ttk.Frame(self)
            self.content.pack(fill="both", expand=True)

        def _toggle(self):
            if self.content.winfo_ismapped():
                self.content.pack_forget()
                self._btn.config(text=f"▸ {self.title}")
            else:
                self.content.pack(fill="both", expand=True)
                self._btn.config(text=f"▾ {self.title}")

    def _create_widgets(self):
        # Main container with padding
        main_container = ttk.Frame(self, padding="10")
        main_container.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(main_container, text="AI-Powered Image Tagger",
                                font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))

        subtitle_label = ttk.Label(main_container,
                                   text="Follow the steps below to tag your images with AI",
                                   font=("Arial", 10))
        subtitle_label.pack(pady=(0, 20))

        # Collapsible panes for each step
        self.step1_pane = self.CollapsiblePane(main_container, title="Step 1: Choose Image Source")
        self.step1_pane.pack(fill="x", pady=(0, 10))
        self._create_step1_source(self.step1_pane.content)

        self.step2_pane = self.CollapsiblePane(main_container, title="Step 2: Select AI Model")
        self.step2_pane.pack(fill="x", pady=(0, 10))
        self._create_step2_model(self.step2_pane.content)

        self.step3_pane = self.CollapsiblePane(main_container, title="Step 3: Configure Tagging")
        self.step3_pane.pack(fill="x", pady=(0, 10))
        self._create_step3_config(self.step3_pane.content)

        self.step4_pane = self.CollapsiblePane(main_container, title="Step 4: Process Images")
        self.step4_pane.pack(fill="x", pady=(0, 10))
        self._create_step4_process(self.step4_pane.content)

        # Progress Section (not collapsible)
        self._create_progress_section(main_container)

    def _create_step1_source(self, parent):
        """Step 1: Choose your image source"""
        frame = ttk.LabelFrame(parent, text="⓵ Choose Image Source", padding="15")
        frame.pack(fill="x", pady=(0, 15))

        # Mode selection
        mode_frame = ttk.Frame(frame)
        mode_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(mode_frame, text="Select where your images are:",
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))

        self.mode_var = tk.StringVar(value="local")

        radio_frame = ttk.Frame(mode_frame)
        radio_frame.pack(fill="x")

        self.local_radio = ttk.Radiobutton(radio_frame, text="📁 Local Files (from your computer)",
                                          variable=self.mode_var, value="local",
                                          command=self.on_mode_change)
        self.local_radio.pack(anchor="w", padx=20)

        self.daminion_radio = ttk.Radiobutton(radio_frame, text="☁️  Daminion DAMS (from cloud server)",
                                             variable=self.mode_var, value="daminion",
                                             command=self.on_mode_change)
        self.daminion_radio.pack(anchor="w", padx=20, pady=(5, 0))

        # Local files section
        self.local_section = ttk.Frame(frame)
        self.local_section.pack(fill="x", pady=(10, 0))

        ttk.Label(self.local_section, text="Image Directory:",
                 font=("Arial", 9)).pack(anchor="w")

        dir_frame = ttk.Frame(self.local_section)
        dir_frame.pack(fill="x", pady=(5, 0))

        self.select_dir_button = ttk.Button(dir_frame, text="Browse...",
                                           command=self.select_directory, width=15)
        self.select_dir_button.pack(side="left")

        self.dir_label = ttk.Label(dir_frame, text="No directory selected",
                                   foreground="gray")
        self.dir_label.pack(side="left", padx=(10, 0))

        # Daminion section (hidden by default)
        self.daminion_section = ttk.Frame(frame)

        ttk.Label(self.daminion_section, text="Daminion Server Connection:",
                 font=("Arial", 9)).pack(anchor="w")

        conn_grid = ttk.Frame(self.daminion_section)
        conn_grid.pack(fill="x", pady=(5, 0))

        ttk.Label(conn_grid, text="Server URL:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.daminion_url_entry = ttk.Entry(conn_grid, width=40)
        self.daminion_url_entry.grid(row=0, column=1, sticky="ew", pady=2)
        self.daminion_url_entry.insert(0, str(self.config_manager.get('daminion_url',
                                                                  'https://interiors.daminion.net')))

        ttk.Label(conn_grid, text="Username:").grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.daminion_username_entry = ttk.Entry(conn_grid, width=40)
        self.daminion_username_entry.grid(row=1, column=1, sticky="ew", pady=2)
        self.daminion_username_entry.insert(0, str(self.config_manager.get('daminion_username', '')))

        ttk.Label(conn_grid, text="Password:").grid(row=2, column=0, sticky="w", padx=(0, 10))
        self.daminion_password_entry = ttk.Entry(conn_grid, width=40, show="*")
        self.daminion_password_entry.grid(row=2, column=1, sticky="ew", pady=2)

        conn_grid.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(self.daminion_section)
        btn_frame.pack(fill="x", pady=(10, 0))

        self.daminion_connect_button = ttk.Button(btn_frame, text="Connect to Daminion",
                                                 command=self.connect_daminion)
        self.daminion_connect_button.pack(side="left")

        self.daminion_status_label = ttk.Label(btn_frame, text="● Not connected",
                                              foreground="gray")
        self.daminion_status_label.pack(side="left", padx=(15, 0))

        # Status indicator for Step 1
        self.step1_status = ttk.Label(frame, text="", foreground="gray")
        self.step1_status.pack(anchor="w", pady=(10, 0))

    def _create_step2_model(self, parent):
        """Step 2: Select and load AI model"""
        frame = ttk.LabelFrame(parent, text="⓶ Select AI Model", padding="15")
        frame.pack(fill="x", pady=(0, 15))

        ttk.Label(frame, text="Choose the type of AI analysis:",
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))

        # Model task selection
        task_frame = ttk.Frame(frame)
        task_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(task_frame, text="Analysis Type:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.model_task = ttk.Combobox(task_frame, values=[
            config.MODEL_TASK_IMAGE_CLASSIFICATION,
            config.MODEL_TASK_ZERO_SHOT,
            config.MODEL_TASK_IMAGE_TO_TEXT
        ], state="readonly", width=40)
        self.model_task.grid(row=0, column=1, sticky="ew")

        last_task = self.config_manager.get('last_model_task', config.MODEL_TASK_IMAGE_CLASSIFICATION)
        task_index = [config.MODEL_TASK_IMAGE_CLASSIFICATION, config.MODEL_TASK_ZERO_SHOT,
                      config.MODEL_TASK_IMAGE_TO_TEXT].index(last_task) if last_task in [
            config.MODEL_TASK_IMAGE_CLASSIFICATION, config.MODEL_TASK_ZERO_SHOT,
            config.MODEL_TASK_IMAGE_TO_TEXT] else 0
        self.model_task.current(task_index)
        self.model_task.bind("<<ComboboxSelected>>", self.on_model_task_change)

        task_frame.columnconfigure(1, weight=1)

        # Task description
        self.task_description = ttk.Label(frame, text="", foreground="gray", wraplength=800)
        self.task_description.pack(anchor="w", pady=(5, 15))
        self.update_task_description()

        # Find models button
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill="x", pady=(0, 10))

        self.find_models_button = ttk.Button(search_frame,
                                            text="🔍 Search for Models on Hugging Face",
                                            command=self.find_models, width=35)
        self.find_models_button.pack(side="left")

        # Model list
        ttk.Label(frame, text="Available Models:", font=("Arial", 9)).pack(anchor="w", pady=(0, 5))

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 10))

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.model_listbox = tk.Listbox(list_frame, height=6, yscrollcommand=scrollbar.set)
        self.model_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.model_listbox.yview)
        self.model_listbox.bind("<<ListboxSelect>>", self.show_model_info)

        # Model info
        ttk.Label(frame, text="Model Information:", font=("Arial", 9)).pack(anchor="w", pady=(0, 5))

        info_frame = ttk.Frame(frame)
        info_frame.pack(fill="both", expand=True, pady=(0, 10))

        info_scrollbar = ttk.Scrollbar(info_frame)
        info_scrollbar.pack(side="right", fill="y")

        self.model_info_text = tk.Text(info_frame, height=6, wrap="word",
                                       yscrollcommand=info_scrollbar.set)
        self.model_info_text.pack(side="left", fill="both", expand=True)
        info_scrollbar.config(command=self.model_info_text.yview)

        # Load model button and progress
        load_frame = ttk.Frame(frame)
        load_frame.pack(fill="x", pady=(0, 5))

        self.load_model_button = ttk.Button(load_frame, text="⬇️  Download & Load Selected Model",
                                           command=self.load_model, width=35)
        self.load_model_button.pack(side="left")

        self.model_progress_bar = ttk.Progressbar(load_frame, orient="horizontal",
                                                 length=200, mode="determinate")
        self.model_progress_bar.pack(side="left", padx=(15, 0), fill="x", expand=True)

        # Small status label showing MB, percent and ETA for downloads
        self.model_progress_label = ttk.Label(load_frame, text="", foreground="gray", font=("Arial", 8))
        self.model_progress_label.pack(side="left", padx=(10,0))

        # Status indicator for Step 2
        self.step2_status = ttk.Label(frame, text="", foreground="gray")
        self.step2_status.pack(anchor="w")

    def _create_step3_config(self, parent):
        """Step 3: Configure tagging options"""
        frame = ttk.LabelFrame(parent, text="⓷ Configure Tagging", padding="15")
        frame.pack(fill="x", pady=(0, 15))

        ttk.Label(frame, text="Specify the categories or keywords for tagging:",
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 10))

        # Categories
        cat_frame = ttk.Frame(frame)
        cat_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(cat_frame, text="Categories:", font=("Arial", 9)).grid(row=0, column=0,
                                                                         sticky="nw", padx=(0, 10), pady=5)
        ttk.Label(cat_frame, text="(for Image Classification)",
                 foreground="gray", font=("Arial", 8)).grid(row=1, column=0, sticky="nw", padx=(0, 10))

        self.categories_entry = ttk.Entry(cat_frame, width=60)
        self.categories_entry.grid(row=0, column=1, rowspan=2, sticky="ew", pady=5)
        # Ensure the default value is a string, even if config_manager returns None
        default_categories = str(self.config_manager.get('default_categories', 'Interior, Exterior, Furniture, Decor'))
        self.categories_entry.insert(0, default_categories)

        cat_frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Examples: Interior, Exterior, Furniture, Portrait, Landscape",
                 foreground="gray", font=("Arial", 8)).pack(anchor="w", padx=(100, 0))

        # Keywords
        kw_frame = ttk.Frame(frame)
        kw_frame.pack(fill="x", pady=(15, 10))

        ttk.Label(kw_frame, text="Keywords:", font=("Arial", 9)).grid(row=0, column=0,
                                                                      sticky="nw", padx=(0, 10), pady=5)
        ttk.Label(kw_frame, text="(for Zero-Shot Classification)",
                 foreground="gray", font=("Arial", 8)).grid(row=1, column=0, sticky="nw", padx=(0, 10))

        self.keywords_entry = ttk.Entry(kw_frame, width=60)
        self.keywords_entry.grid(row=0, column=1, rowspan=2, sticky="ew", pady=5)
        self.keywords_entry.insert(0, self.config_manager.get('default_keywords',
                                                              'bedroom, kitchen, sofa, chair, modern, vintage'))

        kw_frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Examples: bedroom, kitchen, sofa, modern, vintage, sunset, portrait",
                 foreground="gray", font=("Arial", 8)).pack(anchor="w", padx=(100, 0))

        # Note about Image-to-Text
        note_frame = ttk.Frame(frame)
        note_frame.pack(fill="x", pady=(15, 0))

        ttk.Label(note_frame, text="ℹ️", font=("Arial", 12)).pack(side="left")
        ttk.Label(note_frame,
                 text="For Image-to-Text, categories and keywords are not required (auto-generated)",
                 foreground="gray", font=("Arial", 8), wraplength=750).pack(side="left", padx=(5, 0))

        # Status indicator for Step 3
        self.step3_status = ttk.Label(frame, text="", foreground="gray")
        self.step3_status.pack(anchor="w", pady=(10, 0))

    def _create_step4_process(self, parent):
        """Step 4: Start processing"""
        frame = ttk.LabelFrame(parent, text="⓸ Process Images", padding="15")
        frame.pack(fill="x", pady=(0, 15))

        ttk.Label(frame, text="Ready to tag your images with AI!",
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 10))

        # Processing scope (collection / flagged / untagged)
        scope_frame = ttk.Frame(frame)
        scope_frame.pack(fill="x", pady=(10, 5))

        ttk.Label(scope_frame, text="Process scope:", font=("Arial", 9, "bold")).pack(anchor="w")

        self.scope_var = tk.StringVar(value="untagged")

        rb_frame = ttk.Frame(scope_frame)
        rb_frame.pack(fill="x", padx=(20, 0))

        self.scope_collection_rb = ttk.Radiobutton(rb_frame, text="A collection",
                               variable=self.scope_var, value="collection",
                               command=self.on_scope_change)
        self.scope_collection_rb.pack(anchor="w")

        self.scope_flagged_rb = ttk.Radiobutton(rb_frame, text="Flagged / Rejected images",
                            variable=self.scope_var, value="flagged",
                            command=self.on_scope_change)
        self.scope_flagged_rb.pack(anchor="w", pady=(5, 0))

        self.scope_untagged_rb = ttk.Radiobutton(rb_frame, text="All untagged images",
                             variable=self.scope_var, value="untagged",
                             command=self.on_scope_change)
        self.scope_untagged_rb.pack(anchor="w", pady=(5, 0))

        # Extra controls shown when scope==collection
        self.collection_selector_frame = ttk.Frame(scope_frame)
        self.collection_selector_frame.pack(fill="x", pady=(5, 0))

        self.collection_path = None
        self.collection_path_label = ttk.Label(self.collection_selector_frame, text="No collection selected", foreground="gray")
        self.collection_path_label.pack(side="left", padx=(20, 0))

        self.select_collection_btn = ttk.Button(self.collection_selector_frame, text="Select Collection (sub-folder)",
                               command=self.select_collection)
        self.select_collection_btn.pack(side="left", padx=(5, 10))

        # For Daminion, allow user to pick a shared-collection (populated after connecting)
        self.daminion_collections = []
        self.daminion_collection_combo = ttk.Combobox(self.collection_selector_frame, values=[], state='disabled', width=40)
        self.daminion_collection_combo.pack(side="left", padx=(5, 0))

        self.refresh_collections_btn = ttk.Button(self.collection_selector_frame, text="Refresh collections",
                              command=self.refresh_daminion_collections)
        self.refresh_collections_btn.pack(side="left", padx=(6, 0))

        # Start Button
        self.start_button = ttk.Button(frame, text="▶️  Start Processing Images",
                                       command=self.start_processing,
                                       state="disabled", width=30)
        self.start_button.pack(anchor="w")

        # Status indicator for Step 4
        self.step4_status = ttk.Label(frame, text="", foreground="gray")
        self.step4_status.pack(anchor="w", pady=(10, 0))

    def _create_progress_section(self, parent):
        """Progress tracking section"""
        frame = ttk.LabelFrame(parent, text="Progress", padding="15")
        frame.pack(fill="both", expand=True)

        self.status_label = ttk.Label(frame, text="Status: Ready to begin",
                                     font=("Arial", 9))
        self.status_label.pack(anchor="w", pady=(0, 10))

        self.progress_bar = ttk.Progressbar(frame, orient="horizontal",
                                           length=100, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(0, 5))

        progress_info_frame = ttk.Frame(frame)
        progress_info_frame.pack(fill="x")

        self.progress_label = ttk.Label(progress_info_frame, text="0 / 0 images processed",
                                       foreground="gray", font=("Arial", 8))
        self.progress_label.pack(side="left")

        self.time_label = ttk.Label(progress_info_frame, text="",
                                    foreground="gray", font=("Arial", 8))
        self.time_label.pack(side="right")

    def _update_step_states(self):
        """Update visual indicators for each step"""
        # Step 1: Source selected?
        if self.processing_mode == "local":
            if self.image_dir:
                self.step1_status.config(text="[OK] Source ready: Local directory selected",
                                        foreground="green")
            else:
                self.step1_status.config(text="[WARN] Please select an image directory",
                                        foreground="orange")
        else:
            if self.daminion_client:
                self.step1_status.config(text="[OK] Source ready: Connected to Daminion",
                                        foreground="green")
            else:
                self.step1_status.config(text="[WARN] Please connect to Daminion server",
                                        foreground="orange")

        # Step 2: Model loaded?
        if self.model:
            model_name = self.model.model.name_or_path
            self.step2_status.config(text=f"[OK] Model loaded: {model_name}",
                                    foreground="green")
        else:
            self.step2_status.config(text="[WARN] Please search for and load a model",
                                    foreground="orange")

        # Step 3: Configuration ready?
        task = self.model_task.get()
        cats = self.categories_entry.get().strip()
        kws = self.keywords_entry.get().strip()

        if task == config.MODEL_TASK_IMAGE_TO_TEXT:
            self.step3_status.config(text="[OK] Configuration ready: Image-to-Text mode (auto)",
                                    foreground="green")
        elif task == config.MODEL_TASK_IMAGE_CLASSIFICATION and cats:
            self.step3_status.config(text="[OK] Configuration ready: Categories entered",
                                    foreground="green")
        elif task == config.MODEL_TASK_ZERO_SHOT and kws:
            self.step3_status.config(text="[OK] Configuration ready: Keywords entered",
                                    foreground="green")
        else:
            self.step3_status.config(text="[WARN] Please enter categories or keywords",
                                    foreground="orange")

        # Step 4: Ready to process?
        source_ready = (self.processing_mode == "local" and self.image_dir) or \
                      (self.processing_mode == "daminion" and self.daminion_client)
        config_ready = (task == config.MODEL_TASK_IMAGE_TO_TEXT) or \
                      (task == config.MODEL_TASK_IMAGE_CLASSIFICATION and cats) or \
                      (task == config.MODEL_TASK_ZERO_SHOT and kws)

        if source_ready and self.model and config_ready:
            self.start_button.config(state="normal")
            self.step4_status.config(text="[OK] Ready to process!", foreground="green")
        else:
            self.start_button.config(state="disabled")
            missing = []
            if not source_ready:
                missing.append("image source")
            if not self.model:
                missing.append("AI model")
            if not config_ready:
                missing.append("configuration")
            self.step4_status.config(text=f"[WARN] Complete previous steps: {', '.join(missing)}",
                                    foreground="orange")

    def update_task_description(self):
        """Update the description based on selected task"""
        task = self.model_task.get()
        descriptions = {
            config.MODEL_TASK_IMAGE_CLASSIFICATION:
                "📋 Assigns ONE category to each image from your predefined list (e.g., Interior, Exterior, Furniture)",
            config.MODEL_TASK_ZERO_SHOT:
                "🏷️  Detects MULTIPLE keywords from your list with confidence >90% (e.g., bedroom, modern, sofa)",
            config.MODEL_TASK_IMAGE_TO_TEXT:
                "✍️  Automatically generates descriptions and extracts keywords (no configuration needed)"
        }
        self.task_description.config(text=descriptions.get(task, ""))

    def on_model_task_change(self, event=None):
        """Handle model task selection change"""
        self.update_task_description()
        self._update_step_states()
        logging.info(f"Model task changed to: {self.model_task.get()}")

    def on_mode_change(self):
        """Handle mode change between local and Daminion"""
        mode = self.mode_var.get()
        self.processing_mode = mode
        logging.info(f"Processing mode changed to: {mode}")

        if mode == "daminion":
            self.daminion_section.pack(fill="x", pady=(10, 0))
            self.local_section.pack_forget()
            self.dir_label.config(text="Daminion mode: Items will be fetched from DAMS")
        else:
            self.local_section.pack(fill="x", pady=(10, 0))
            self.daminion_section.pack_forget()
            if self.image_dir:
                self.dir_label.config(text=str(self.image_dir))
            else:
                self.dir_label.config(text="No directory selected")

        self._update_step_states()

    def on_scope_change(self):
        """Handle showing/hiding controls depending on the selected processing scope."""
        scope = self.scope_var.get()
        if scope == 'collection':
            # show collection selectors
            self.collection_selector_frame.pack(fill="x", pady=(5, 0))
            # default visibility: keep both local selection label and daminion entry visible but greyed
            if self.processing_mode == 'local':
                self.collection_path_label.config(foreground='black' if self.collection_path else 'gray')
                self.daminion_collection_combo.config(state='disabled')
                self.refresh_collections_btn.config(state='disabled')
            else:
                # daminion: enable entry
                self.collection_path_label.config(foreground='gray')
                self.daminion_collection_combo.config(state='readonly')
                self.refresh_collections_btn.config(state='normal')
        else:
            # hide additional controls
            self.collection_selector_frame.pack_forget()


    def select_directory(self):
        """Select local image directory"""
        directory = filedialog.askdirectory(title="Select Image Directory")
        if directory:
            self.image_dir = Path(directory)
            self.dir_label.config(text=str(self.image_dir), foreground="black")
            logging.info(f"Selected directory: {self.image_dir}")
            self._update_step_states()

    def select_collection(self):
        """Select a sub-folder within the currently chosen local image directory.

        This is used when the user picks 'A collection' as the processing scope.
        """
        if not self.image_dir:
            messagebox.showerror("Error", "Please select an image directory first (Step 1).")
            return

        directory = filedialog.askdirectory(title="Select Collection (sub-folder)", initialdir=str(self.image_dir))
        if directory:
            # ensure selection is inside image_dir
            try:
                sel = Path(directory).resolve()
                if str(sel).startswith(str(self.image_dir.resolve())):
                    self.collection_path = sel
                    self.collection_path_label.config(text=str(self.collection_path), foreground='black')
                else:
                    messagebox.showerror("Error", "Please select a sub-folder inside the chosen image directory.")
            except Exception:
                messagebox.showerror("Error", "Failed to select collection path.")

    def connect_daminion(self):
        """Connect to Daminion server"""
        url = self.daminion_url_entry.get().strip()
        username = self.daminion_username_entry.get().strip()
        password = self.daminion_password_entry.get()

        if not url or not username or not password:
            messagebox.showerror("Error", "Please fill in all Daminion connection fields.")
            return

        self.daminion_status_label.config(text="● Connecting...", foreground="orange")
        self.daminion_connect_button.config(state="disabled")

        threading.Thread(target=self.connect_daminion_worker,
                        args=(url, username, password), daemon=True).start()

    def connect_daminion_worker(self, url, username, password):
        """Worker thread for Daminion connection"""
        logging.info(f"[GUI] ========== DAMINION CONNECTION WORKER STARTED ==========")
        logging.info(f"[GUI] URL: {url}")
        logging.info(f"[GUI] Username: {username}")

        try:
            logging.info(f"[GUI] Creating DaminionClient instance...")
            client = DaminionClient(url, username, password)

            logging.info(f"[GUI] Testing connection to Daminion server...")
            status = client.test_connection()
            logging.info(f"[GUI] Connection test result: {status}")

            if status['connected']:
                logging.info(f"[GUI] \u2713 Connection successful!")
                self.daminion_client = client

                logging.debug(f"[GUI] Saving connection config...")
                self.config_manager.set('daminion_url', url)
                self.config_manager.set('daminion_username', username)
                self.config_manager.save_config()

                logging.info(f"[GUI] Notifying GUI of successful connection...")
                self.q.put(("daminion_connected", status))

                # fetch shared collections immediately in the worker thread
                try:
                    logging.info(f"[GUI] Fetching shared collections...")
                    cols = client.get_shared_collections(index=0, page_size=200)
                    logging.info(f"[GUI] Retrieved {len(cols) if cols else 0} shared collections")
                    self.q.put(("daminion_collections", cols))
                except Exception as coll_error:
                    logging.warning(f"[GUI] Failed to fetch collections: {coll_error}")
                    pass

                logging.info(f"[GUI] ========== CONNECTION WORKER COMPLETE ==========")
            else:
                error_msg = status.get('error', 'Unknown error')
                logging.error(f"[GUI] \u2717 Connection failed: {error_msg}")
                self.q.put(("daminion_error", error_msg))

        except Exception as e:
            logging.exception(f"[GUI] \u2717 Daminion connection worker exception")
            self.q.put(("daminion_error", str(e)))

    def find_models(self):
        """Search for models on Hugging Face"""
        self.find_models_button.config(state="disabled")
        self.status_label.config(text="Status: Searching for models on Hugging Face...")
        logging.info("User initiated model search.")
        threading.Thread(target=self.find_models_worker, daemon=True).start()

    def find_models_worker(self):
        """Worker thread for finding models"""
        try:
            task = self.model_task.get()
            model_ids, downloaded_models = huggingface_utils.find_models_by_task(task)
            self.q.put(("models_found", (model_ids, downloaded_models)))
            logging.info(f"Found {len(model_ids)} models for task {task}.")
        except Exception as e:
            logging.exception("Failed to find models.")
            self.q.put(("error", f"Failed to find models: {e}"))

    def show_model_info(self, event=None):
        """Show information about selected model"""
        selection = self.model_listbox.curselection()
        if not selection:
            return

        model_id_display = self.model_listbox.get(selection[0])
        model_id = model_id_display.split(" (")[0]

        self.status_label.config(text=f"Status: Fetching info for {model_id}...")
        threading.Thread(target=self.show_model_info_worker, args=(model_id,), daemon=True).start()

    def show_model_info_worker(self, model_id):
        """Worker thread for fetching model info"""
        try:
            info = huggingface_utils.get_model_info(model_id)
            self.q.put(("model_info_found", info))
        except Exception as e:
            logging.exception(f"Failed to fetch model info for {model_id}.")
            self.q.put(("error", f"Failed to fetch model info: {e}"))

    def load_model(self):
        """Load selected model"""
        selection = self.model_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a model from the list.")
            return

        model_id_display = self.model_listbox.get(selection[0])
        model_id = model_id_display.split(" (")[0]

        self.load_model_button.config(state="disabled")
        self.status_label.config(text=f"Status: Downloading and loading {model_id}...")
        logging.info(f"User initiated loading of model {model_id}.")

        threading.Thread(target=self.load_model_worker, args=(model_id,), daemon=True).start()

    def load_model_worker(self, model_id):
        """Worker thread for loading model"""
        try:
            task = self.model_task.get()
            model = huggingface_utils.load_model(model_id, task, progress_queue=self.q)
            self.q.put(("model_loaded", model))
            logging.info(f"Model {model_id} loaded successfully.")
        except Exception as e:
            logging.exception(f"Failed to load model {model_id}.")
            self.q.put(("error", f"Failed to load model: {e}"))

    def start_processing(self):
        """Start image processing"""
        logging.info("User started image processing.")

        if self.processing_mode == "daminion":
            self.start_daminion_processing()
        else:
            self.start_local_processing()

    def start_local_processing(self):
        """Start processing local files"""
        if not self.image_dir:
            messagebox.showerror("Error", "Please select an image directory first.")
            return

        task = self.model_task.get()
        cats_str = self.categories_entry.get().strip()
        keywords_str = self.keywords_entry.get().strip()

        if not cats_str and task == config.MODEL_TASK_IMAGE_CLASSIFICATION:
            messagebox.showerror("Error", "Categories are required for image classification.")
            return

        if not keywords_str and task == config.MODEL_TASK_ZERO_SHOT:
            messagebox.showerror("Error", "Keywords are required for zero-shot classification.")
            return

        categories = [c.strip() for c in cats_str.split(",") if c.strip()]
        keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]

        if not categories and task == config.MODEL_TASK_IMAGE_CLASSIFICATION:
            messagebox.showerror("Error", "At least one valid category is required.")
            return

        if not keywords and task == config.MODEL_TASK_ZERO_SHOT:
            messagebox.showerror("Error", "At least one valid keyword is required.")
            return

        all_image_files = []
        for ext in config.SUPPORTED_IMAGE_EXTENSIONS:
            all_image_files.extend(self.image_dir.rglob(ext))

        if not all_image_files:
            logging.warning("Image processing started with no images found.")
            messagebox.showinfo("Info", "No image files found in the selected directory.")
            return

        saved_job = self.progress_tracker.load_job()
        scope = getattr(self, 'scope_var', None) and self.scope_var.get() or 'untagged'

        # When filtering by collection/flagged we will ignore previous saved job and work from
        # the filtered set. For untagged (default) we preserve the existing resume logic.
        if scope == 'untagged' and saved_job and saved_job.get("directory") == str(self.image_dir):
            resume = messagebox.askyesno(
                "Resume Job",
                f"Found incomplete job from {saved_job.get('started_at', 'unknown')}\n"
                f"Processed: {len(saved_job.get('processed_images', []))} / {saved_job.get('total_images', 0)}\n\n"
                "Do you want to resume?"
            )
            if not resume:
                self.progress_tracker.clear()
                image_files = all_image_files
            else:
                image_files = self.progress_tracker.get_unprocessed_images(all_image_files)
                if not image_files:
                    messagebox.showinfo("Info", "All images have already been processed.")
                    self.progress_tracker.complete_job()
                    return
        else:
            # For collection or flagged scope, filter the full image list accordingly
            if scope == 'collection':
                if not self.collection_path:
                    messagebox.showerror("Error", "Please select a collection sub-folder to process.")
                    return

                image_files = [p for p in all_image_files if self.collection_path in p.parents or str(p).startswith(str(self.collection_path))]
            elif scope == 'flagged':
                def is_flagged(p):
                    name = p.name.lower()
                    if 'flag' in name or 'reject' in name or 'rejected' in name:
                        return True
                    # check parent folder names
                    for part in p.parents:
                        pn = part.name.lower()
                        if 'flag' in pn or 'reject' in pn or 'rejected' in pn:
                            return True
                    return False

                image_files = [p for p in all_image_files if is_flagged(p)]
            else:
                # default: untagged behavior or fallback to everything
                self.progress_tracker.clear()
                image_files = all_image_files

        model_name = self.model.model.name_or_path if self.model else "unknown"
        self.progress_tracker.start_job(self.image_dir, len(image_files), model_name, task)

        self.report.start_session(model_name, task, len(image_files))
        self.processing_start_time = time.time()

        self.start_button.config(state="disabled")
        self.progress_bar["maximum"] = len(image_files)
        self.progress_bar["value"] = 0
        self.progress_label.config(text=f"0 / {len(image_files)} images processed")
        self.time_label.config(text="Calculating...")
        logging.info(f"Starting processing for {len(image_files)} images.")
        threading.Thread(target=self.process_images_worker,
                        args=(image_files, categories, keywords), daemon=True).start()

    def start_daminion_processing(self):
        """Start processing Daminion items"""
        if not self.daminion_client:
            messagebox.showerror("Error", "Not connected to Daminion. Please connect first.")
            return

        task = self.model_task.get()
        cats_str = self.categories_entry.get().strip()
        keywords_str = self.keywords_entry.get().strip()

        if not cats_str and task == config.MODEL_TASK_IMAGE_CLASSIFICATION:
            messagebox.showerror("Error", "Categories are required for image classification.")
            return

        if not keywords_str and task == config.MODEL_TASK_ZERO_SHOT:
            messagebox.showerror("Error", "Keywords are required for zero-shot classification.")
            return

        categories = [c.strip() for c in cats_str.split(",") if c.strip()]
        keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]

        if not categories and task == config.MODEL_TASK_IMAGE_CLASSIFICATION:
            messagebox.showerror("Error", "At least one valid category is required.")
            return

        if not keywords and task == config.MODEL_TASK_ZERO_SHOT:
            messagebox.showerror("Error", "At least one valid keyword is required.")
            return

        scope = getattr(self, 'scope_var', None) and self.scope_var.get() or 'untagged'

        items_to_process = None

        if scope == 'untagged':
            items, total = self.daminion_client.get_untagged_items()
            if not items:
                messagebox.showinfo("Info", "No untagged items found in Daminion.")
                return
            if not messagebox.askyesno("Start Daminion Processing",
                                       f"This will process {len(items)} untagged items from Daminion. Proceed?"):
                return
            items_to_process = items

        elif scope == 'flagged':
            # use a Daminion client helper that applies server fetch + heuristics
            filtered = self.daminion_client.get_flagged_items(batch_size=200, max_items=None)
            if not filtered:
                messagebox.showinfo("Info", "No flagged/rejected items found in Daminion.")
                return
            if not messagebox.askyesno("Start Daminion Processing",
                                       f"This will process {len(filtered)} flagged/rejected items from Daminion. Proceed?"):
                return
            items_to_process = filtered

        elif scope == 'collection':
            # for Daminion we prefer using an explicit shared collection selection
            if not self.daminion_collections:
                messagebox.showerror("Error", "No Daminion collections are available. Refresh collections or connect to the server.")
                return

            sel_index = self.daminion_collection_combo.current()
            if sel_index is None or sel_index < 0:
                messagebox.showerror("Error", "Please select a shared collection to process from Daminion.")
                return

            col = self.daminion_collections[sel_index]
            collection_id = col.get('id') or col.get('code') or col.get('collectionId')
            if not collection_id:
                messagebox.showerror("Error", "Selected collection does not have a usable identifier.")
                return

            items = self.daminion_client.get_shared_collection_items(collection_id, index=0, page_size=500)
            if not items:
                messagebox.showinfo("Info", f"No items were found in the selected shared collection.")
                return

            if not messagebox.askyesno("Start Daminion Processing",
                                       f"This will process {len(items)} items from the selected shared collection. Proceed?"):
                return

            items_to_process = items

        if not items_to_process:
            # fallback guard
            if not messagebox.askyesno("Start Daminion Processing",
                                       f"This will process items from Daminion.\n\nTotal items in catalog: {self.daminion_client.get_total_count()}\nProcessing mode: {task}\n\nProcess all items?"):
                return
            items_to_process = self.daminion_client.get_all_items_paginated(batch_size=100, max_items=None)

        self.start_button.config(state="disabled")
        logging.info("Starting Daminion processing...")
        threading.Thread(target=self.process_daminion_worker,
                         args=(categories, keywords, items_to_process), daemon=True).start()

    def process_daminion_worker(self, categories, keywords, items=None):
        """Worker thread for processing Daminion items"""
        logging.info(f"[GUI] ========== DAMINION PROCESSING WORKER STARTED ==========")
        logging.info(f"[GUI] Categories: {categories}")
        logging.info(f"[GUI] Keywords: {keywords}")
        logging.info(f"[GUI] Pre-filtered items: {len(items) if items else 'None (will fetch all)'}")

        model_task = self.model_task.get()
        logging.info(f"[GUI] Model task: {model_task}")

        if not self.daminion_client:
            logging.error(f"[GUI] \u2717 Daminion client not initialized!")
            self.q.put(("error", "Daminion client not initialized"))
            return

        if not self.model:
            logging.error(f"[GUI] \u2717 Model not loaded!")
            self.q.put(("error", "Model not loaded"))
            return

        logging.info(f"[GUI] Daminion client: {self.daminion_client}")
        logging.info(f"[GUI] Model: {self.model}")

        try:
            if items is None:
                logging.info(f"[GUI] No pre-filtered items, fetching all from Daminion...")
                self.q.put(("status_update", "Fetching items from Daminion..."))
                items = self.daminion_client.get_all_items_paginated(batch_size=100, max_items=None)
                logging.info(f"[GUI] \u2713 Fetched {len(items)} items from Daminion")

            if not items:
                logging.error(f"[GUI] \u2717 No items retrieved from Daminion")
                self.q.put(("error", "No items retrieved from Daminion"))
                return

            # Validate items structure
            logging.info(f"[GUI] Validating items structure...")
            logging.info(f"[GUI] Items type: {type(items)}")
            logging.info(f"[GUI] Items length: {len(items)}")
            if items:
                logging.info(f"[GUI] First item type: {type(items[0])}")
                logging.info(f"[GUI] First item sample: {str(items[0])[:200] if isinstance(items[0], dict) else type(items[0])}")

            # Flatten if items is a list of lists
            if items and isinstance(items[0], list):
                logging.warning(f"[GUI] Items is a list of lists, flattening...")
                flat_items = []
                for sublist in items:
                    if isinstance(sublist, list):
                        flat_items.extend(sublist)
                    else:
                        flat_items.append(sublist)
                items = flat_items
                logging.info(f"[GUI] Flattened to {len(items)} items")

            # Validate each item is a dict
            valid_items = []
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    valid_items.append(item)
                else:
                    logging.warning(f"[GUI] Skipping item {i}: not a dict, type={type(item)}")

            items = valid_items
            logging.info(f"[GUI] Valid items after filtering: {len(items)}")

            if not items:
                logging.error(f"[GUI] [ERROR] No valid items after validation")
                self.q.put(("error", "No valid items to process"))
                return


            logging.info(f"[GUI] Setting up progress tracking for {len(items)} items...")
            self.q.put(("progress_max", len(items)))
            self.q.put(("status_update", f"Processing {len(items)} items..."))

            completed_count = 0
            failed_count = 0

            logging.info(f"[GUI] ========== STARTING ITEM PROCESSING LOOP ==========")

            for idx, item in enumerate(items, 1):
                if self.stop_event.is_set():
                    logging.warning(f"[GUI] Stop event detected, aborting processing")
                    break

                try:
                    item_id = item.get('id')
                    filename = item.get('fileName', f'item_{item_id}')

                    logging.info(f"[GUI] --- Processing item {idx}/{len(items)}: {filename} (ID: {item_id}) ---")
                    self.q.put(("status_update", f"Processing {filename}..."))

                    logging.debug(f"[GUI] Downloading thumbnail for item {item_id}...")
                    thumb_path = self.daminion_client.download_thumbnail(item_id)

                    if not thumb_path or not thumb_path.exists():
                        logging.error(f"[GUI] \u2717 Failed to download thumbnail for item {item_id}")
                        failed_count += 1
                        continue

                    logging.debug(f"[GUI] \u2713 Thumbnail downloaded: {thumb_path}")
                    logging.debug(f"[GUI] Opening image with PIL...")

                    from PIL import Image
                    image = Image.open(thumb_path)
                    logging.debug(f"[GUI] \u2713 Image opened: {image.size}, {image.mode}")

                    result = None

                    if model_task == config.MODEL_TASK_IMAGE_CLASSIFICATION:
                        logging.debug(f"[GUI] Running image classification with {len(categories)} categories...")
                        result = self.model(image, candidate_labels=categories)
                        logging.debug(f"[GUI] \u2713 Classification result: {result}")

                        if result:
                            category = result[0]['label']
                            confidence = result[0]['score']
                            logging.info(f"[GUI] \u2713 Item {item_id}: Category={category} (confidence={confidence:.2f})")

                            logging.debug(f"[GUI] Updating Daminion metadata for item {item_id}...")
                            self.daminion_client.update_item_metadata(str(item_id), category=category)
                            logging.debug(f"[GUI] \u2713 Metadata updated")

                    elif model_task == config.MODEL_TASK_ZERO_SHOT:
                        logging.debug(f"[GUI] Running zero-shot classification with {len(keywords)} keywords...")
                        result = self.model(image, candidate_labels=keywords)
                        logging.debug(f"[GUI] \u2713 Zero-shot result: {result}")

                        if result:
                            detected_keywords = [r['label'] for r in result if r['score'] > 0.9]
                            if detected_keywords:
                                logging.info(f"[GUI] \u2713 Item {item_id}: Keywords={detected_keywords}")

                                logging.debug(f"[GUI] Updating Daminion metadata for item {item_id}...")
                                self.daminion_client.update_item_metadata(str(item_id),
                                                                        keywords=detected_keywords)
                                logging.debug(f"[GUI] \u2713 Metadata updated")
                            else:
                                logging.info(f"[GUI] Item {item_id}: No keywords above 0.9 threshold")

                    elif model_task == config.MODEL_TASK_IMAGE_TO_TEXT:
                        logging.debug(f"[GUI] Running image-to-text generation...")
                        result = self.model(image)
                        logging.debug(f"[GUI] \u2713 Image-to-text result: {result}")

                        if result and len(result) > 0:
                            generated_text = result[0].get('generated_text', '')
                            generated_keywords = [w for w in generated_text.split() if len(w) > 3][:10]
                            logging.info(f"[GUI] \u2713 Item {item_id}: Generated keywords={generated_keywords}")

                            logging.debug(f"[GUI] Updating Daminion metadata for item {item_id}...")
                            self.daminion_client.update_item_metadata(str(item_id),
                                                                    keywords=generated_keywords)
                            logging.debug(f"[GUI] \u2713 Metadata updated")

                    completed_count += 1
                    logging.info(f"[GUI] \u2713 Item {idx}/{len(items)} processed successfully")
                    self.q.put(("progress", completed_count))

                except Exception as e:
                    failed_count += 1
                    logging.exception(f"[GUI] \u2717 Error processing Daminion item {item.get('id')}")
                    self.q.put(("error", f"Failed to process item: {e}"))

            logging.info(f"[GUI] ========== ITEM PROCESSING LOOP COMPLETE ==========")
            logging.info(f"[GUI] Total processed: {completed_count}")
            logging.info(f"[GUI] Total failed: {failed_count}")

            logging.info(f"[GUI] Cleaning up temp files...")
            self.daminion_client.cleanup_temp_files()

            self.q.put(("progress_done", f"Finished processing {completed_count} Daminion items."))
            logging.info(f"[GUI] ========== DAMINION PROCESSING WORKER COMPLETE ==========")

        except Exception as e:
            logging.exception(f"[GUI] \u2717 CRITICAL: Daminion processing worker failed")
            logging.error(f"[GUI] Exception type: {type(e).__name__}")
            logging.error(f"[GUI] Exception message: {str(e)}")
            self.q.put(("error", f"Daminion processing failed: {e}"))

    def process_images_worker(self, image_files, categories, keywords):
        """Worker thread for processing local images"""
        logging.info("Image processing worker started.")
        model_task = self.model_task.get()
        max_workers = self.config_manager.get('max_concurrent_workers', 4)

        completed_count = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_image = {
                executor.submit(
                    image_processing.process_single_image,
                    image_path, self.model, model_task, categories, keywords, self.q
                ): image_path for image_path in image_files
            }

            for future in as_completed(future_to_image):
                image_path = future_to_image[future]
                start_time = time.time()
                completed_count += 1
                self.q.put(("progress", completed_count))

                try:
                    success, error = future.result()
                    processing_time = time.time() - start_time

                    if success:
                        self.progress_tracker.mark_processed(image_path)
                        self.report.add_result(
                            str(image_path),
                            "",
                            [],
                            True,
                            None,
                            processing_time
                        )
                    else:
                        error_msg = error or "Unknown error"
                        self.progress_tracker.mark_failed(image_path, error_msg)
                        self.report.add_result(
                            str(image_path),
                            "",
                            [],
                            False,
                            error_msg,
                            processing_time
                        )

                except Exception as e:
                    logging.exception(f"Error processing {image_path.name} in worker.")
                    error_msg = str(e)
                    processing_time = time.time() - start_time

                    self.progress_tracker.mark_failed(image_path, error_msg)
                    self.report.add_result(
                        str(image_path),
                        "",
                        [],
                        False,
                        error_msg,
                        processing_time
                    )
                    self.q.put(("error", f"Failed to process {image_path.name}: {e}"))

        self.progress_tracker.complete_job()
        self.q.put(("progress_done", "Finished processing."))
        logging.info("Image processing worker finished.")

    def process_queue(self):
        """Process messages from worker threads"""
        try:
            message_type, data = self.q.get_nowait()
            logging.debug(f"GUI received queue message: {message_type}")

            if message_type == "models_found":
                self.model_listbox.delete(0, tk.END)
                model_ids, downloaded_models = data
                for model_id in model_ids:
                    if model_id in downloaded_models:
                        self.model_listbox.insert(tk.END, f"{model_id} ([OK] cached)")
                        self.model_listbox.itemconfig(tk.END, fg='green')
                    else:
                        self.model_listbox.insert(tk.END, model_id)
                self.status_label.config(text=f"Status: Found {len(model_ids)} models. Select one to see details.")
                self.find_models_button.config(state="normal")
                self._update_step_states()

            elif message_type == "model_info_found":
                self.model_info_text.delete("1.0", tk.END)
                self.model_info_text.insert("1.0", data)
                self.status_label.config(text="Status: Model info loaded.")

            elif message_type == "model_download_progress":
                current, total = data
                # Defensive defaults
                total = total or 1
                self.model_progress_bar["maximum"] = total
                self.model_progress_bar["value"] = current

                # Initialize download tracking on first progress message
                now = time.time()
                if not self._dl_start_time:
                    self._dl_start_time = now
                    self._dl_total_bytes = total
                    self._dl_last_bytes = current
                    self._dl_last_time = now

                # Compute average bytes/sec and ETA
                elapsed = max(0.001, now - self._dl_start_time)
                bytes_per_sec = current / elapsed if elapsed > 0 else 0
                remaining = max(0, total - current)
                eta = int(remaining / bytes_per_sec) if bytes_per_sec > 0 else None

                # Format human-friendly label
                def _mb(b):
                    return b / (1024 * 1024)

                percent = (current / total) * 100 if total else 0
                if eta is None:
                    eta_text = ""
                elif eta < 60:
                    eta_text = f"ETA: ~{eta}s"
                else:
                    m = int(eta / 60)
                    eta_text = f"ETA: ~{m}m"

                self.model_progress_label.config(
                    text=f"{_mb(current):.1f}/{_mb(total):.1f} MB ({percent:.1f}%) {eta_text}"
                )

                # Reset when finished
                if current >= total:
                    self._dl_start_time = None
                    self._dl_total_bytes = None
                    self._dl_last_bytes = 0
                    self._dl_last_time = None
                    # briefly keep the success text then clear progress bar later when model_loaded arrives

            elif message_type == "model_loaded":
                self.model = data
                model_name = self.model.model.name_or_path
                self.config_manager.set('last_model_id', model_name)
                self.config_manager.set('last_model_task', self.model_task.get())
                self.config_manager.save_config()
                self.status_label.config(text=f"Status: Model {model_name} loaded successfully!")
                self.load_model_button.config(state="normal")
                self.model_progress_bar["value"] = 0
                self.model_progress_label.config(text="")
                self._update_step_states()

            elif message_type == "error":
                self.status_label.config(text=f"Status: Error - {data}")
                self.load_model_button.config(state="normal")
                self.find_models_button.config(state="normal")

            elif message_type == "status_update":
                self.status_label.config(text=f"Status: {data}")

            elif message_type == "progress_max":
                self.progress_bar["maximum"] = data
                self.progress_bar["value"] = 0
                self.progress_label.config(text=f"0 / {data} images processed")

            elif message_type == "progress":
                self.progress_bar["value"] = data
                max_val = self.progress_bar["maximum"]
                self.progress_label.config(text=f"{data} / {int(max_val)} images processed")

                time_remaining = self.calculate_time_remaining(data, int(max_val))
                self.time_label.config(text=time_remaining)

            elif message_type == "progress_done":
                self.report.end_session()
                self.status_label.config(text=f"Status: {data}")
                self.start_button.config(state="normal")
                self.progress_bar["value"] = self.progress_bar["maximum"]
                max_val = int(self.progress_bar["maximum"])
                self.progress_label.config(text=f"{max_val} / {max_val} images processed - Complete!")
                self.time_label.config(text="Done!")

            elif message_type == "daminion_connected":
                status = data
                self.daminion_status_label.config(
                    text=f"● Connected: {status['total_items']} items in catalog",
                    foreground="green"
                )
                self.daminion_connect_button.config(state="normal")
                self._update_step_states()
                logging.info(f"Daminion connected: {status['total_items']} items")

            elif message_type == "daminion_error":
                self.daminion_status_label.config(text=f"● Connection failed", foreground="red")
                self.daminion_connect_button.config(state="normal")
                messagebox.showerror("Daminion Connection Error",
                                   f"Failed to connect to Daminion:\n\n{data}")
                self._update_step_states()

            elif message_type == "daminion_collections":
                # populate combobox with names and keep full collection objects for selection
                cols = data or []
                # normalize to list of dicts
                if isinstance(cols, dict):
                    # if API wraps collection list in data/results
                    vals = cols.get('items') or cols.get('collections') or list(cols.values())
                    cols = vals or []

                self.daminion_collections = cols
                names = []
                for c in cols:
                    # try to choose a friendly label for combobox
                    title = c.get('name') or c.get('title') or c.get('code') or str(c.get('id') or '')
                    idx = c.get('id') or c.get('code') or c.get('collectionId') or ''
                    names.append(f"{title} ({idx})" if idx else title)

                self.daminion_collection_combo['values'] = names
                if names:
                    self.daminion_collection_combo.current(0)
                # ensure refresh button is enabled
                try:
                    self.refresh_collections_btn.config(state='normal')
                except Exception:
                    pass

        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue)

    def refresh_daminion_collections(self):
        """Start background refresh of shared collections and update the combobox."""
        if not self.daminion_client:
            messagebox.showerror("Error", "Not connected to Daminion. Please connect first.")
            return

        self.refresh_collections_btn.config(state='disabled')
        self.status_label.config(text="Status: Refreshing Daminion collections...")
        threading.Thread(target=self.refresh_daminion_collections_worker, daemon=True).start()

    def refresh_daminion_collections_worker(self):
        try:
            if not self.daminion_client:
                self.q.put(("error", "Daminion client not initialized"))
                return

            cols = self.daminion_client.get_shared_collections(index=0, page_size=200)
            self.q.put(("daminion_collections", cols))
            self.q.put(("status_update", f"Found {len(cols)} shared collections on server."))
        except Exception as e:
            logging.exception("Failed to refresh collections")
            self.q.put(("error", f"Failed to fetch collections: {e}"))

    def show_cache_path(self):
        """Show cache path dialog"""
        logging.info("User viewed cache path.")
        messagebox.showinfo("Hugging Face Cache Path",
                          f"The model cache is located at:\n\n{config.HF_CACHE_DIR}")

    def clear_cache(self):
        """Clear model cache"""
        logging.info("User initiated cache clearing.")
        if messagebox.askyesno("Confirm Clear Cache",
                              "Are you sure you want to delete the entire model cache?\n"
                              "This action cannot be undone and will require re-downloading all models."):
            try:
                cache_path = Path(config.HF_CACHE_DIR)
                if not cache_path.exists():
                    logging.warning("Cache directory not found during clearing.")
                    messagebox.showinfo("Info", "The cache directory does not exist.")
                    return

                if not cache_path.is_dir():
                    logging.error(f"Cache path is not a directory: {cache_path}")
                    messagebox.showerror("Error", "Cache path is not a valid directory.")
                    return

                cache_path_resolved = cache_path.resolve()
                if config.CACHE_DIRECTORY_IDENTIFIER not in str(cache_path_resolved):
                    logging.error(f"Refusing to delete directory that doesn't appear to be a cache: {cache_path_resolved}")
                    messagebox.showerror("Error", "Safety check failed: path does not appear to be a cache directory.")
                    return

                shutil.rmtree(cache_path)
                logging.info("Cache cleared successfully.")
                messagebox.showinfo("Success", "The model cache has been cleared.")
            except FileNotFoundError:
                logging.warning("Cache directory not found during clearing.")
                messagebox.showinfo("Info", "The cache directory does not exist.")
            except Exception as e:
                logging.exception("Failed to clear cache.")
                messagebox.showerror("Error", f"Failed to clear cache: {e}")

    def export_report_csv(self):
        """Export processing report to CSV"""
        if not self.report.results:
            messagebox.showinfo("No Data", "No processing results to export.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save CSV Report",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if file_path:
            success = self.report.export_csv(Path(file_path))
            if success:
                messagebox.showinfo("Success", f"Report exported to:\n{file_path}")
            else:
                messagebox.showerror("Error", "Failed to export report.")

    def export_report_json(self):
        """Export processing report to JSON"""
        if not self.report.results:
            messagebox.showinfo("No Data", "No processing results to export.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save JSON Report",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            success = self.report.export_json(Path(file_path), include_summary=True)
            if success:
                messagebox.showinfo("Success", f"Report exported to:\n{file_path}")
            else:
                messagebox.showerror("Error", "Failed to export report.")

    def show_report_summary(self):
        """Show report summary dialog"""
        if not self.report.results:
            messagebox.showinfo("No Data", "No processing results available.")
            return

        summary = self.report.get_summary()

        summary_text = f"""Processing Report Summary

Model: {summary['model_name']}
Task: {summary['model_task']}
Duration: {summary['session_duration_seconds']}s

Processed: {summary['processed']} / {summary['total_images']} images
Successful: {summary['successful']} ({summary['success_rate']}%)
Failed: {summary['failed']}

Average time per image: {summary['average_time_per_image_seconds']}s
Total processing time: {summary['total_processing_time_seconds']}s
"""

        if self.report.failed > 0:
            failed_images = self.report.get_failed_images()
            summary_text += f"\n\nFailed Images ({len(failed_images)}):\n"
            for result in failed_images[:10]:
                summary_text += f"  - {result['image_name']}: {result['error_message']}\n"
            if len(failed_images) > 10:
                summary_text += f"  ... and {len(failed_images) - 10} more\n"

        messagebox.showinfo("Processing Report", summary_text)

    def calculate_time_remaining(self, completed: int, total: int) -> str:
        """Calculate estimated time remaining"""
        if not self.processing_start_time or completed == 0:
            return ""

        elapsed = time.time() - self.processing_start_time
        avg_time_per_item = elapsed / completed
        remaining = total - completed
        estimated_seconds = avg_time_per_item * remaining

        if estimated_seconds < 60:
            return f"~{int(estimated_seconds)}s remaining"
        elif estimated_seconds < 3600:
            minutes = int(estimated_seconds / 60)
            return f"~{minutes}m remaining"
        else:
            hours = int(estimated_seconds / 3600)
            minutes = int((estimated_seconds % 3600) / 60)
            return f"~{hours}h {minutes}m remaining"

def main():
    from logging_config import setup_logging
    setup_logging()
    app = ImageTaggerGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
