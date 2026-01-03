"""
Modern event handlers and helper functions for the CustomTkinter Image Tagger.
Contains UI state management and user interaction logic adapted for modern UI.
"""

import logging
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import config

# Import CustomTkinter for modern dialogs
import customtkinter as ctk


def _check_flagged_keywords(text):
    """Check if text contains flagged keywords.

    Args:
        text: Text to check

    Returns:
        True if text contains flag/reject keywords
    """
    if not text:
        return False
    text_lower = str(text).lower()
    return any(keyword in text_lower for keyword in ['flag', 'reject', 'rejected'])


def filter_local_images(all_images, scope, collection_path=None):
    """Return a filtered list of local image Path objects according to scope.

    Args:
        all_images: List of all image paths
        scope: 'collection' | 'flagged' | 'untagged'
        collection_path: Path object pointing to a sub-folder when scope == 'collection'

    Returns:
        Filtered list of image paths
    """
    if scope == 'collection':
        if collection_path is None:
            return []
        return [p for p in all_images if collection_path in p.parents or str(p).startswith(str(collection_path))]

    if scope == 'flagged':
        def is_flagged(p):
            # Check filename
            if _check_flagged_keywords(p.name):
                return True
            # Check parent directories
            for part in p.parents:
                if _check_flagged_keywords(part.name):
                    return True
            return False

        return [p for p in all_images if is_flagged(p)]

    return list(all_images)


def filter_daminion_items(items, scope, collection_name=None):
    """Return a filtered list of Daminion item dicts according to scope.

    Args:
        items: List of dicts from Daminion API
        scope: 'collection' | 'flagged' | 'untagged'
        collection_name: Substring to match when scope == 'collection'

    Returns:
        Filtered list of items
    """
    if scope == 'collection':
        if not collection_name:
            return []
        cn = collection_name.lower()
        return [it for it in items if cn in (it.get('fileName') or '').lower() or cn in str(it.get('id', '')).lower()]

    if scope == 'flagged':
        def is_flagged_item(it):
            # Check filename
            if _check_flagged_keywords(it.get('fileName')):
                return True

            # Check metadata fields
            for k in ('status', 'tags', 'keywords', 'description'):
                v = it.get(k)
                if isinstance(v, str) and _check_flagged_keywords(v):
                    return True
                if isinstance(v, list) and any(_check_flagged_keywords(x) for x in v if isinstance(x, str)):
                    return True
            return False

        return [it for it in items if is_flagged_item(it)]

    return list(items)


def scan_image_directory(image_dir):
    """Efficiently scan directory for images with all supported extensions.

    Args:
        image_dir: Path to directory to scan

    Returns:
        List of image file paths
    """
    logging.info(f"Scanning directory: {image_dir}")
    all_image_files = []

    for image_path in image_dir.rglob('*'):
        if image_path.is_file() and image_path.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
            all_image_files.append(image_path)

    logging.info(f"Found {len(all_image_files)} images")
    return all_image_files


def update_step_states(gui_instance):
    """Update visual indicators for each step with modern styling.

    Args:
        gui_instance: Reference to main GUI instance
    """
    # Step 1: Source selected?
    if gui_instance.processing_mode == "local":
        if gui_instance.image_dir:
            gui_instance.step1_status.configure(
                text="✅ Source ready: Local directory selected"
            )
        else:
            gui_instance.step1_status.configure(
                text="⚠️ Please select an image directory",
                text_color="orange"
            )
    else:
        if gui_instance.daminion_client:
            gui_instance.step1_status.configure(
                text="✅ Source ready: Connected to Daminion"
            )
        else:
            gui_instance.step1_status.configure(
                text="⚠️ Please connect to Daminion server",
                text_color="orange"
            )

    # Step 2: Model loaded?
    if gui_instance.model:
        model_name = gui_instance.model.model.name_or_path
        gui_instance.step2_status.configure(
            text=f"✅ Model loaded: {model_name}"
        )
    else:
        gui_instance.step2_status.configure(
            text="⚠️ Please search for and load a model",
            text_color="orange"
        )

    # Step 3: Configuration ready?
    try:
        display_task = gui_instance.model_task.get()
        task = config.DISPLAY_TASK_MAP.get(display_task, "")
        
        cats = gui_instance.categories_entry.get().strip()
        kws = gui_instance.keywords_entry.get().strip()
    except:
        task = ""
        cats = ""
        kws = ""

    if task == config.MODEL_TASK_IMAGE_TO_TEXT:
        gui_instance.step3_status.configure(
            text="✅ Configuration ready: Image-to-Text mode (auto)"
        )
    elif task == config.MODEL_TASK_IMAGE_CLASSIFICATION and cats:
        gui_instance.step3_status.configure(
            text="✅ Configuration ready: Categories entered"
        )
    elif task == config.MODEL_TASK_ZERO_SHOT and kws:
        gui_instance.step3_status.configure(
            text="✅ Configuration ready: Keywords entered"
        )
    else:
        gui_instance.step3_status.configure(
            text="⚠️ Please enter categories or keywords",
            text_color="orange"
        )

    # Step 4: Ready to process?
    source_ready = (gui_instance.processing_mode == "local" and gui_instance.image_dir) or \
                   (gui_instance.processing_mode == "daminion" and gui_instance.daminion_client)
    
    # Model/API Ready?
    is_cloud = hasattr(gui_instance, 'inference_mode_var') and gui_instance.inference_mode_var.get() == "Cloud (HF API)"
    if is_cloud:
        model_ready = bool(gui_instance.api_token_entry.get() and gui_instance.cloud_model_entry.get())
    else:
        model_ready = bool(gui_instance.model)

    config_ready = (task == config.MODEL_TASK_IMAGE_TO_TEXT) or \
                   (task == config.MODEL_TASK_IMAGE_CLASSIFICATION and cats) or \
                   (task == config.MODEL_TASK_ZERO_SHOT and kws)

    if source_ready and model_ready and config_ready:
        if gui_instance.start_button:
            gui_instance.start_button.configure(
                state="normal",
                fg_color="green",
                hover_color="darkgreen"
            )
        gui_instance.step4_status.configure(text="🚀 Ready to process!", text_color="green")
    else:
        if gui_instance.start_button:
            gui_instance.start_button.configure(
                state="disabled",
                fg_color="gray",
                hover_color="gray"
            )
        missing = []
        if not source_ready:
            missing.append("image source")
        if not model_ready:
            missing.append("AI model/API config")
        if not config_ready:
            missing.append("configuration")
        gui_instance.step4_status.configure(
            text=f"⚠️ Complete previous steps: {', '.join(missing)}",
            text_color="orange"
        )

    # Update configuration summary
    if hasattr(gui_instance, 'config_summary'):
        summary_text = f"""
Task: {task if task else 'Not selected'}
Categories: {cats if cats else 'Not specified'}
Keywords: {kws if kws else 'Not specified'}
Scope: {gui_instance.scope_var.get() if gui_instance.scope_var else 'Not selected'}
Source: {gui_instance.processing_mode.title()}
"""
        gui_instance.config_summary.configure(text=summary_text.strip())


def update_task_description(gui_instance):
    """Update the description based on selected task.

    Args:
        gui_instance: Reference to main GUI instance
    """
    try:
        display_task = gui_instance.model_task.get()
        task = config.DISPLAY_TASK_MAP.get(display_task, "")
        
        descriptions = {
            config.MODEL_TASK_IMAGE_CLASSIFICATION:
                "📋 Auto-detects specific objects (e.g. tree, car) using standard models. Best for general tagging.",
            
            config.MODEL_TASK_ZERO_SHOT:
                "🔍 Sorts into your defined buckets (e.g. Indoor, Outdoor). Best for broad categorization.",
            
            config.MODEL_TASK_IMAGE_TO_TEXT:
                "📝 Generates a full sentence description of the image content."
        }
        gui_instance.task_description.configure(text=descriptions.get(task, ""))
    except Exception as e:
        logging.warning(f"Could not update task description: {e}")


def update_step3_visibility(gui_instance):
    """Update visibility of Step 3 sections based on selected analysis type.

    Shows/hides Categories and Keywords sections based on the selected task:
    - Image Classification: Show Categories only
    - Zero-Shot: Show Keywords only
    - Image-to-Text: Hide both (auto-generates)

    Args:
        gui_instance: Reference to main GUI instance
    """
    try:
        task = gui_instance.model_task.get()

        # Show/hide Categories section
        if hasattr(gui_instance, 'categories_section'):
            if task == config.MODEL_TASK_IMAGE_CLASSIFICATION:
                # Pack before scope section to maintain order
                if hasattr(gui_instance, 'scope_var') and gui_instance.scope_var.master and gui_instance.scope_var.master.master:
                    gui_instance.categories_section.pack(fill="x", pady=(0, 20), before=gui_instance.scope_var.master.master)
                else:
                    gui_instance.categories_section.pack(fill="x", pady=(0, 20))
            else:
                gui_instance.categories_section.pack_forget()

        # Show/hide Keywords section
        if hasattr(gui_instance, 'keywords_section'):
            if task == config.MODEL_TASK_ZERO_SHOT:
                # Pack before scope section to maintain order
                if hasattr(gui_instance, 'scope_var') and gui_instance.scope_var.master and gui_instance.scope_var.master.master:
                    gui_instance.keywords_section.pack(fill="x", pady=(0, 20), before=gui_instance.scope_var.master.master)
                else:
                    gui_instance.keywords_section.pack(fill="x", pady=(0, 20))
            else:
                gui_instance.keywords_section.pack_forget()

        logging.debug(f"Updated Step 3 visibility for task: {task}")
    except Exception as e:
        logging.warning(f"Could not update Step 3 visibility: {e}")


def filter_models_by_task(gui_instance, task):
    """Filter the model list to show only models compatible with the selected task.

    Args:
        gui_instance: Reference to main GUI instance
        task: Selected model task type
    """
    try:
        # Get all models stored with their task info
        if not hasattr(gui_instance, 'all_models_with_tasks'):
            # If we don't have task info stored, just show all models
            logging.warning("No task information available for models, showing all")
            return

        # Filter models that support the current task
        task_models = gui_instance.all_models_with_tasks.get(task, set())

        # Update the display with filtered models
        downloaded = gui_instance.downloaded_models if hasattr(gui_instance, 'downloaded_models') else set()
        update_model_list(gui_instance, list(task_models), downloaded)

        # Update status
        cached_count = len([m for m in task_models if m in downloaded])
        cloud_count = len(task_models) - cached_count

        if gui_instance.status_label:
            if task_models:
                gui_instance.status_label.configure(
                    text=f"ℹ️ Showing {len(task_models)} models for {task} ({cached_count} cached, {cloud_count} cloud)"
                )
            else:
                gui_instance.status_label.configure(
                    text=f"ℹ️ No cached models for {task}. Click 'Find Models' to search HuggingFace."
                )

        logging.info(f"Filtered to {len(task_models)} models for task: {task}")
    except Exception as e:
        logging.error(f"Failed to filter models by task: {e}")


def calculate_time_remaining(gui_instance, completed, total):
    """Calculate estimated time remaining.

    Args:
        gui_instance: Reference to main GUI instance
        completed: Number of items completed
        total: Total number of items

    Returns:
        Formatted string with time remaining
    """
    if not gui_instance.processing_start_time or completed == 0:
        return ""

    elapsed = time.time() - gui_instance.processing_start_time
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


def on_model_task_change(gui_instance, event=None):
    """Handle model task selection change.

    Filters existing model list instead of re-fetching from HuggingFace.
    Updates Step 3 visibility based on selected task.

    Args:
        gui_instance: Reference to main GUI instance
        event: Tkinter event (optional)
    """
    update_task_description(gui_instance)
    update_step3_visibility(gui_instance)
    update_step_states(gui_instance)

    # Filter existing model list by task instead of re-fetching
    try:
        display_task = gui_instance.model_task.get()
        task = config.DISPLAY_TASK_MAP.get(display_task, "")
        logging.info(f"Model task changed to: {task} (Display: {display_task})")

        # Update Dynamic Cloud Model Suggestions
        if hasattr(gui_instance, 'cloud_model_entry'):
            suggestions = {
                config.MODEL_TASK_IMAGE_CLASSIFICATION: [
                    "google/vit-base-patch16-224",
                    "microsoft/resnet-50", 
                    "facebook/deit-base-distilled-patch16-224"
                ],
                config.MODEL_TASK_IMAGE_TO_TEXT: [
                    "nlpconnect/vit-gpt2-image-captioning",
                    "Salesforce/blip-image-captioning-base",
                    "microsoft/git-base"
                ],
                config.MODEL_TASK_ZERO_SHOT: [
                     "openai/clip-vit-base-patch32",
                     "openai/clip-vit-large-patch14"
                ]
            }
            new_values = suggestions.get(task, ["google/vit-base-patch16-224"])
            gui_instance.cloud_model_entry.configure(values=new_values)
            
            # Reset to first default if current is not valid/custom
            current_val = gui_instance.cloud_model_entry.get()
            # If current value is empty or one of the defaults from *another* task, switch it.
            # Simple heuristic: always switch to default of new task to guide user
            gui_instance.cloud_model_entry.set(new_values[0])

        # If we have models already loaded, filter them by the new task
        if hasattr(gui_instance, 'all_models') and gui_instance.all_models:
            filter_models_by_task(gui_instance, task)
        else:
            # No models loaded yet, show placeholder message
            if gui_instance.status_label:
                gui_instance.status_label.configure(
                    text="ℹ️ Click 'Find Models' to search for compatible models"
                )
    except Exception as e:
        logging.error(f"Failed to filter models after task change: {e}")




def on_mode_change(gui_instance, mode):
    """Handle source mode change (Local vs Daminion).
    
    Args:
        gui_instance: Reference to main GUI instance
        mode: Selected mode ('local' or 'daminion')
    """
    logging.info(f"Switching source mode to: {mode}")
    gui_instance.processing_mode = mode
    
    if mode == "local":
        # Hide Daminion section
        if hasattr(gui_instance, 'daminion_section'):
            gui_instance.daminion_section.pack_forget()
        
        # Show Local section
        if hasattr(gui_instance, 'local_section'):
            # Pack before status label to maintain order
            if hasattr(gui_instance, 'step1_status'):
                gui_instance.local_section.pack(fill="x", pady=(0, 20), before=gui_instance.step1_status)
            else:
                gui_instance.local_section.pack(fill="x", pady=(0, 20))

        if gui_instance.step1_status:
            gui_instance.step1_status.configure(text="✅ Step 1: Ready to select image source", text_color="green")
            
    elif mode == "daminion":
        # Hide Local section
        if hasattr(gui_instance, 'local_section'):
            gui_instance.local_section.pack_forget()
            
        # Show Daminion section
        if hasattr(gui_instance, 'daminion_section'):
             if hasattr(gui_instance, 'step1_status'):
                 gui_instance.daminion_section.pack(fill="x", padx=20, pady=(0, 20), before=gui_instance.step1_status)
             else:
                 gui_instance.daminion_section.pack(fill="x", padx=20, pady=(0, 20))
            
        if gui_instance.step1_status:
             gui_instance.step1_status.configure(text="ℹ️ Enter Daminion server details", text_color="blue")
    
    update_step_states(gui_instance)


def on_inference_mode_change(gui_instance, mode_value=None):
    """Handle inference mode change (Local vs Cloud).
    
    Args:
        gui_instance: Reference to main GUI instance
        mode_value: Passed by SegmentedButton (optional)
    """
    mode = gui_instance.inference_mode_var.get()
    
    # Toggle sections
    if mode == "Cloud (HF API)":
        # Cloud Mode
        # Hide local model search frames first to avoid conflict
        if hasattr(gui_instance, 'local_model_search_section'):
            gui_instance.local_model_search_section.pack_forget()

        # Show Cloud Config
        # Pack after the mode selector to ensure correct order
        if hasattr(gui_instance, 'inference_mode_selector') and gui_instance.inference_mode_selector.master:
             gui_instance.cloud_config_frame.pack(fill="x", padx=40, pady=(0, 20), after=gui_instance.inference_mode_selector.master)
        else:
             gui_instance.cloud_config_frame.pack(fill="x", padx=40, pady=(0, 20))
        
        # Hide model listbox if we want to force API usage
        # (Optional: keep it if we want to allow hybrid, but sticking to design)
        # gui_instance.model_section... (Leaving standard list visible for reference)

        update_step_states(gui_instance)
        
    else:
        # Local Mode
        if hasattr(gui_instance, 'cloud_config_frame'):
            gui_instance.cloud_config_frame.pack_forget()
            
        if hasattr(gui_instance, 'local_model_search_section'):
             # Restore search section
             if hasattr(gui_instance, 'inference_mode_selector') and gui_instance.inference_mode_selector.master:
                 gui_instance.local_model_search_section.pack(fill="x", pady=(0, 20), after=gui_instance.inference_mode_selector.master)
             else:
                 gui_instance.local_model_search_section.pack(fill="x", pady=(0, 20))
        
        update_step_states(gui_instance)


def on_test_api_connection(gui_instance):
    """Validates the HF Token and Model ID for API access.
    """
    token = gui_instance.api_token_entry.get().strip()
    model_id = gui_instance.cloud_model_entry.get().strip()
    
    if not token:
        show_modern_messagebox(gui_instance, "Missing Token", "Please enter a Hugging Face API Token.", "warning")
        return

    if not model_id:
        show_modern_messagebox(gui_instance, "Missing Model ID", "Please enter a Model ID.", "warning")
        return
        
    gui_instance.test_api_button.configure(state="disabled", text="Testing...")
    gui_instance.api_status_label.configure(text="Connecting...", text_color="blue")
    
    # We can do this in a quick inline thread or worker
    def _test():
        try:
             from huggingface_hub import InferenceClient
             client = InferenceClient(token=token)
             
             # Simple non-inference check (get model info) or a tiny inference?
             # get_model_info verifies readability.
             from huggingface_hub import HfApi
             api = HfApi(token=token)
             info = api.model_info(model_id)
             
             # Check if pipeline tag matches expected if possible
             # But generic 'post' works for all.
             
             # Success
             # Save to Registry on success
             gui_instance.settings_manager.save_api_key_to_registry(token)
             gui_instance.q.put({'type': 'api_test_result', 'success': True, 'msg': f"Model found: {info.pipeline_tag}"})
             
        except Exception as e:
             gui_instance.q.put({'type': 'api_test_result', 'success': False, 'msg': str(e)})

    thread = threading.Thread(target=_test, daemon=True)
    thread.start()

# Handlers for API testing need to be added to the queue processor in main, 
# but we can hack it for now or rely on generic status updates.
# Wait, gui_main needs to know how to handle 'api_test_result'.
# We should update gui_handlers.check_queue or just handle it here if passed via some callback?
# Standard pattern is queue.


def on_scope_change(gui_instance, event=None):
    """Handle scope change for Daminion collections.

    Args:
        gui_instance: Reference to main GUI instance
        event: Tkinter event (optional)
    """
    try:
        scope = gui_instance.scope_var.get()

        # Show/hide collection path frame based on scope
        if hasattr(gui_instance, 'collection_path_frame'):
            if scope == "Custom Collection":
                gui_instance.collection_path_frame.pack(fill="x", padx=40, pady=(0, 10))
            else:
                gui_instance.collection_path_frame.pack_forget()

            # Show/hide Daminion collections dropdown
            if hasattr(gui_instance, 'daminion_collections_frame'):
                 if scope == "Shared Collection":
                     gui_instance.daminion_collections_frame.pack(fill="x", padx=40, pady=(0, 10))
                 else:
                     gui_instance.daminion_collections_frame.pack_forget()
        else:
            # Legacy support: fall back to individual widget
            if scope == "Custom Collection":
                gui_instance.collection_path.pack(side="left", padx=(10, 0))
            else:
                gui_instance.collection_path.pack_forget()
            
            # Legacy dropdown support
            if hasattr(gui_instance, 'daminion_collection_combo'):
                if scope == "Shared Collection":
                    gui_instance.daminion_collection_combo.pack(side="left", padx=(10, 0))
                    if hasattr(gui_instance, 'refresh_collections_btn'):
                        gui_instance.refresh_collections_btn.pack(side="left", padx=(10, 0))
                else:
                    gui_instance.daminion_collection_combo.pack_forget()
                    if hasattr(gui_instance, 'refresh_collections_btn'):
                        gui_instance.refresh_collections_btn.pack_forget()

        # Update processing info
        if hasattr(gui_instance, 'processing_info_label'):
            info_text = f"Ready to process {scope.lower()} from {'Daminion' if gui_instance.processing_mode == 'daminion' else 'local directory'}"
            gui_instance.processing_info_label.configure(text=info_text)

        update_step_states(gui_instance)
    except Exception as e:
        logging.warning(f"Could not handle scope change: {e}")


def show_modern_messagebox(gui_instance, title, message, msg_type="info"):
    """Show a modern message dialog using CustomTkinter.

    Args:
        gui_instance: Reference to main GUI instance
        title: Dialog title
        message: Dialog message
        msg_type: "info", "warning", "error", "success"
    """
    dialog = ctk.CTkToplevel(gui_instance)
    dialog.title(title)
    dialog.geometry("400x200")
    dialog.transient(gui_instance)
    dialog.grab_set()
    
    # Icon based on message type
    icons = {
        "info": "ℹ️",
        "warning": "⚠️", 
        "error": "❌",
        "success": "✅"
    }
    
    icon = icons.get(msg_type, "ℹ️")
    
    # Title label
    title_label = ctk.CTkLabel(
        dialog,
        text=f"{icon} {title}",
        font=ctk.CTkFont(size=16, weight="bold")
    )
    title_label.pack(pady=20)
    
    # Message label
    message_label = ctk.CTkLabel(
        dialog,
        text=message,
        wraplength=350,
        justify="center"
    )
    message_label.pack(pady=10)
    
    # Close button
    close_button = ctk.CTkButton(
        dialog,
        text="Close",
        command=dialog.destroy
    )
    close_button.pack(pady=20)


# Event handler functions (simplified versions - full implementations would be in the original handlers)
import gui_workers


def on_daminion_connect(gui_instance):
    """Handle Daminion connection button click."""
    try:
        url = gui_instance.daminion_url_entry.get().strip()
        username = gui_instance.daminion_username_entry.get().strip()
        password = gui_instance.daminion_password_entry.get().strip()
        
        if not all([url, username, password]):
            show_modern_messagebox(gui_instance, "Missing Information", "Please fill in all connection fields", "warning")
            return
        
        gui_instance.daminion_status_label.configure(text="🔄 Connecting...", text_color="blue")
        
        # Start connection in worker thread
        thread = threading.Thread(
            target=gui_workers.connect_daminion_worker,
            args=(gui_instance, url, username, password),
            daemon=True
        )
        thread.start()
        
    except Exception as e:
        logging.error(f"Daminion connection error: {e}")
        gui_instance.daminion_status_label.configure(text="🔴 Connection failed", text_color="red")





def on_find_models(gui_instance):
    """Handle find models button click."""
    try:
        gui_instance.find_models_button.configure(state="disabled", text="🔍 Searching...")
        
        # Get optional search query
        search_query = None
        if hasattr(gui_instance, 'model_search_entry'):
            q = gui_instance.model_search_entry.get().strip()
            if q:
                search_query = q

        # Start model search in worker thread
        thread = threading.Thread(
            target=gui_workers.find_models_worker,
            args=(gui_instance, search_query),
            daemon=True
        )
        thread.start()
        
    except Exception as e:
        logging.error(f"Model search error: {e}")
        gui_instance.find_models_button.configure(state="normal", text="🔍 Find Models")





def on_model_selected(gui_instance):
    """Enable Load Model button when a model is selected.

    Args:
        gui_instance: Reference to main GUI instance
    """
    if gui_instance.load_model_button and gui_instance.selected_model_var.get():
        gui_instance.load_model_button.configure(state="normal")
        logging.debug(f"Model selected: {gui_instance.selected_model_var.get()}")


def update_model_list(gui_instance, models, downloaded_models):
    """Update the model list display with cached models prioritized."""
    try:
        # Clear existing models
        for widget in gui_instance.model_listbox.winfo_children():
            widget.destroy()

        # Separate cached and cloud models
        cached_models = [m for m in models if m in downloaded_models]
        cloud_models = [m for m in models if m not in downloaded_models]
        
        all_models_to_show = cached_models + cloud_models
        auto_select_model = None

        for model_id in all_models_to_show:
            gui_instance.all_models.add(model_id)

            model_frame = ctk.CTkFrame(gui_instance.model_listbox)
            model_frame.pack(fill="x", padx=5, pady=5)

            is_cached = model_id in downloaded_models
            cached_text = "✅ Cached" if is_cached else "☁️ Cloud"
            cached_color = "green" if is_cached else ("gray", "gray")

            if is_cached and not auto_select_model:
                auto_select_model = model_id

            radio_args = {
                "text": f"{model_id}   [{cached_text}]",
                "variable": gui_instance.selected_model_var,
                "value": model_id,
                "font": ctk.CTkFont(weight="bold"),
                "command": lambda: on_model_selected(gui_instance)
            }

            if is_cached:
                radio_args["text_color"] = cached_color

            radio_btn = ctk.CTkRadioButton(model_frame, **radio_args)
            radio_btn.pack(anchor="w", padx=10, pady=(10, 5))

            description = ""
            if is_cached:
                description = f"✨ Ready to use!"

            desc_label = ctk.CTkLabel(
                model_frame,
                text=description,
                font=ctk.CTkFont(size=11),
                text_color="green" if is_cached else "gray",
                anchor="w",
                wraplength=400
            )
            desc_label.pack(fill="x", padx=35, pady=(0, 10))

        if auto_select_model:
            gui_instance.selected_model_var.set(auto_select_model)
            gui_instance.load_model_button.configure(state="normal")

        if cached_models:
            gui_instance.find_models_button.configure(
                state="normal",
                text=f"🔍 Find More Models ({len(cloud_models)} cloud)"
            )
            gui_instance.q.put({
                'type': 'status_update',
                'status': f'🚀 {len(cached_models)} cached models ready + {len(cloud_models)} cloud models available'
            })
        else:
            gui_instance.find_models_button.configure(state="normal", text="🔍 Find Models")
            gui_instance.q.put({
                'type': 'status_update',
                'status': f'Found {len(models)} models - none cached yet'
            })

        logging.info(f"Found {len(models)} models ({len(cached_models)} cached, {len(cloud_models)} cloud)")

    except Exception as e:
        logging.error(f"Failed to update model list: {e}")


def on_load_model(gui_instance):
    """Handle load model button click."""
    selected_model = gui_instance.selected_model_var.get()

    if not selected_model:
        show_modern_messagebox(
            gui_instance,
            "Model Selection",
            "Please select a model from the list above.",
            "warning"
        )
        return

    try:
        gui_instance.load_model_button.configure(
            text="⏳ Loading...",
            state="disabled"
        )
        
        # Get selected device
        device_name = gui_instance.device_var.get() if gui_instance.device_var else "CPU"
        device_map = {"CPU": -1, "CUDA": 0, "MPS": "mps"}
        device = device_map.get(device_name, -1)

        # Start model loading in worker thread
        thread = threading.Thread(
            target=gui_workers.load_model_worker,
            args=(gui_instance, selected_model, device),
            daemon=True
        )
        thread.start()

    except Exception as e:
        logging.error(f"Failed to start model loading: {e}")
        gui_instance.load_model_button.configure(
            text="📥 Load Selected Model",
            state="normal"
        )




def on_start_processing(gui_instance):
    """Handle start processing button click."""
    try:
        gui_instance.start_button.configure(
            text="⏸️ Processing...",
            state="disabled",
            fg_color="orange"
        )
        gui_instance.stop_button.configure(state="normal", fg_color="red")
        
        gui_instance.stop_event.clear()
        gui_instance.processing_start_time = time.time()
        
        # Get categories and keywords
        categories = [c.strip() for c in gui_instance.categories_entry.get().split(',') if c.strip()]
        keywords = [k.strip() for k in gui_instance.keywords_entry.get().split(',') if k.strip()]

        # Get Advanced Config
        device = gui_instance.device_var.get() if gui_instance.device_var else "CPU"
        batch_size = int(gui_instance.batch_size_slider.get()) if gui_instance.batch_size_slider else 8
        truncation = gui_instance.truncation_var.get() if gui_instance.truncation_var else True
        threshold = gui_instance.threshold_slider.get() if gui_instance.threshold_slider else 0.0

        logging.info(f"Starting processing with Device={device}, Batch={batch_size}, Trunc={truncation}, Thr={threshold}")

        # Gather Cloud/Local Params
        mode = gui_instance.inference_mode_var.get() if hasattr(gui_instance, 'inference_mode_var') else "local"
        # Convert display string "Cloud (HF API)" -> "cloud"
        mode_key = "cloud" if "Cloud" in mode else "local"
        
        token = None
        cloud_model_id = None
        
        if mode_key == "cloud":
            token = gui_instance.api_token_entry.get().strip()
            cloud_model_id = gui_instance.cloud_model_entry.get().strip()
            
            if not token or not cloud_model_id:
                show_modern_messagebox(gui_instance, "Missing Credentials", "Please enter HF Token and Model ID for Cloud mode.", "error")
                gui_instance.start_button.configure(text="🚀 Start Processing", state="normal", fg_color="green")
                gui_instance.stop_button.configure(state="disabled", fg_color="red")
                return
                
            # Allow invalid model selection check? We rely on worker to fail if so.

        # Determine target worker
        if gui_instance.processing_mode == "local":
            image_files = scan_image_directory(gui_instance.image_dir)
            target_worker = gui_workers.process_images_worker
            worker_args = (gui_instance, image_files, categories, keywords, device, batch_size, truncation, threshold, mode_key, token, cloud_model_id)
        else: # daminion
            target_worker = gui_workers.process_daminion_worker
            
            # Extract scope and collection ID
            scope = gui_instance.scope_var.get()
            collection_id = None
            
            if scope == "Shared Collection":
                # Extract ID from combo "Name (ID)"
                selection = gui_instance.daminion_collection_combo.get()
                if selection:
                    # Robust parsing of "Name (ID)" format
                    import re
                    match = re.search(r'\(([^)]+)\)$', selection)
                    if match:
                        collection_id = match.group(1)
                    else:
                        # Fallback for simple ID or unexpected format
                        collection_id = selection
                        logging.warning(f"Could not parse ID from selection '{selection}', using as-is.")
                else:
                    show_modern_messagebox(gui_instance, "Missing Selection", "Please select a shared collection.", "warning")
                    gui_instance.start_button.configure(text="🚀 Start Processing", state="normal", fg_color="green")
                    gui_instance.stop_button.configure(state="disabled", fg_color="red")
                    return
            
            worker_args = (gui_instance, categories, keywords, None, device, batch_size, truncation, threshold, collection_id, mode_key, token, cloud_model_id)


        # Start processing in worker thread
        thread = threading.Thread(
            target=target_worker,
            args=worker_args,
            daemon=True
        )
        thread.start()
        
    except Exception as e:
        logging.error(f"Failed to start processing: {e}")





def on_stop_processing(gui_instance):
    """Handle stop processing button click."""
    gui_instance.stop_event.set()
    gui_instance.start_button.configure(
        text="🚀 Start Processing",
        state="normal",
        fg_color="green"
    )
    gui_instance.stop_button.configure(state="disabled", fg_color="red")


def on_select_directory(gui_instance):
    """Handle directory selection."""
    try:
        directory = filedialog.askdirectory(title="Select Image Directory")
        if directory:
            gui_instance.image_dir = Path(directory)
            gui_instance.dir_label.configure(text=str(directory))
            update_step_states(gui_instance)
            
    except Exception as e:
        logging.error(f"Directory selection error: {e}")


def on_refresh_collections(gui_instance):
    """Handle refresh collections button click (Async)."""
    try:
        if not gui_instance.daminion_client:
            show_modern_messagebox(gui_instance, "Connection Required", "Please connect to Daminion first.", "warning")
            return

        # Disable button to prevent spamming
        if gui_instance.refresh_collections_btn:
            gui_instance.refresh_collections_btn.configure(state="disabled", text="Refreshing...")

        # Start refresh in worker thread
        thread = threading.Thread(
            target=gui_workers.refresh_daminion_collections_worker,
            args=(gui_instance,),
            daemon=True
        )
        thread.start()
        
    except Exception as e:
        logging.error(f"Collection refresh error: {e}")
        if gui_instance.refresh_collections_btn:
            gui_instance.refresh_collections_btn.configure(state="normal", text="🔄 Refresh")


# Menu functions
def show_cache_path(gui_instance):
    """Show cache path information."""
    from huggingface_utils import get_cache_dir
    cache_path = get_cache_dir()
    show_modern_messagebox(
        gui_instance,
        "Cache Location",
        f"Model cache location: {cache_path}",
        "info"
    )


def clear_cache(gui_instance):
    """Clear the model cache."""
    result = messagebox.askyesno(
        "Clear Cache",
        "Are you sure you want to clear the model cache?\n\nThis will delete all downloaded models and require re-downloading."
    )
    
    if result:
        try:
            from huggingface_utils import clear_cache
            clear_cache()
            show_modern_messagebox(
                gui_instance,
                "Cache Cleared",
                "Model cache has been cleared successfully.",
                "success"
            )
        except Exception as e:
            logging.error(f"Cache clearing error: {e}")
            show_modern_messagebox(
                gui_instance,
                "Error",
                f"Failed to clear cache: {e}",
                "error"
            )


def export_report_csv(gui_instance):
    """Export processing report to CSV."""
    try:
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            gui_instance.report.export_csv(filename)
            show_modern_messagebox(
                gui_instance,
                "Export Complete",
                f"Report exported to {filename}",
                "success"
            )
    except Exception as e:
        logging.error(f"CSV export error: {e}")


def export_report_json(gui_instance):
    """Export processing report to JSON."""
    try:
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            gui_instance.report.export_json(filename)
            show_modern_messagebox(
                gui_instance,
                "Export Complete",
                f"Report exported to {filename}",
                "success"
            )
    except Exception as e:
        logging.error(f"JSON export error: {e}")


def show_report_summary(gui_instance):
    """Show processing report summary."""
    summary = gui_instance.report.get_summary()
    show_modern_messagebox(
        gui_instance,
        "Report Summary",
        f"Total processed: {summary.get('total', 0)}\nSuccessful: {summary.get('successful', 0)}\nFailed: {summary.get('failed', 0)}",
        "info"
    )

def set_hf_token(gui_instance):
    """Dialog to set the Hugging Face API token (Modern)."""
    current_token = gui_instance.config_manager.get('hf_token') or ""
    dialog = ctk.CTkInputDialog(
        text="Enter your Hugging Face API Token (Read access):", 
        title="Hugging Face API Token"
    )
    token = dialog.get_input()
    
    if token is not None:
        gui_instance.config_manager.set('hf_token', token.strip() if token.strip() else None)
        gui_instance.config_manager.save_config()
        show_modern_messagebox(gui_instance, "Token Saved", "API Token updated successfully.", "success")