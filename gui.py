"""
Main GUI for the Advanced Image Tagger application.
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

class ImageTaggerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(config.APP_NAME)
        self.geometry(config.GEOMETRY)

        self.q = queue.Queue()
        self.model = None
        self.image_dir = None
        self.stop_event = threading.Event()
        self.config_manager = ConfigManager()
        self.progress_tracker = ProgressTracker()
        self.daminion_client = None
        self.processing_mode = "local"

        self._create_widgets()
        self._create_menu()

        self.after(100, self.process_queue)
        logging.info("GUI initialized.")

    def _create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        cache_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Cache", menu=cache_menu)
        cache_menu.add_command(label="View Cache Path", command=self.show_cache_path)
        cache_menu.add_command(label="Clear Model Cache", command=self.clear_cache)
        logging.info("Cache menu created.")

    def _create_widgets(self):
        self.mode_frame = ttk.LabelFrame(self, text="Processing Mode")
        self.mode_frame.pack(padx=10, pady=10, fill="x")
        self.daminion_frame = ttk.LabelFrame(self, text="Daminion DAMS Connection")
        self.daminion_frame.pack(padx=10, pady=10, fill="x")
        self.model_frame = ttk.LabelFrame(self, text="Model Selection")
        self.model_frame.pack(padx=10, pady=10, fill="x")
        self.config_frame = ttk.LabelFrame(self, text="Configuration & Execution")
        self.config_frame.pack(padx=10, pady=10, fill="x")
        self.progress_frame = ttk.LabelFrame(self, text="Progress & Status")
        self.progress_frame.pack(padx=10, pady=10, fill="x")

        self._create_mode_widgets()
        self._create_daminion_widgets()
        self._create_model_widgets()
        self._create_config_widgets()
        self._create_progress_widgets()
        logging.info("GUI widgets created.")

    def _create_mode_widgets(self):
        ttk.Label(self.mode_frame, text="Select Mode:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.mode_var = tk.StringVar(value="local")
        ttk.Radiobutton(self.mode_frame, text="Local Files", variable=self.mode_var, value="local", command=self.on_mode_change).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(self.mode_frame, text="Daminion DAMS", variable=self.mode_var, value="daminion", command=self.on_mode_change).grid(row=0, column=2, padx=5, pady=5, sticky="w")

    def _create_daminion_widgets(self):
        ttk.Label(self.daminion_frame, text="Server URL:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.daminion_url_entry = ttk.Entry(self.daminion_frame, width=40)
        self.daminion_url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.daminion_url_entry.insert(0, self.config_manager.get('daminion_url', 'https://interiors.daminion.net'))

        ttk.Label(self.daminion_frame, text="Username:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.daminion_username_entry = ttk.Entry(self.daminion_frame, width=40)
        self.daminion_username_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.daminion_username_entry.insert(0, self.config_manager.get('daminion_username', ''))

        ttk.Label(self.daminion_frame, text="Password:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.daminion_password_entry = ttk.Entry(self.daminion_frame, width=40, show="*")
        self.daminion_password_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.daminion_connect_button = ttk.Button(self.daminion_frame, text="Connect to Daminion", command=self.connect_daminion)
        self.daminion_connect_button.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

        self.daminion_status_label = ttk.Label(self.daminion_frame, text="Not connected", foreground="gray")
        self.daminion_status_label.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

        self.daminion_frame.grid_columnconfigure(1, weight=1)
        self.daminion_frame.pack_forget()

    def on_mode_change(self):
        mode = self.mode_var.get()
        self.processing_mode = mode
        logging.info(f"Processing mode changed to: {mode}")

        if mode == "daminion":
            self.daminion_frame.pack(after=self.mode_frame, padx=10, pady=10, fill="x")
            self.select_dir_button.config(state="disabled")
            self.dir_label.config(text="Daminion mode: Items will be fetched from DAMS")
        else:
            self.daminion_frame.pack_forget()
            self.select_dir_button.config(state="normal")
            if self.image_dir:
                self.dir_label.config(text=str(self.image_dir))
            else:
                self.dir_label.config(text="No directory selected.")

    def connect_daminion(self):
        url = self.daminion_url_entry.get().strip()
        username = self.daminion_username_entry.get().strip()
        password = self.daminion_password_entry.get()

        if not url or not username or not password:
            messagebox.showerror("Error", "Please fill in all Daminion connection fields.")
            return

        self.daminion_status_label.config(text="Connecting...", foreground="orange")
        self.daminion_connect_button.config(state="disabled")

        threading.Thread(target=self.connect_daminion_worker, args=(url, username, password), daemon=True).start()

    def connect_daminion_worker(self, url, username, password):
        try:
            client = DaminionClient(url, username, password)
            status = client.test_connection()

            if status['connected']:
                self.daminion_client = client
                self.config_manager.set('daminion_url', url)
                self.config_manager.set('daminion_username', username)
                self.config_manager.save_config()

                self.q.put(("daminion_connected", status))
            else:
                self.q.put(("daminion_error", status.get('error', 'Unknown error')))
        except Exception as e:
            logging.exception("Daminion connection failed")
            self.q.put(("daminion_error", str(e)))

    def _create_model_widgets(self):
        ttk.Label(self.model_frame, text="Model Task:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.model_task = ttk.Combobox(self.model_frame, values=[config.MODEL_TASK_IMAGE_CLASSIFICATION, config.MODEL_TASK_ZERO_SHOT, config.MODEL_TASK_IMAGE_TO_TEXT])
        self.model_task.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        last_task = self.config_manager.get('last_model_task', config.MODEL_TASK_IMAGE_CLASSIFICATION)
        task_index = [config.MODEL_TASK_IMAGE_CLASSIFICATION, config.MODEL_TASK_ZERO_SHOT, config.MODEL_TASK_IMAGE_TO_TEXT].index(last_task) if last_task in [config.MODEL_TASK_IMAGE_CLASSIFICATION, config.MODEL_TASK_ZERO_SHOT, config.MODEL_TASK_IMAGE_TO_TEXT] else 0
        self.model_task.current(task_index)
        self.model_task.bind("<<ComboboxSelected>>", self.on_model_task_change)
        self.find_models_button = ttk.Button(self.model_frame, text="Find Models", command=self.find_models)
        self.find_models_button.grid(row=0, column=2, padx=5, pady=5)
        self.model_listbox = tk.Listbox(self.model_frame, height=10)
        self.model_listbox.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        self.model_listbox.bind("<<ListboxSelect>>", self.show_model_info)
        self.model_info_text = tk.Text(self.model_frame, height=10, wrap="word")
        self.model_info_text.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        self.load_model_button = ttk.Button(self.model_frame, text="Load Selected Model", command=self.load_model)
        self.load_model_button.grid(row=3, column=0, columnspan=3, padx=5, pady=5)

    def _create_config_widgets(self):
        self.select_dir_button = ttk.Button(self.config_frame, text="Select Image Directory", command=self.select_directory)
        self.select_dir_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.dir_label = ttk.Label(self.config_frame, text="No directory selected.")
        self.dir_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(self.config_frame, text="Enter fixed categories:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.categories_entry = ttk.Entry(self.config_frame, width=80)
        self.categories_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.categories_entry.insert(0, self.config_manager.get('default_categories', 'Scenery, Portrait, Document, Animal'))
        ttk.Label(self.config_frame, text="Enter custom keywords:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.keywords_entry = ttk.Entry(self.config_frame, width=80)
        self.keywords_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.keywords_entry.insert(0, self.config_manager.get('default_keywords', 'beach, sunset, dog, car, winter'))
        self.start_button = ttk.Button(self.config_frame, text="Start Processing", state="disabled", command=self.start_processing)
        self.start_button.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

    def _create_progress_widgets(self):
        self.status_label = ttk.Label(self.progress_frame, text="Status: Ready")
        self.status_label.pack(padx=5, pady=5, fill="x")
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", length=100, mode="determinate")
        self.progress_bar.pack(padx=5, pady=5, fill="x")
        self.model_progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", length=100, mode="determinate")
        self.model_progress_bar.pack(padx=5, pady=5, fill="x")

    def on_model_task_change(self, event=None):
        task = self.model_task.get()
        logging.info(f"Model task changed to: {task}")
        if task == config.MODEL_TASK_IMAGE_TO_TEXT:
            self.categories_entry.config(state="disabled")
            self.keywords_entry.config(state="disabled")
        else:
            self.categories_entry.config(state="normal")
            self.keywords_entry.config(state="normal")

    def find_models(self):
        logging.info("User initiated model search.")
        self.status_label.config(text="Status: Finding models...")
        self.find_models_button.config(state="disabled")
        task = self.model_task.get()
        threading.Thread(target=huggingface_utils.find_models_worker, args=(task, self.q), daemon=True).start()

    def show_model_info(self, event):
        selection = self.model_listbox.curselection()
        if not selection:
            return
        model_id = self.model_listbox.get(selection[0])
        model_id = model_id.replace(" (downloaded)", "")
        logging.info(f"User requested info for model: {model_id}")
        self.status_label.config(text=f"Status: Fetching info for {model_id}...")
        threading.Thread(target=huggingface_utils.show_model_info_worker, args=(model_id, self.q), daemon=True).start()

    def load_model(self):
        selection = self.model_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a model to load.")
            return
        model_id = self.model_listbox.get(selection[0])
        model_id = model_id.replace(" (downloaded)", "")
        logging.info(f"User initiated model load for: {model_id}")
        self.status_label.config(text=f"Status: Loading model {model_id}...")
        self.load_model_button.config(state="disabled")
        task = self.model_task.get()
        threading.Thread(target=huggingface_utils.load_model_with_progress, args=(model_id, task, self.q), daemon=True).start()

    def select_directory(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            selected_path = Path(dir_path)

            if not selected_path.exists():
                messagebox.showerror("Error", "Selected directory does not exist.")
                return

            if not selected_path.is_dir():
                messagebox.showerror("Error", "Selected path is not a directory.")
                return

            try:
                test_file = selected_path / ".write_test"
                test_file.touch()
                test_file.unlink()
            except (PermissionError, OSError):
                messagebox.showerror("Error", "Directory is not writable. Please select a directory with write permissions.")
                return

            self.image_dir = selected_path
            self.config_manager.set('last_directory', str(selected_path))
            self.config_manager.save_config()
            logging.info(f"User selected directory: {dir_path}")
            self.dir_label.config(text=str(self.image_dir))
            if self.model:
                self.start_button.config(state="normal")

    def start_processing(self):
        logging.info("User started image processing.")

        if self.processing_mode == "daminion":
            self.start_daminion_processing()
        else:
            self.start_local_processing()

    def start_local_processing(self):
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
        if saved_job and saved_job.get("directory") == str(self.image_dir):
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
            self.progress_tracker.clear()
            image_files = all_image_files

        model_name = self.model.model.name_or_path if self.model else "unknown"
        self.progress_tracker.start_job(self.image_dir, len(image_files), model_name, task)

        self.start_button.config(state="disabled")
        self.progress_bar["maximum"] = len(image_files)
        self.progress_bar["value"] = 0
        logging.info(f"Starting processing for {len(image_files)} images.")
        threading.Thread(target=self.process_images_worker, args=(image_files, categories, keywords), daemon=True).start()

    def start_daminion_processing(self):
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

        response = messagebox.askyesno(
            "Start Daminion Processing",
            f"This will process items from Daminion DAMS.\n\n"
            f"Total items in catalog: {self.daminion_client.get_total_count()}\n"
            f"Processing mode: {task}\n\n"
            "Process all items?"
        )

        if not response:
            return

        self.start_button.config(state="disabled")
        logging.info("Starting Daminion processing...")
        threading.Thread(target=self.process_daminion_worker, args=(categories, keywords), daemon=True).start()

    def process_daminion_worker(self, categories, keywords):
        logging.info("Daminion processing worker started.")
        model_task = self.model_task.get()

        try:
            self.q.put(("status_update", "Fetching items from Daminion..."))
            items = self.daminion_client.get_all_items_paginated(batch_size=100, max_items=None)

            if not items:
                self.q.put(("error", "No items retrieved from Daminion"))
                return

            self.progress_bar["maximum"] = len(items)
            self.progress_bar["value"] = 0
            self.q.put(("status_update", f"Processing {len(items)} items..."))

            completed_count = 0
            for item in items:
                if self.stop_event.is_set():
                    break

                try:
                    item_id = item.get('id')
                    filename = item.get('fileName', f'item_{item_id}')

                    self.q.put(("status_update", f"Processing {filename}..."))

                    thumb_path = self.daminion_client.download_thumbnail(item_id)
                    if not thumb_path or not thumb_path.exists():
                        logging.warning(f"Failed to download thumbnail for item {item_id}")
                        continue

                    from PIL import Image
                    image = Image.open(thumb_path)

                    result = None
                    if model_task == config.MODEL_TASK_IMAGE_CLASSIFICATION:
                        result = self.model(image, candidate_labels=categories)
                        if result:
                            category = result[0]['label']
                            confidence = result[0]['score']
                            logging.info(f"Item {item_id}: {category} ({confidence:.2f})")
                            self.daminion_client.update_item_metadata(str(item_id), category=category)

                    elif model_task == config.MODEL_TASK_ZERO_SHOT:
                        result = self.model(image, candidate_labels=keywords)
                        if result:
                            detected_keywords = [r['label'] for r in result if r['score'] > 0.9]
                            if detected_keywords:
                                logging.info(f"Item {item_id}: {detected_keywords}")
                                self.daminion_client.update_item_metadata(str(item_id), keywords=detected_keywords)

                    elif model_task == config.MODEL_TASK_IMAGE_TO_TEXT:
                        result = self.model(image)
                        if result and len(result) > 0:
                            generated_text = result[0].get('generated_text', '')
                            generated_keywords = [w for w in generated_text.split() if len(w) > 3][:10]
                            logging.info(f"Item {item_id}: {generated_keywords}")
                            self.daminion_client.update_item_metadata(str(item_id), keywords=generated_keywords)

                    completed_count += 1
                    self.q.put(("progress", completed_count))

                except Exception as e:
                    logging.exception(f"Error processing Daminion item {item.get('id')}")
                    self.q.put(("error", f"Failed to process item: {e}"))

            self.daminion_client.cleanup_temp_files()
            self.q.put(("progress_done", f"Finished processing {completed_count} Daminion items."))
            logging.info("Daminion processing worker finished.")

        except Exception as e:
            logging.exception("Daminion processing worker failed")
            self.q.put(("error", f"Daminion processing failed: {e}"))
            self.start_button.config(state="normal")

    def process_images_worker(self, image_files, categories, keywords):
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
                completed_count += 1
                self.q.put(("progress", completed_count))
                try:
                    future.result()
                    self.progress_tracker.mark_processed(image_path)
                except Exception as e:
                    logging.exception(f"Error processing {image_path.name} in worker.")
                    error_msg = str(e)
                    self.progress_tracker.mark_failed(image_path, error_msg)
                    self.q.put(("error", f"Failed to process {image_path.name}: {e}"))

        self.progress_tracker.complete_job()
        self.q.put(("progress_done", "Finished processing."))
        logging.info("Image processing worker finished.")

    def process_queue(self):
        try:
            message_type, data = self.q.get_nowait()
            logging.debug(f"GUI received queue message: {message_type}")

            if message_type == "models_found":
                self.model_listbox.delete(0, tk.END)
                model_ids, downloaded_models = data
                for model_id in model_ids:
                    if model_id in downloaded_models:
                        self.model_listbox.insert(tk.END, f"{model_id} (downloaded)")
                        self.model_listbox.itemconfig(tk.END, fg='green')
                    else:
                        self.model_listbox.insert(tk.END, model_id)
                self.status_label.config(text="Status: Found models. Select one to see details.")
                self.find_models_button.config(state="normal")

            elif message_type == "model_info_found":
                self.model_info_text.delete("1.0", tk.END)
                self.model_info_text.insert("1.0", data)
                self.status_label.config(text="Status: Model info loaded.")

            elif message_type == "model_download_progress":
                current, total = data
                self.model_progress_bar["maximum"] = total
                self.model_progress_bar["value"] = current

            elif message_type == "model_loaded":
                self.model = data
                model_name = self.model.model.name_or_path
                self.config_manager.set('last_model_id', model_name)
                self.config_manager.set('last_model_task', self.model_task.get())
                self.config_manager.save_config()
                self.status_label.config(text=f"Status: Model {model_name} loaded.")
                self.load_model_button.config(state="normal")
                self.model_progress_bar["value"] = 0
                if self.image_dir or (self.processing_mode == "daminion" and self.daminion_client):
                    self.start_button.config(state="normal")

            elif message_type == "error":
                self.status_label.config(text=f"Status: Error - {data}")
                self.load_model_button.config(state="normal")
                self.find_models_button.config(state="normal")

            elif message_type == "status_update":
                self.status_label.config(text=f"Status: {data}")

            elif message_type == "progress":
                self.progress_bar["value"] = data

            elif message_type == "progress_done":
                self.status_label.config(text=f"Status: {data}")
                self.start_button.config(state="normal")
                self.progress_bar["value"] = self.progress_bar["maximum"]

            elif message_type == "daminion_connected":
                status = data
                self.daminion_status_label.config(
                    text=f"Connected: {status['total_items']} items in catalog",
                    foreground="green"
                )
                self.daminion_connect_button.config(state="normal")
                if self.model:
                    self.start_button.config(state="normal")
                logging.info(f"Daminion connected: {status['total_items']} items")

            elif message_type == "daminion_error":
                self.daminion_status_label.config(text=f"Connection failed: {data}", foreground="red")
                self.daminion_connect_button.config(state="normal")
                messagebox.showerror("Daminion Connection Error", f"Failed to connect to Daminion:\n\n{data}")

        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue)

    def show_cache_path(self):
        logging.info("User viewed cache path.")
        messagebox.showinfo("Hugging Face Cache Path", f"The model cache is located at:\n\n{config.HF_CACHE_DIR}")

    def clear_cache(self):
        logging.info("User initiated cache clearing.")
        if messagebox.askyesno("Confirm Clear Cache", "Are you sure you want to delete the entire model cache?\nThis action cannot be undone and will require re-downloading all models."):
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