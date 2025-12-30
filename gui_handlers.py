"""
Event handlers and helper functions for the Image Tagger application.
Contains UI state management and user interaction logic.
"""

import logging
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path
import config


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
            name = p.name.lower()
            if 'flag' in name or 'reject' in name or 'rejected' in name:
                return True
            for part in p.parents:
                pn = part.name.lower()
                if 'flag' in pn or 'reject' in pn or 'rejected' in pn:
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
    """Update visual indicators for each step.

    Args:
        gui_instance: Reference to main GUI instance
    """
    # Step 1: Source selected?
    if gui_instance.processing_mode == "local":
        if gui_instance.image_dir:
            gui_instance.step1_status.config(
                text="[OK] Source ready: Local directory selected", foreground="green"
            )
        else:
            gui_instance.step1_status.config(
                text="[WARN] Please select an image directory", foreground="orange"
            )
    else:
        if gui_instance.daminion_client:
            gui_instance.step1_status.config(
                text="[OK] Source ready: Connected to Daminion", foreground="green"
            )
        else:
            gui_instance.step1_status.config(
                text="[WARN] Please connect to Daminion server", foreground="orange"
            )

    # Step 2: Model loaded?
    if gui_instance.model:
        model_name = gui_instance.model.model.name_or_path
        gui_instance.step2_status.config(
            text=f"[OK] Model loaded: {model_name}", foreground="green"
        )
    else:
        gui_instance.step2_status.config(
            text="[WARN] Please search for and load a model", foreground="orange"
        )

    # Step 3: Configuration ready?
    task = gui_instance.model_task.get()
    cats = gui_instance.categories_entry.get().strip()
    kws = gui_instance.keywords_entry.get().strip()

    if task == config.MODEL_TASK_IMAGE_TO_TEXT:
        gui_instance.step3_status.config(
            text="[OK] Configuration ready: Image-to-Text mode (auto)", foreground="green"
        )
    elif task == config.MODEL_TASK_IMAGE_CLASSIFICATION and cats:
        gui_instance.step3_status.config(
            text="[OK] Configuration ready: Categories entered", foreground="green"
        )
    elif task == config.MODEL_TASK_ZERO_SHOT and kws:
        gui_instance.step3_status.config(
            text="[OK] Configuration ready: Keywords entered", foreground="green"
        )
    else:
        gui_instance.step3_status.config(
            text="[WARN] Please enter categories or keywords", foreground="orange"
        )

    # Step 4: Ready to process?
    source_ready = (gui_instance.processing_mode == "local" and gui_instance.image_dir) or \
                  (gui_instance.processing_mode == "daminion" and gui_instance.daminion_client)
    config_ready = (task == config.MODEL_TASK_IMAGE_TO_TEXT) or \
                  (task == config.MODEL_TASK_IMAGE_CLASSIFICATION and cats) or \
                  (task == config.MODEL_TASK_ZERO_SHOT and kws)

    if source_ready and gui_instance.model and config_ready:
        gui_instance.start_button.config(state="normal")
        gui_instance.step4_status.config(text="[OK] Ready to process!", foreground="green")
    else:
        gui_instance.start_button.config(state="disabled")
        missing = []
        if not source_ready:
            missing.append("image source")
        if not gui_instance.model:
            missing.append("AI model")
        if not config_ready:
            missing.append("configuration")
        gui_instance.step4_status.config(
            text=f"[WARN] Complete previous steps: {', '.join(missing)}", foreground="orange"
        )


def update_task_description(gui_instance):
    """Update the description based on selected task.

    Args:
        gui_instance: Reference to main GUI instance
    """
    task = gui_instance.model_task.get()
    descriptions = {
        config.MODEL_TASK_IMAGE_CLASSIFICATION:
            "📋 Assigns ONE category to each image from your predefined list (e.g., Interior, Exterior, Furniture)",
        config.MODEL_TASK_ZERO_SHOT:
            "🏷️  Detects MULTIPLE keywords from your list with confidence >90% (e.g., bedroom, modern, sofa)",
        config.MODEL_TASK_IMAGE_TO_TEXT:
            "✍️  Automatically generates descriptions and extracts keywords (no configuration needed)"
    }
    gui_instance.task_description.config(text=descriptions.get(task, ""))


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

    Args:
        gui_instance: Reference to main GUI instance
        event: Tkinter event (optional)
    """
    update_task_description(gui_instance)
    update_step_states(gui_instance)
    logging.info(f"Model task changed to: {gui_instance.model_task.get()}")


def on_mode_change(gui_instance):
    """Handle mode change between local and Daminion.

    Args:
        gui_instance: Reference to main GUI instance
    """
    mode = gui_instance.mode_var.get()
    gui_instance.processing_mode = mode
    logging.info(f"Processing mode changed to: {mode}")

    if mode == "daminion":
        gui_instance.daminion_section.pack(fill="x", pady=(10, 0))
        gui_instance.local_section.pack_forget()
        gui_instance.dir_label.config(text="Daminion mode: Items will be fetched from DAMS")
    else:
        gui_instance.local_section.pack(fill="x", pady=(10, 0))
        gui_instance.daminion_section.pack_forget()
        if gui_instance.image_dir:
            gui_instance.dir_label.config(text=str(gui_instance.image_dir))
        else:
            gui_instance.dir_label.config(text="No directory selected")

    update_step_states(gui_instance)


def on_scope_change(gui_instance):
    """Handle showing/hiding controls depending on the selected processing scope.

    Args:
        gui_instance: Reference to main GUI instance
    """
    scope = gui_instance.scope_var.get()
    if scope == 'collection':
        gui_instance.collection_selector_frame.pack(fill="x", pady=(5, 0))
        if gui_instance.processing_mode == 'local':
            gui_instance.collection_path_label.config(
                foreground='black' if gui_instance.collection_path else 'gray'
            )
            gui_instance.daminion_collection_combo.config(state='disabled')
            gui_instance.refresh_collections_btn.config(state='disabled')
        else:
            gui_instance.collection_path_label.config(foreground='gray')
            gui_instance.daminion_collection_combo.config(state='readonly')
            gui_instance.refresh_collections_btn.config(state='normal')
    else:
        gui_instance.collection_selector_frame.pack_forget()


def select_directory(gui_instance):
    """Select local image directory.

    Args:
        gui_instance: Reference to main GUI instance
    """
    directory = filedialog.askdirectory(title="Select Image Directory")
    if directory:
        gui_instance.image_dir = Path(directory)
        gui_instance.dir_label.config(text=str(gui_instance.image_dir), foreground="black")
        logging.info(f"Selected directory: {gui_instance.image_dir}")
        update_step_states(gui_instance)


def select_collection(gui_instance):
    """Select a sub-folder within the currently chosen local image directory.

    Args:
        gui_instance: Reference to main GUI instance
    """
    if not gui_instance.image_dir:
        messagebox.showerror("Error", "Please select an image directory first (Step 1).")
        return

    directory = filedialog.askdirectory(
        title="Select Collection (sub-folder)", initialdir=str(gui_instance.image_dir)
    )
    if directory:
        try:
            sel = Path(directory).resolve()
            if str(sel).startswith(str(gui_instance.image_dir.resolve())):
                gui_instance.collection_path = sel
                gui_instance.collection_path_label.config(text=str(gui_instance.collection_path), foreground='black')
            else:
                messagebox.showerror("Error", "Please select a sub-folder inside the chosen image directory.")
        except Exception:
            messagebox.showerror("Error", "Failed to select collection path.")


def show_model_info(gui_instance, event=None):
    """Show information about selected model.

    Args:
        gui_instance: Reference to main GUI instance
        event: Tkinter event (optional)
    """
    selection = gui_instance.model_listbox.curselection()
    if not selection:
        return

    model_id_display = gui_instance.model_listbox.get(selection[0])
    model_id = model_id_display.split(" (")[0]

    gui_instance.status_label.config(text=f"Status: Fetching info for {model_id}...")
    threading.Thread(
        target=lambda: gui_instance.show_model_info_worker(model_id), daemon=True
    ).start()

def set_hf_token(gui_instance):
    """Dialog to set the Hugging Face API token."""
    current_token = gui_instance.config_manager.get('hf_token') or ""
    token = simpledialog.askstring(
        "Hugging Face API Token", 
        "Enter your Hugging Face API Token (Read access):\n(Leave empty to remove)", 
        parent=gui_instance, initialvalue=current_token
    )
    if token is not None:
        gui_instance.config_manager.set('hf_token', token.strip() if token.strip() else None)
        gui_instance.config_manager.save_config()
        messagebox.showinfo("Token Saved", "API Token updated successfully.")
