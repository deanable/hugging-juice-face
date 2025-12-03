"""
Main GUI for the Advanced Image Tagger application.
Simplified version using modular components.
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import shutil
import time
from pathlib import Path

import config
from config_manager import ConfigManager
from progress_tracker import ProgressTracker
from daminion_client import DaminionClient
from report_generator import ProcessingReport

# Import modular components
import gui_steps
import gui_workers
import gui_handlers


class ImageTaggerGUI(tk.Tk):
    """Main application window with step-by-step workflow."""

    def __init__(self):
        super().__init__()
        self.title(config.APP_NAME)
        self.geometry("900x800")

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
        self.daminion_client = None
        self.processing_mode = "local"
        self.report = ProcessingReport()
        self.processing_start_time = None

        self._create_widgets()
        self._create_menu()
        gui_handlers.update_step_states(self)

        try:
            gui_handlers.on_scope_change(self)
        except Exception:
            pass

        self.after(100, self.process_queue)
        logging.info("GUI initialized with step-by-step workflow.")

    def _create_menu(self):
        """Create application menu bar."""
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

    def _create_widgets(self):
        """Create main UI widgets using modular components."""
        main_container = ttk.Frame(self, padding="10")
        main_container.pack(fill="both", expand=True)

        title_label = ttk.Label(
            main_container, text="AI-Powered Image Tagger",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 10))

        subtitle_label = ttk.Label(
            main_container,
            text="Follow the steps below to tag your images with AI",
            font=("Arial", 10)
        )
        subtitle_label.pack(pady=(0, 20))

        # Create collapsible panes for each step
        self.step1_pane = gui_steps.CollapsiblePane(main_container, title="Step 1: Choose Image Source")
        self.step1_pane.pack(fill="x", pady=(0, 10))
        gui_steps.create_step1_source(self.step1_pane.content, self)

        self.step2_pane = gui_steps.CollapsiblePane(main_container, title="Step 2: Select AI Model")
        self.step2_pane.pack(fill="x", pady=(0, 10))
        gui_steps.create_step2_model(self.step2_pane.content, self)

        self.step3_pane = gui_steps.CollapsiblePane(main_container, title="Step 3: Configure Tagging")
        self.step3_pane.pack(fill="x", pady=(0, 10))
        gui_steps.create_step3_config(self.step3_pane.content, self)

        self.step4_pane = gui_steps.CollapsiblePane(main_container, title="Step 4: Process Images")
        self.step4_pane.pack(fill="x", pady=(0, 10))
        gui_steps.create_step4_process(self.step4_pane.content, self)

        gui_steps.create_progress_section(main_container, self)

    # Event handlers (delegate to gui_handlers module)
    def on_model_task_change(self, event=None):
        gui_handlers.on_model_task_change(self, event)

    def on_mode_change(self):
        gui_handlers.on_mode_change(self)

    def on_scope_change(self):
        gui_handlers.on_scope_change(self)

    def select_directory(self):
        gui_handlers.select_directory(self)

    def select_collection(self):
        gui_handlers.select_collection(self)

    def update_task_description(self):
        gui_handlers.update_task_description(self)

    def show_model_info(self, event=None):
        gui_handlers.show_model_info(self, event)

    def _update_step_states(self):
        gui_handlers.update_step_states(self)

    def calculate_time_remaining(self, completed, total):
        return gui_handlers.calculate_time_remaining(self, completed, total)

    # Worker thread launchers
    def connect_daminion(self):
        """Connect to Daminion server."""
        url = self.daminion_url_entry.get().strip()
        username = self.daminion_username_entry.get().strip()
        password = self.daminion_password_entry.get()

        if not url or not username or not password:
            messagebox.showerror("Error", "Please fill in all Daminion connection fields.")
            return

        self.daminion_status_label.config(text="● Connecting...", foreground="orange")
        self.daminion_connect_button.config(state="disabled")

        threading.Thread(
            target=gui_workers.connect_daminion_worker,
            args=(self, url, username, password), daemon=True
        ).start()

    def find_models(self):
        """Search for models on Hugging Face."""
        self.find_models_button.config(state="disabled")
        self.status_label.config(text="Status: Searching for models on Hugging Face...")
        logging.info("User initiated model search.")
        threading.Thread(target=gui_workers.find_models_worker, args=(self,), daemon=True).start()

    def show_model_info_worker(self, model_id):
        """Worker to fetch model info."""
        gui_workers.show_model_info_worker(self, model_id)

    def load_model(self):
        """Load selected model."""
        selection = self.model_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a model from the list.")
            return

        model_id_display = self.model_listbox.get(selection[0])
        model_id = model_id_display.split(" (")[0]

        self.load_model_button.config(state="disabled")
        self.status_label.config(text=f"Status: Downloading and loading {model_id}...")
        logging.info(f"User initiated loading of model {model_id}.")

        threading.Thread(target=gui_workers.load_model_worker, args=(self, model_id), daemon=True).start()

    def start_processing(self):
        """Start image processing."""
        logging.info("User started image processing.")

        if self.processing_mode == "daminion":
            self.start_daminion_processing()
        else:
            self.start_local_processing()

    def start_local_processing(self):
        """Start processing local files."""
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

        # Use efficient scanning
        all_image_files = gui_handlers.scan_image_directory(self.image_dir)

        if not all_image_files:
            logging.warning("Image processing started with no images found.")
            messagebox.showinfo("Info", "No image files found in the selected directory.")
            return

        saved_job = self.progress_tracker.load_job()
        scope = getattr(self, 'scope_var', None) and self.scope_var.get() or 'untagged'

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
            image_files = gui_handlers.filter_local_images(all_image_files, scope, self.collection_path)
            if scope != 'untagged':
                self.progress_tracker.clear()

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

        threading.Thread(
            target=gui_workers.process_images_worker,
            args=(self, image_files, categories, keywords), daemon=True
        ).start()

    def start_daminion_processing(self):
        """Start processing Daminion items."""
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
            filtered = self.daminion_client.get_flagged_items(batch_size=200, max_items=None)
            if not filtered:
                messagebox.showinfo("Info", "No flagged/rejected items found in Daminion.")
                return
            if not messagebox.askyesno("Start Daminion Processing",
                                       f"This will process {len(filtered)} flagged/rejected items from Daminion. Proceed?"):
                return
            items_to_process = filtered

        elif scope == 'collection':
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
            if not messagebox.askyesno("Start Daminion Processing",
                                       f"This will process items from Daminion.\n\nTotal items in catalog: {self.daminion_client.get_total_count()}\nProcessing mode: {task}\n\nProcess all items?"):
                return
            items_to_process = self.daminion_client.get_all_items_paginated(batch_size=100, max_items=None)

        self.start_button.config(state="disabled")
        logging.info("Starting Daminion processing...")
        threading.Thread(
            target=gui_workers.process_daminion_worker,
            args=(self, categories, keywords, items_to_process), daemon=True
        ).start()

    def refresh_daminion_collections(self):
        """Start background refresh of shared collections."""
        if not self.daminion_client:
            messagebox.showerror("Error", "Not connected to Daminion. Please connect first.")
            return

        self.refresh_collections_btn.config(state='disabled')
        self.status_label.config(text="Status: Refreshing Daminion collections...")
        threading.Thread(target=gui_workers.refresh_daminion_collections_worker, args=(self,), daemon=True).start()

    def process_queue(self):
        """Process messages from worker threads."""
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
                total = total or 1
                self.model_progress_bar["maximum"] = total
                self.model_progress_bar["value"] = current

                now = time.time()
                if not self._dl_start_time:
                    self._dl_start_time = now
                    self._dl_total_bytes = total
                    self._dl_last_bytes = current
                    self._dl_last_time = now

                elapsed = max(0.001, now - self._dl_start_time)
                bytes_per_sec = current / elapsed if elapsed > 0 else 0
                remaining = max(0, total - current)
                eta = int(remaining / bytes_per_sec) if bytes_per_sec > 0 else None

                def mb(b):
                    return b / (1024 * 1024)

                percent = (current / total) * 100 if total else 0
                eta_text = ""
                if eta is not None:
                    if eta < 60:
                        eta_text = f"ETA: ~{eta}s"
                    else:
                        m = int(eta / 60)
                        eta_text = f"ETA: ~{m}m"

                self.model_progress_label.config(
                    text=f"{mb(current):.1f}/{mb(total):.1f} MB ({percent:.1f}%) {eta_text}"
                )

                if current >= total:
                    self._dl_start_time = None
                    self._dl_total_bytes = None
                    self._dl_last_bytes = 0
                    self._dl_last_time = None

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
                messagebox.showerror("Daminion Connection Error", f"Failed to connect to Daminion:\n\n{data}")
                self._update_step_states()

            elif message_type == "daminion_collections":
                cols = data or []
                if isinstance(cols, dict):
                    vals = cols.get('items') or cols.get('collections') or list(cols.values())
                    cols = vals or []

                self.daminion_collections = cols
                names = []
                for c in cols:
                    title = c.get('name') or c.get('title') or c.get('code') or str(c.get('id') or '')
                    idx = c.get('id') or c.get('code') or c.get('collectionId') or ''
                    names.append(f"{title} ({idx})" if idx else title)

                self.daminion_collection_combo['values'] = names
                if names:
                    self.daminion_collection_combo.current(0)
                try:
                    self.refresh_collections_btn.config(state='normal')
                except Exception:
                    pass

        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue)

    # Menu handlers
    def show_cache_path(self):
        """Show cache path dialog."""
        logging.info("User viewed cache path.")
        messagebox.showinfo("Hugging Face Cache Path",
                          f"The model cache is located at:\n\n{config.HF_CACHE_DIR}")

    def clear_cache(self):
        """Clear model cache."""
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
        """Export processing report to CSV."""
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
        """Export processing report to JSON."""
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
        """Show report summary dialog."""
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


def main():
    """Run the application."""
    from logging_config import setup_logging
    setup_logging()
    app = ImageTaggerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
