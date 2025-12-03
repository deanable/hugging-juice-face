"""
GUI step components for the Image Tagger application.
Contains methods for creating the step-by-step workflow UI.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import config


class CollapsiblePane(ttk.Frame):
    """Collapsible container to reduce UI overflow on small screens."""

    def __init__(self, parent, title="", *args, **kwargs):
        super().__init__(parent)
        self.title = title
        header = ttk.Frame(self)
        header.pack(fill="x")
        self._btn = ttk.Button(header, text=f"▾ {self.title}", width=40, command=self._toggle)
        self._btn.pack(side="left", anchor="w")
        self.content = ttk.Frame(self)
        self.content.pack(fill="both", expand=True)

    def _toggle(self):
        if self.content.winfo_ismapped():
            self.content.pack_forget()
            self._btn.config(text=f"▸ {self.title}")
        else:
            self.content.pack(fill="both", expand=True)
            self._btn.config(text=f"▾ {self.title}")


def create_step1_source(parent, gui_instance):
    """Create Step 1: Choose Image Source widgets.

    Args:
        parent: Parent widget
        gui_instance: Reference to main GUI instance for event handlers
    """
    frame = ttk.LabelFrame(parent, text="⓵ Choose Image Source", padding="15")
    frame.pack(fill="x", pady=(0, 15))

    mode_frame = ttk.Frame(frame)
    mode_frame.pack(fill="x", pady=(0, 10))

    ttk.Label(mode_frame, text="Select where your images are:",
             font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))

    gui_instance.mode_var = tk.StringVar(value="local")

    radio_frame = ttk.Frame(mode_frame)
    radio_frame.pack(fill="x")

    gui_instance.local_radio = ttk.Radiobutton(
        radio_frame, text="📁 Local Files (from your computer)",
        variable=gui_instance.mode_var, value="local",
        command=gui_instance.on_mode_change
    )
    gui_instance.local_radio.pack(anchor="w", padx=20)

    gui_instance.daminion_radio = ttk.Radiobutton(
        radio_frame, text="☁️  Daminion DAMS (from cloud server)",
        variable=gui_instance.mode_var, value="daminion",
        command=gui_instance.on_mode_change
    )
    gui_instance.daminion_radio.pack(anchor="w", padx=20, pady=(5, 0))

    # Local files section
    gui_instance.local_section = ttk.Frame(frame)
    gui_instance.local_section.pack(fill="x", pady=(10, 0))

    ttk.Label(gui_instance.local_section, text="Image Directory:",
             font=("Arial", 9)).pack(anchor="w")

    dir_frame = ttk.Frame(gui_instance.local_section)
    dir_frame.pack(fill="x", pady=(5, 0))

    gui_instance.select_dir_button = ttk.Button(
        dir_frame, text="Browse...",
        command=gui_instance.select_directory, width=15
    )
    gui_instance.select_dir_button.pack(side="left")

    gui_instance.dir_label = ttk.Label(
        dir_frame, text="No directory selected", foreground="gray"
    )
    gui_instance.dir_label.pack(side="left", padx=(10, 0))

    # Daminion section (hidden by default)
    gui_instance.daminion_section = ttk.Frame(frame)

    ttk.Label(gui_instance.daminion_section, text="Daminion Server Connection:",
             font=("Arial", 9)).pack(anchor="w")

    conn_grid = ttk.Frame(gui_instance.daminion_section)
    conn_grid.pack(fill="x", pady=(5, 0))

    ttk.Label(conn_grid, text="Server URL:").grid(row=0, column=0, sticky="w", padx=(0, 10))
    gui_instance.daminion_url_entry = ttk.Entry(conn_grid, width=40)
    gui_instance.daminion_url_entry.grid(row=0, column=1, sticky="ew", pady=2)
    gui_instance.daminion_url_entry.insert(
        0, str(gui_instance.config_manager.get('daminion_url', 'https://interiors.daminion.net'))
    )

    ttk.Label(conn_grid, text="Username:").grid(row=1, column=0, sticky="w", padx=(0, 10))
    gui_instance.daminion_username_entry = ttk.Entry(conn_grid, width=40)
    gui_instance.daminion_username_entry.grid(row=1, column=1, sticky="ew", pady=2)
    gui_instance.daminion_username_entry.insert(
        0, str(gui_instance.config_manager.get('daminion_username', ''))
    )

    ttk.Label(conn_grid, text="Password:").grid(row=2, column=0, sticky="w", padx=(0, 10))
    gui_instance.daminion_password_entry = ttk.Entry(conn_grid, width=40, show="*")
    gui_instance.daminion_password_entry.grid(row=2, column=1, sticky="ew", pady=2)

    conn_grid.columnconfigure(1, weight=1)

    btn_frame = ttk.Frame(gui_instance.daminion_section)
    btn_frame.pack(fill="x", pady=(10, 0))

    gui_instance.daminion_connect_button = ttk.Button(
        btn_frame, text="Connect to Daminion",
        command=gui_instance.connect_daminion
    )
    gui_instance.daminion_connect_button.pack(side="left")

    gui_instance.daminion_status_label = ttk.Label(
        btn_frame, text="● Not connected", foreground="gray"
    )
    gui_instance.daminion_status_label.pack(side="left", padx=(15, 0))

    gui_instance.step1_status = ttk.Label(frame, text="", foreground="gray")
    gui_instance.step1_status.pack(anchor="w", pady=(10, 0))


def create_step2_model(parent, gui_instance):
    """Create Step 2: Select AI Model widgets.

    Args:
        parent: Parent widget
        gui_instance: Reference to main GUI instance
    """
    frame = ttk.LabelFrame(parent, text="⓶ Select AI Model", padding="15")
    frame.pack(fill="x", pady=(0, 15))

    ttk.Label(frame, text="Choose the type of AI analysis:",
             font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))

    task_frame = ttk.Frame(frame)
    task_frame.pack(fill="x", pady=(0, 10))

    ttk.Label(task_frame, text="Analysis Type:").grid(row=0, column=0, sticky="w", padx=(0, 10))
    gui_instance.model_task = ttk.Combobox(task_frame, values=[
        config.MODEL_TASK_IMAGE_CLASSIFICATION,
        config.MODEL_TASK_ZERO_SHOT,
        config.MODEL_TASK_IMAGE_TO_TEXT
    ], state="readonly", width=40)
    gui_instance.model_task.grid(row=0, column=1, sticky="ew")

    last_task = gui_instance.config_manager.get('last_model_task', config.MODEL_TASK_IMAGE_CLASSIFICATION)
    task_index = [
        config.MODEL_TASK_IMAGE_CLASSIFICATION,
        config.MODEL_TASK_ZERO_SHOT,
        config.MODEL_TASK_IMAGE_TO_TEXT
    ].index(last_task) if last_task in [
        config.MODEL_TASK_IMAGE_CLASSIFICATION,
        config.MODEL_TASK_ZERO_SHOT,
        config.MODEL_TASK_IMAGE_TO_TEXT
    ] else 0
    gui_instance.model_task.current(task_index)
    gui_instance.model_task.bind("<<ComboboxSelected>>", gui_instance.on_model_task_change)

    task_frame.columnconfigure(1, weight=1)

    gui_instance.task_description = ttk.Label(frame, text="", foreground="gray", wraplength=800)
    gui_instance.task_description.pack(anchor="w", pady=(5, 15))
    gui_instance.update_task_description()

    search_frame = ttk.Frame(frame)
    search_frame.pack(fill="x", pady=(0, 10))

    gui_instance.find_models_button = ttk.Button(
        search_frame, text="🔍 Search for Models on Hugging Face",
        command=gui_instance.find_models, width=35
    )
    gui_instance.find_models_button.pack(side="left")

    ttk.Label(frame, text="Available Models:", font=("Arial", 9)).pack(anchor="w", pady=(0, 5))

    list_frame = ttk.Frame(frame)
    list_frame.pack(fill="both", expand=True, pady=(0, 10))

    scrollbar = ttk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")

    gui_instance.model_listbox = tk.Listbox(list_frame, height=6, yscrollcommand=scrollbar.set)
    gui_instance.model_listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=gui_instance.model_listbox.yview)
    gui_instance.model_listbox.bind("<<ListboxSelect>>", gui_instance.show_model_info)

    ttk.Label(frame, text="Model Information:", font=("Arial", 9)).pack(anchor="w", pady=(0, 5))

    info_frame = ttk.Frame(frame)
    info_frame.pack(fill="both", expand=True, pady=(0, 10))

    info_scrollbar = ttk.Scrollbar(info_frame)
    info_scrollbar.pack(side="right", fill="y")

    gui_instance.model_info_text = tk.Text(
        info_frame, height=6, wrap="word", yscrollcommand=info_scrollbar.set
    )
    gui_instance.model_info_text.pack(side="left", fill="both", expand=True)
    info_scrollbar.config(command=gui_instance.model_info_text.yview)

    load_frame = ttk.Frame(frame)
    load_frame.pack(fill="x", pady=(0, 5))

    gui_instance.load_model_button = ttk.Button(
        load_frame, text="⬇️  Download & Load Selected Model",
        command=gui_instance.load_model, width=35
    )
    gui_instance.load_model_button.pack(side="left")

    gui_instance.model_progress_bar = ttk.Progressbar(
        load_frame, orient="horizontal", length=200, mode="determinate"
    )
    gui_instance.model_progress_bar.pack(side="left", padx=(15, 0), fill="x", expand=True)

    gui_instance.model_progress_label = ttk.Label(
        load_frame, text="", foreground="gray", font=("Arial", 8)
    )
    gui_instance.model_progress_label.pack(side="left", padx=(10, 0))

    gui_instance.step2_status = ttk.Label(frame, text="", foreground="gray")
    gui_instance.step2_status.pack(anchor="w")


def create_step3_config(parent, gui_instance):
    """Create Step 3: Configure Tagging widgets.

    Args:
        parent: Parent widget
        gui_instance: Reference to main GUI instance
    """
    frame = ttk.LabelFrame(parent, text="⓷ Configure Tagging", padding="15")
    frame.pack(fill="x", pady=(0, 15))

    ttk.Label(frame, text="Specify the categories or keywords for tagging:",
             font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 10))

    cat_frame = ttk.Frame(frame)
    cat_frame.pack(fill="x", pady=(0, 10))

    ttk.Label(cat_frame, text="Categories:", font=("Arial", 9)).grid(
        row=0, column=0, sticky="nw", padx=(0, 10), pady=5
    )
    ttk.Label(cat_frame, text="(for Image Classification)",
             foreground="gray", font=("Arial", 8)).grid(
        row=1, column=0, sticky="nw", padx=(0, 10)
    )

    gui_instance.categories_entry = ttk.Entry(cat_frame, width=60)
    gui_instance.categories_entry.grid(row=0, column=1, rowspan=2, sticky="ew", pady=5)
    default_categories = str(
        gui_instance.config_manager.get('default_categories', 'Interior, Exterior, Furniture, Decor')
    )
    gui_instance.categories_entry.insert(0, default_categories)

    cat_frame.columnconfigure(1, weight=1)

    ttk.Label(frame, text="Examples: Interior, Exterior, Furniture, Portrait, Landscape",
             foreground="gray", font=("Arial", 8)).pack(anchor="w", padx=(100, 0))

    kw_frame = ttk.Frame(frame)
    kw_frame.pack(fill="x", pady=(15, 10))

    ttk.Label(kw_frame, text="Keywords:", font=("Arial", 9)).grid(
        row=0, column=0, sticky="nw", padx=(0, 10), pady=5
    )
    ttk.Label(kw_frame, text="(for Zero-Shot Classification)",
             foreground="gray", font=("Arial", 8)).grid(
        row=1, column=0, sticky="nw", padx=(0, 10)
    )

    gui_instance.keywords_entry = ttk.Entry(kw_frame, width=60)
    gui_instance.keywords_entry.grid(row=0, column=1, rowspan=2, sticky="ew", pady=5)
    gui_instance.keywords_entry.insert(
        0, gui_instance.config_manager.get('default_keywords', 'bedroom, kitchen, sofa, chair, modern, vintage')
    )

    kw_frame.columnconfigure(1, weight=1)

    ttk.Label(frame, text="Examples: bedroom, kitchen, sofa, modern, vintage, sunset, portrait",
             foreground="gray", font=("Arial", 8)).pack(anchor="w", padx=(100, 0))

    note_frame = ttk.Frame(frame)
    note_frame.pack(fill="x", pady=(15, 0))

    ttk.Label(note_frame, text="ℹ️", font=("Arial", 12)).pack(side="left")
    ttk.Label(
        note_frame,
        text="For Image-to-Text, categories and keywords are not required (auto-generated)",
        foreground="gray", font=("Arial", 8), wraplength=750
    ).pack(side="left", padx=(5, 0))

    gui_instance.step3_status = ttk.Label(frame, text="", foreground="gray")
    gui_instance.step3_status.pack(anchor="w", pady=(10, 0))


def create_step4_process(parent, gui_instance):
    """Create Step 4: Process Images widgets.

    Args:
        parent: Parent widget
        gui_instance: Reference to main GUI instance
    """
    frame = ttk.LabelFrame(parent, text="⓸ Process Images", padding="15")
    frame.pack(fill="x", pady=(0, 15))

    ttk.Label(frame, text="Ready to tag your images with AI!",
             font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 10))

    scope_frame = ttk.Frame(frame)
    scope_frame.pack(fill="x", pady=(10, 5))

    ttk.Label(scope_frame, text="Process scope:", font=("Arial", 9, "bold")).pack(anchor="w")

    gui_instance.scope_var = tk.StringVar(value="untagged")

    rb_frame = ttk.Frame(scope_frame)
    rb_frame.pack(fill="x", padx=(20, 0))

    gui_instance.scope_collection_rb = ttk.Radiobutton(
        rb_frame, text="A collection",
        variable=gui_instance.scope_var, value="collection",
        command=gui_instance.on_scope_change
    )
    gui_instance.scope_collection_rb.pack(anchor="w")

    gui_instance.scope_flagged_rb = ttk.Radiobutton(
        rb_frame, text="Flagged / Rejected images",
        variable=gui_instance.scope_var, value="flagged",
        command=gui_instance.on_scope_change
    )
    gui_instance.scope_flagged_rb.pack(anchor="w", pady=(5, 0))

    gui_instance.scope_untagged_rb = ttk.Radiobutton(
        rb_frame, text="All untagged images",
        variable=gui_instance.scope_var, value="untagged",
        command=gui_instance.on_scope_change
    )
    gui_instance.scope_untagged_rb.pack(anchor="w", pady=(5, 0))

    gui_instance.collection_selector_frame = ttk.Frame(scope_frame)
    gui_instance.collection_selector_frame.pack(fill="x", pady=(5, 0))

    gui_instance.collection_path = None
    gui_instance.collection_path_label = ttk.Label(
        gui_instance.collection_selector_frame, text="No collection selected", foreground="gray"
    )
    gui_instance.collection_path_label.pack(side="left", padx=(20, 0))

    gui_instance.select_collection_btn = ttk.Button(
        gui_instance.collection_selector_frame, text="Select Collection (sub-folder)",
        command=gui_instance.select_collection
    )
    gui_instance.select_collection_btn.pack(side="left", padx=(5, 10))

    gui_instance.daminion_collections = []
    gui_instance.daminion_collection_combo = ttk.Combobox(
        gui_instance.collection_selector_frame, values=[], state='disabled', width=40
    )
    gui_instance.daminion_collection_combo.pack(side="left", padx=(5, 0))

    gui_instance.refresh_collections_btn = ttk.Button(
        gui_instance.collection_selector_frame, text="Refresh collections",
        command=gui_instance.refresh_daminion_collections
    )
    gui_instance.refresh_collections_btn.pack(side="left", padx=(6, 0))

    gui_instance.start_button = ttk.Button(
        frame, text="▶️  Start Processing Images",
        command=gui_instance.start_processing,
        state="disabled", width=30
    )
    gui_instance.start_button.pack(anchor="w")

    gui_instance.step4_status = ttk.Label(frame, text="", foreground="gray")
    gui_instance.step4_status.pack(anchor="w", pady=(10, 0))


def create_progress_section(parent, gui_instance):
    """Create progress tracking section.

    Args:
        parent: Parent widget
        gui_instance: Reference to main GUI instance
    """
    frame = ttk.LabelFrame(parent, text="Progress", padding="15")
    frame.pack(fill="both", expand=True)

    gui_instance.status_label = ttk.Label(
        frame, text="Status: Ready to begin", font=("Arial", 9)
    )
    gui_instance.status_label.pack(anchor="w", pady=(0, 10))

    gui_instance.progress_bar = ttk.Progressbar(
        frame, orient="horizontal", length=100, mode="determinate"
    )
    gui_instance.progress_bar.pack(fill="x", pady=(0, 5))

    progress_info_frame = ttk.Frame(frame)
    progress_info_frame.pack(fill="x")

    gui_instance.progress_label = ttk.Label(
        progress_info_frame, text="0 / 0 images processed",
        foreground="gray", font=("Arial", 8)
    )
    gui_instance.progress_label.pack(side="left")

    gui_instance.time_label = ttk.Label(
        progress_info_frame, text="", foreground="gray", font=("Arial", 8)
    )
    gui_instance.time_label.pack(side="right")
