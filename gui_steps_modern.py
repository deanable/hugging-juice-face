import customtkinter as ctk
from pathlib import Path
import config
import logging
import os


def create_step1_source(parent, gui_instance):
    """Create Step 1: Choose Image Source widgets using CustomTkinter.

    Args:
        parent: Parent widget (tab)
        gui_instance: Reference to main GUI instance for event handlers
    """
    # Main frame with modern styling
    main_frame = ctk.CTkFrame(parent, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Title with icon
    title_label = ctk.CTkLabel(
        main_frame,
        text="📁 Choose Image Source",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    title_label.pack(anchor="w", pady=(0, 15))

    # Mode selection section
    mode_section = ctk.CTkFrame(main_frame)
    mode_section.pack(fill="x", pady=(0, 20))

    mode_label = ctk.CTkLabel(
        mode_section,
        text="Select where your images are located:",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    mode_label.pack(anchor="w", padx=20, pady=(15, 10))

    # Radio button frame
    radio_frame = ctk.CTkFrame(mode_section, fg_color="transparent")
    radio_frame.pack(fill="x", padx=40, pady=(0, 15))

    # Initialize mode variable
    gui_instance.mode_var = ctk.StringVar(value="local")

    # Local files option
    local_radio = ctk.CTkRadioButton(
        radio_frame,
        text="📁 Local Files (from your computer)",
        variable=gui_instance.mode_var,
        value="local",
        command=lambda: gui_instance.on_mode_change("local"),
        font=ctk.CTkFont(size=13),
        width=300
    )
    local_radio.pack(anchor="w", pady=5)

    # Daminion option
    daminion_radio = ctk.CTkRadioButton(
        radio_frame,
        text="☁️ Daminion DAMS (from cloud server)",
        variable=gui_instance.mode_var,
        value="daminion",
        command=lambda: gui_instance.on_mode_change("daminion"),
        font=ctk.CTkFont(size=13),
        width=300
    )
    daminion_radio.pack(anchor="w", pady=5)

    # Local files section
    gui_instance.local_section = ctk.CTkFrame(main_frame)
    gui_instance.local_section.pack(fill="x", pady=(0, 20))

    local_label = ctk.CTkLabel(
        gui_instance.local_section,
        text="📂 Local Image Directory",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    local_label.pack(anchor="w", padx=20, pady=(15, 10))

    dir_frame = ctk.CTkFrame(gui_instance.local_section, fg_color="transparent")
    dir_frame.pack(fill="x", padx=40, pady=(0, 15))

    gui_instance.select_dir_button = ctk.CTkButton(
        dir_frame,
        text="📁 Browse Directory...",
        command=gui_instance.on_select_directory,
        width=150,
        height=35,
        font=ctk.CTkFont(size=12)
    )
    gui_instance.select_dir_button.pack(side="left")

    gui_instance.dir_label = ctk.CTkLabel(
        dir_frame,
        text="No directory selected",
        text_color="gray"
    )
    gui_instance.dir_label.pack(side="left", padx=(15, 0))

    # Daminion section (initially hidden)
    gui_instance.daminion_section = ctk.CTkFrame(main_frame)

    daminion_label = ctk.CTkLabel(
        gui_instance.daminion_section,
        text="☁️ Daminion Server Connection",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    daminion_label.pack(anchor="w", padx=20, pady=(15, 10))

    # Connection form (using grid-like layout for better responsiveness)
    conn_frame = ctk.CTkFrame(gui_instance.daminion_section, fg_color="transparent")
    conn_frame.pack(fill="x", padx=40, pady=(0, 15))

    # Server URL
    url_frame = ctk.CTkFrame(conn_frame, fg_color="transparent")
    url_frame.pack(fill="x", pady=5)

    ctk.CTkLabel(url_frame, text="Server URL:", width=120, anchor="w").pack(side="left")
    gui_instance.daminion_url_entry = ctk.CTkEntry(
        url_frame,
        placeholder_text="https://interiors.daminion.net"
    )
    gui_instance.daminion_url_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)
    gui_instance.daminion_url_entry.insert(
        0, str(gui_instance.config_manager.get('daminion_url', 'https://interiors.daminion.net'))
    )

    # Username
    user_frame = ctk.CTkFrame(conn_frame, fg_color="transparent")
    user_frame.pack(fill="x", pady=5)

    ctk.CTkLabel(user_frame, text="Username:", width=120, anchor="w").pack(side="left")
    gui_instance.daminion_username_entry = ctk.CTkEntry(
        user_frame,
        placeholder_text="Enter username"
    )
    gui_instance.daminion_username_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)
    gui_instance.daminion_username_entry.insert(
        0, str(gui_instance.config_manager.get('daminion_username', ''))
    )

    # Password
    pass_frame = ctk.CTkFrame(conn_frame, fg_color="transparent")
    pass_frame.pack(fill="x", pady=5)

    ctk.CTkLabel(pass_frame, text="Password:", width=120, anchor="w").pack(side="left")
    gui_instance.daminion_password_entry = ctk.CTkEntry(
        pass_frame,
        placeholder_text="Enter password",
        show="*"
    )
    gui_instance.daminion_password_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

    # Pre-fill password (Registry)
    saved_pwd = gui_instance.settings_manager.load_daminion_password_from_registry()
    if saved_pwd:
         gui_instance.daminion_password_entry.insert(0, saved_pwd)

    # Connect button and status
    connect_frame = ctk.CTkFrame(gui_instance.daminion_section, fg_color="transparent")
    connect_frame.pack(fill="x", padx=40, pady=(10, 15))

    gui_instance.daminion_connect_button = ctk.CTkButton(
        connect_frame,
        text="🔗 Connect to Daminion",
        command=gui_instance.on_daminion_connect,
        width=160,
        height=35,
        font=ctk.CTkFont(size=12, weight="bold")
    )
    gui_instance.daminion_connect_button.pack(side="left")

    gui_instance.daminion_status_label = ctk.CTkLabel(
        connect_frame,
        text="🔴 Not connected",
        text_color="gray"
    )
    gui_instance.daminion_status_label.pack(side="left", padx=(20, 0))

    # Status indicator
    gui_instance.step1_status = ctk.CTkLabel(
        main_frame,
        text="✅ Step 1: Ready to select image source",
        text_color="green"
    )
    gui_instance.step1_status.pack(anchor="w")


def create_step2_model(parent, gui_instance):
    """Create Step 2: Select AI Model widgets using CustomTkinter.

    Args:
        parent: Parent widget (tab)
        gui_instance: Reference to main GUI instance
    """
    # Main frame with modern styling
    main_frame = ctk.CTkFrame(parent, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Title with icon
    title_label = ctk.CTkLabel(
        main_frame,
        text="🤖 Select AI Model",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    title_label.pack(anchor="w", pady=(0, 15))

    # Task selection section
    task_section = ctk.CTkFrame(main_frame)
    task_section.pack(fill="x", pady=(0, 20))

    task_label = ctk.CTkLabel(
        task_section,
        text="Choose the type of AI analysis:",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    task_label.pack(anchor="w", padx=20, pady=(15, 10))

    # Model task selection
    task_frame = ctk.CTkFrame(task_section, fg_color="transparent")
    task_frame.pack(fill="x", padx=40, pady=(0, 15))

    ctk.CTkLabel(task_frame, text="Analysis Type:", width=120, anchor="w", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 10))
    
    # Initialize task variable
    last_task = gui_instance.config_manager.get('last_model_task', config.MODEL_TASK_IMAGE_CLASSIFICATION)
    # Ensure default is Keywords/Classification
    if last_task not in config.TASK_DISPLAY_MAP:
        last_task = config.MODEL_TASK_IMAGE_CLASSIFICATION
        
    display_task = config.TASK_DISPLAY_MAP.get(last_task, "Keywords (Auto)")
    gui_instance.model_task = ctk.StringVar(value=display_task)

    # Radio Buttons for Task
    r1 = ctk.CTkRadioButton(
        task_frame, 
        text="Auto-Tagging (Keywords)", 
        variable=gui_instance.model_task, 
        value="Keywords (Auto)",
        command=gui_instance.on_model_task_change
    )
    r1.pack(anchor="w", pady=5, padx=20)
    
    r2 = ctk.CTkRadioButton(
        task_frame, 
        text="Categorization (Custom)", 
        variable=gui_instance.model_task, 
        value="Categories (Custom)",
        command=gui_instance.on_model_task_change
    )
    r2.pack(anchor="w", pady=5, padx=20)
    
    r3 = ctk.CTkRadioButton(
        task_frame, 
        text="Captioning (Description)", 
        variable=gui_instance.model_task, 
        value="Description",
        command=gui_instance.on_model_task_change
    )
    r3.pack(anchor="w", pady=5, padx=20)

    # Task description
    gui_instance.task_description = ctk.CTkLabel(
        task_section,
        text="",
        wraplength=600,
        text_color="gray"
    )
    gui_instance.task_description.pack(anchor="w", padx=40, pady=(5, 15))

    # Processing Mode Selection (Local vs Cloud)
    mode_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    mode_frame.pack(fill="x", padx=40, pady=(0, 15))
    
    ctk.CTkLabel(mode_frame, text="Processing Mode:", width=120, anchor="w").pack(side="left")
    
    gui_instance.inference_mode_var = ctk.StringVar(value="local")
    gui_instance.inference_mode_selector = ctk.CTkSegmentedButton(
        mode_frame,
        values=["Local (Offline)", "Cloud (HF API)"],
        variable=gui_instance.inference_mode_var,
        command=gui_instance.on_inference_mode_change
    )
    gui_instance.inference_mode_selector.pack(side="left", padx=(10, 0), fill="x", expand=True)

    # Cloud Configuration Section (Initially Hidden)
    gui_instance.cloud_config_frame = ctk.CTkFrame(main_frame)
    # Don't pack initially, shown by handler if mode is cloud
    
    cloud_label = ctk.CTkLabel(
        gui_instance.cloud_config_frame,
        text="☁️ Cloud API Configuration",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    cloud_label.pack(anchor="w", padx=20, pady=(15, 10))
    
    # API Token Input
    token_frame = ctk.CTkFrame(gui_instance.cloud_config_frame, fg_color="transparent")
    token_frame.pack(fill="x", padx=40, pady=(0, 10))
    
    ctk.CTkLabel(token_frame, text="HF API Token:", width=120, anchor="w").pack(side="left")
    gui_instance.api_token_entry = ctk.CTkEntry(
        token_frame,
        placeholder_text="hf_...",
        show="*"
    )
    gui_instance.api_token_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)
    
    # Pre-fill token if available (from Registry via settings_manager)
    saved_token = gui_instance.settings_manager.get('hf_api_token', '')
    if saved_token:
        gui_instance.api_token_entry.insert(0, saved_token)

    # Model ID Input
    model_id_frame = ctk.CTkFrame(gui_instance.cloud_config_frame, fg_color="transparent")
    model_id_frame.pack(fill="x", padx=40, pady=(0, 15))
    
    ctk.CTkLabel(model_id_frame, text="Model ID:", width=120, anchor="w").pack(side="left")
    gui_instance.cloud_model_entry = ctk.CTkComboBox(
        model_id_frame,
        values=[
            "google/siglip-base-patch16-224", 
            "microsoft/resnet-50", 
            "nlpconnect/vit-gpt2-image-captioning",
            "openai/clip-vit-large-patch14"
        ],
        width=300
    )
    gui_instance.cloud_model_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)
    gui_instance.cloud_model_entry.set("google/siglip-base-patch16-224")

    # Test Connection Button
    test_btn_frame = ctk.CTkFrame(gui_instance.cloud_config_frame, fg_color="transparent")
    test_btn_frame.pack(fill="x", padx=40, pady=(0, 15))
    
    gui_instance.test_api_button = ctk.CTkButton(
        test_btn_frame,
        text="📡 Test API Connection",
        command=gui_instance.on_test_api_connection,
        width=160
    )
    gui_instance.test_api_button.pack(side="left")
    
    gui_instance.api_status_label = ctk.CTkLabel(
        test_btn_frame,
        text="",
        text_color="gray"
    )
    gui_instance.api_status_label.pack(side="left", padx=(15, 0))

    # Model search section (Renamed/wrapped to be togglable)
    gui_instance.local_model_search_section = ctk.CTkFrame(main_frame, fg_color="transparent")
    gui_instance.local_model_search_section.pack(fill="x", pady=(0, 20))
    # We will repack the search content into this frame or just control visibility of the frame below
    
    search_section = gui_instance.local_model_search_section # Use this as the parent for existing search code

    search_label = ctk.CTkLabel(
        search_section,
        text="🔍 Find and Load AI Models",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    search_label.pack(anchor="w", padx=20, pady=(15, 10))

    # Search and load buttons
    search_frame = ctk.CTkFrame(search_section, fg_color="transparent")
    search_frame.pack(fill="x", padx=40, pady=(0, 15))

    # Search Entry
    gui_instance.model_search_entry = ctk.CTkEntry(
        search_frame,
        placeholder_text="Filter models (e.g. 'resnet', 'blip')...",
        width=250
    )
    gui_instance.model_search_entry.pack(side="left", padx=(0, 10))

    gui_instance.find_models_button = ctk.CTkButton(
        search_frame,
        text="🔍 Find Models",
        command=gui_instance.on_find_models,
        width=120,
        height=35
    )
    gui_instance.find_models_button.pack(side="left", padx=(0, 10))

    gui_instance.set_token_button = ctk.CTkButton(
        search_frame,
        text="🔑 Set Token",
        command=gui_instance.on_set_hf_token,
        width=100,
        height=35
    )
    gui_instance.set_token_button.pack(side="left", padx=(0, 10))

    gui_instance.load_model_button = ctk.CTkButton(
        search_frame,
        text="📥 Load Selected Model",
        command=gui_instance.on_load_model,
        width=160,
        height=35,
        state="disabled"
    )
    gui_instance.load_model_button.pack(side="left")

    # Model list section
    model_section = ctk.CTkFrame(main_frame)
    model_section.pack(fill="both", expand=True, pady=(0, 20))

    model_label = ctk.CTkLabel(
        model_section,
        text="📋 Available Models",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    model_label.pack(anchor="w", padx=20, pady=(15, 10))

    # Model list with scrollbar
    model_list_frame = ctk.CTkFrame(model_section, fg_color="transparent")
    model_list_frame.pack(fill="both", expand=True, padx=40, pady=(0, 15))

    # Variable to track selected model
    gui_instance.selected_model_var = ctk.StringVar(value="")

    # Create scrollable frame for models
    gui_instance.model_listbox = ctk.CTkScrollableFrame(model_list_frame, height=200)
    gui_instance.model_listbox.pack(fill="both", expand=True)

    # Model info section
    info_section = ctk.CTkFrame(main_frame)
    info_section.pack(fill="x", pady=(0, 20))

    info_label = ctk.CTkLabel(
        info_section,
        text="ℹ️ Model Information",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    info_label.pack(anchor="w", padx=20, pady=(15, 10))

    # Model progress bar
    gui_instance.model_progress_bar = ctk.CTkProgressBar(info_section)
    gui_instance.model_progress_bar.pack(fill="x", padx=40, pady=(0, 10))
    gui_instance.model_progress_bar.set(0)

    gui_instance.model_progress_label = ctk.CTkLabel(
        info_section,
        text="No model loaded",
        text_color="gray"
    )
    gui_instance.model_progress_label.pack(anchor="w", padx=40, pady=(0, 15))

    # Model details text
    gui_instance.model_info_text = ctk.CTkTextbox(
        info_section,
        height=100
    )
    gui_instance.model_info_text.pack(fill="x", padx=40, pady=(0, 15))

    # Status indicator
    gui_instance.step2_status = ctk.CTkLabel(
        main_frame,
        text="✅ Step 2: Ready to select AI model",
        text_color="green"
    )
    gui_instance.step2_status.pack(anchor="w")

    # Update task description initially
    try:
        import gui_handlers_modern as gui_handlers
        gui_handlers.update_task_description(gui_instance)
    except ImportError:
        pass  # Will be updated later when handlers are loaded


def create_step3_config(parent, gui_instance):
    """Create Step 3: Configure Tagging widgets using CustomTkinter.

    Args:
        parent: Parent widget (tab)
        gui_instance: Reference to main GUI instance
    """
    # Main frame with modern styling
    main_frame = ctk.CTkFrame(parent, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Title with icon
    title_label = ctk.CTkLabel(
        main_frame,
        text="⚙️ Configure Tagging",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    title_label.pack(anchor="w", pady=(0, 15))

    # Categories section (for classification tasks) - conditionally visible
    gui_instance.categories_section = ctk.CTkFrame(main_frame)

    cat_label = ctk.CTkLabel(
        gui_instance.categories_section,
        text="📝 Categories (for Image Classification)",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    cat_label.pack(anchor="w", padx=20, pady=(15, 10))

    cat_frame = ctk.CTkFrame(gui_instance.categories_section, fg_color="transparent")
    cat_frame.pack(fill="x", padx=40, pady=(0, 15))

    ctk.CTkLabel(cat_frame, text="Categories:", width=120, anchor="w").pack(side="left")
    gui_instance.categories_entry = ctk.CTkEntry(
        cat_frame,
        placeholder_text="e.g., Scenery, Portrait, Document (comma-separated)"
    )
    gui_instance.categories_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

    default_cats = gui_instance.config_manager.get('default_categories', 'Scenery, Portrait, Document')
    gui_instance.categories_entry.insert(0, default_cats)

    # Keywords section (for zero-shot tasks) - conditionally visible
    gui_instance.keywords_section = ctk.CTkFrame(main_frame)

    kw_label = ctk.CTkLabel(
        gui_instance.keywords_section,
        text="🔑 Keywords (for Zero-Shot Classification)",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    kw_label.pack(anchor="w", padx=20, pady=(15, 10))

    kw_frame = ctk.CTkFrame(gui_instance.keywords_section, fg_color="transparent")
    kw_frame.pack(fill="x", padx=40, pady=(0, 15))

    ctk.CTkLabel(kw_frame, text="Keywords:", width=120, anchor="w").pack(side="left")
    gui_instance.keywords_entry = ctk.CTkEntry(
        kw_frame,
        placeholder_text="e.g., sunset, beach, car, dog (comma-separated)"
    )
    gui_instance.keywords_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

    default_kw = gui_instance.config_manager.get('default_keywords', 'sunset, beach, car, dog')
    gui_instance.keywords_entry.insert(0, default_kw)

    # Scope selection (for Daminion)
    scope_section = ctk.CTkFrame(main_frame)
    scope_section.pack(fill="x", pady=(0, 20))

    scope_label = ctk.CTkLabel(
        scope_section,
        text="🎯 Processing Scope",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    scope_label.pack(anchor="w", padx=20, pady=(15, 10))

    # Row 1: Scope dropdown (full width)
    scope_row1 = ctk.CTkFrame(scope_section, fg_color="transparent")
    scope_row1.pack(fill="x", padx=40, pady=(0, 10))

    ctk.CTkLabel(scope_row1, text="Scope:", width=120).pack(side="left")
    gui_instance.scope_var = ctk.CTkOptionMenu(
        scope_row1,
        values=["All Items", "Flagged Items", "Untagged Items", "Shared Collection"],
        width=400
    )
    gui_instance.scope_var.pack(side="left", padx=(10, 0), fill="x", expand=True)
    gui_instance.scope_var.set("All Items")
    gui_instance.scope_var.configure(command=gui_instance.on_scope_change)

    # Row 2: Collection path (for custom collections) - will be shown/hidden dynamically
    gui_instance.collection_path_frame = ctk.CTkFrame(scope_section, fg_color="transparent")

    ctk.CTkLabel(gui_instance.collection_path_frame, text="Collection Path:", width=120).pack(side="left")
    gui_instance.collection_path = ctk.CTkEntry(
        gui_instance.collection_path_frame,
        placeholder_text="Enter collection name or path",
        width=400
    )
    gui_instance.collection_path.pack(side="left", padx=(10, 0), fill="x", expand=True)

    # Row 3: Daminion collections dropdown with refresh button
    gui_instance.daminion_collections_frame = ctk.CTkFrame(scope_section, fg_color="transparent")

    ctk.CTkLabel(gui_instance.daminion_collections_frame, text="Select Collection:", width=120).pack(side="left")
    gui_instance.daminion_collection_combo = ctk.CTkComboBox(
        gui_instance.daminion_collections_frame,
        values=["Select Collection"],
        width=300,
        state="readonly"
    )
    gui_instance.daminion_collection_combo.pack(side="left", padx=(10, 0), fill="x", expand=True)

    gui_instance.refresh_collections_btn = ctk.CTkButton(
        gui_instance.daminion_collections_frame,
        text="🔄 Refresh",
        command=gui_instance.on_refresh_collections,
        width=100,
        height=30
    )
    gui_instance.refresh_collections_btn.pack(side="left", padx=(10, 0))

    # Configuration summary
    config_section = ctk.CTkFrame(main_frame)
    config_section.pack(fill="x", pady=(0, 20))

    config_label = ctk.CTkLabel(
        config_section,
        text="⚙️ Advanced Configuration",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    config_label.pack(anchor="w", padx=20, pady=(15, 10))

    # Hardware Selection
    gui_instance.hw_frame = ctk.CTkFrame(config_section, fg_color="transparent")
    gui_instance.hw_frame.pack(fill="x", padx=40, pady=(0, 10))
    ctk.CTkLabel(gui_instance.hw_frame, text="Compute Device:", width=120, anchor="w").pack(side="left")
    
    # Check available devices using centralized helper
    import huggingface_utils
    device_info = huggingface_utils.get_device_info()
    devices = device_info["devices"]
    default_device = device_info["default"]
    
    # Log the detailed diagnostic info for debugging
    logging.info(f"Hardware Diagnostic: {device_info['debug_info']}")

    gui_instance.device_var = ctk.StringVar(value=default_device)
    gui_instance.device_selector = ctk.CTkSegmentedButton(
        gui_instance.hw_frame,
        values=devices,
        variable=gui_instance.device_var
    )
    gui_instance.device_selector.pack(side="left", padx=(10, 0), fill="x", expand=True)
    
    # Add a small diagnostic label
    diag_text = "GPU Detected" if "CUDA" in devices else "CPU Mode"
    if "CUDA" in devices:
        gpu_name = device_info["debug_info"].get("cuda_device_name", "Unknown GPU")
        diag_text = f"Using: {gpu_name}"
    
    gui_instance.device_status_label = ctk.CTkLabel(
        gui_instance.hw_frame, 
        text=diag_text, 
        font=ctk.CTkFont(size=10)
    )
    gui_instance.device_status_label.pack(side="left", padx=(10, 0))

    # Open Cache Button
    cache_btn = ctk.CTkButton(
        gui_instance.hw_frame,
        text="📂 Open Model Cache",
        width=120,
        height=30,
        fg_color="gray",
        hover_color="darkgray",
        command=lambda: os.startfile(config.HF_CACHE_DIR) if os.path.exists(config.HF_CACHE_DIR) else print("Cache dir not found")
    )
    cache_btn.pack(side="right", padx=10)

    # Defaults from Settings
    try:
        # settings_manager handles user persistence
        default_batch = gui_instance.settings_manager.get("batch_size", 1)
        default_trunc = gui_instance.settings_manager.get("truncation", True)
        default_thresh = gui_instance.settings_manager.get("confidence_threshold", 0.0)
    except Exception:
        # Fallback
        default_batch = 1
        default_trunc = True
        default_thresh = 0.0

    # Batch Size
    batch_frame = ctk.CTkFrame(config_section, fg_color="transparent")
    batch_frame.pack(fill="x", padx=40, pady=(0, 10))
    
    gui_instance.batch_size_label = ctk.CTkLabel(batch_frame, text=f"Batch Size: {default_batch}", width=120, anchor="w")
    gui_instance.batch_size_label.pack(side="left")
    
    gui_instance.batch_size_slider = ctk.CTkSlider(
        batch_frame,
        from_=1,
        to=32,
        number_of_steps=31,
        command=lambda v: gui_instance.batch_size_label.configure(text=f"Batch Size: {int(v)}")
    )
    gui_instance.batch_size_slider.pack(side="left", padx=(10, 0), fill="x", expand=True)
    gui_instance.batch_size_slider.set(default_batch)

    # Threshold & Truncation
    param_frame = ctk.CTkFrame(config_section, fg_color="transparent")
    param_frame.pack(fill="x", padx=40, pady=(0, 15))
    
    gui_instance.truncation_var = ctk.BooleanVar(value=default_trunc)
    gui_instance.truncation_check = ctk.CTkCheckBox(
        param_frame,
        text="Truncate Inputs (prevent errors on long text)",
        variable=gui_instance.truncation_var
    )
    gui_instance.truncation_check.pack(side="left")
    
    thresh_val_label = ctk.CTkLabel(param_frame, text=f"Min Score: {default_thresh:.2f}", width=120)
    thresh_val_label.pack(side="left", padx=(20, 0))
    
    # Slider with labels
    slider_container = ctk.CTkFrame(param_frame, fg_color="transparent")
    slider_container.pack(side="left", padx=10)
    
    ctk.CTkLabel(slider_container, text="Loose", font=ctk.CTkFont(size=10)).pack(side="left", padx=(0, 5))
    
    gui_instance.threshold_slider = ctk.CTkSlider(
        slider_container,
        from_=0.0,
        to=1.0,
        width=150,
        command=lambda v: thresh_val_label.configure(text=f"Min Score: {v:.2f}")
    )
    gui_instance.threshold_slider.pack(side="left")
    
    ctk.CTkLabel(slider_container, text="Strict", font=ctk.CTkFont(size=10)).pack(side="left", padx=(5, 0))
    gui_instance.threshold_slider.set(default_thresh) # Default to no filtering

    # Status indicator
    gui_instance.step3_status = ctk.CTkLabel(
        main_frame,
        text="✅ Step 3: Ready to configure tagging",
        text_color="green"
    )
    gui_instance.step3_status.pack(anchor="w")


def create_step4_process(parent, gui_instance):
    """Create Step 4: Process Images widgets using CustomTkinter.

    Args:
        parent: Parent widget (tab)
        gui_instance: Reference to main GUI instance
    """
    # Main frame with modern styling
    main_frame = ctk.CTkFrame(parent, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Title with icon
    title_label = ctk.CTkLabel(
        main_frame,
        text="▶️ Process Images",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    title_label.pack(anchor="w", pady=(0, 15))

    # Processing controls section
    control_section = ctk.CTkFrame(main_frame)
    control_section.pack(fill="x", pady=(0, 20))

    control_label = ctk.CTkLabel(
        control_section,
        text="🎮 Processing Controls",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    control_label.pack(anchor="w", padx=20, pady=(15, 10))

    # Start/Stop buttons
    button_frame = ctk.CTkFrame(control_section, fg_color="transparent")
    button_frame.pack(fill="x", padx=40, pady=(0, 15))

    gui_instance.start_button = ctk.CTkButton(
        button_frame,
        text="🚀 Start Processing",
        command=gui_instance.on_start_processing,
        width=150,
        height=40,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color="gray",
        hover_color="gray",
        state="disabled"
    )
    gui_instance.start_button.pack(side="left", padx=(0, 15))

    gui_instance.stop_button = ctk.CTkButton(
        button_frame,
        text="⏹️ Stop Processing",
        command=gui_instance.on_stop_processing,
        width=120,
        height=40,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color="red",
        hover_color="darkred",
        state="disabled"
    )
    gui_instance.stop_button.pack(side="left")

    # Log Output Section
    log_section = ctk.CTkFrame(main_frame)
    log_section.pack(fill="both", expand=True, pady=(0, 20))
    
    log_label = ctk.CTkLabel(
        log_section,
        text="📜 Execution Log",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    log_label.pack(anchor="w", padx=20, pady=(10, 5))
    
    gui_instance.log_box = ctk.CTkTextbox(
        log_section,
        font=ctk.CTkFont(family="Consolas", size=11)
    )
    gui_instance.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    gui_instance.log_box.configure(state="disabled")

    # Status indicator
    gui_instance.step4_status = ctk.CTkLabel(
        main_frame,
        text="✅ Step 4: Ready to start processing",
        text_color="green"
    )
    gui_instance.step4_status.pack(anchor="w")


def create_progress_section(parent, gui_instance):
    """Create progress section at bottom of main window.

    Args:
        parent: Parent widget
        gui_instance: Reference to main GUI instance
    """
    # Progress section frame
    progress_frame = ctk.CTkFrame(parent, height=120)
    progress_frame.pack(fill="x", padx=20, pady=(0, 20))
    progress_frame.pack_propagate(False)  # Fixed height

    # Title
    progress_title = ctk.CTkLabel(
        progress_frame,
        text="📊 Processing Progress",
        font=ctk.CTkFont(size=16, weight="bold")
    )
    progress_title.pack(anchor="w", padx=20, pady=(15, 10))

    # Progress bar and status
    status_frame = ctk.CTkFrame(progress_frame, fg_color="transparent")
    status_frame.pack(fill="x", padx=40, pady=(0, 10))

    gui_instance.progress_bar = ctk.CTkProgressBar(status_frame)
    gui_instance.progress_bar.pack(fill="x", pady=(0, 5))
    gui_instance.progress_bar.set(0)

    # Status labels
    label_frame = ctk.CTkFrame(progress_frame, fg_color="transparent")
    label_frame.pack(fill="x", padx=40, pady=(0, 15))

    gui_instance.progress_label = ctk.CTkLabel(
        label_frame,
        text="Ready to process images"
    )
    gui_instance.progress_label.pack(side="left")

    gui_instance.time_label = ctk.CTkLabel(
        label_frame,
        text="⏱️ Time: 0.0s",
        text_color="gray"
    )
    gui_instance.time_label.pack(side="right")

    # Status indicator
    gui_instance.status_label = ctk.CTkLabel(
        progress_frame,
        text="🟢 Application ready",
        text_color="green"
    )
    gui_instance.status_label.pack(anchor="w", padx=40)