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

import config
import huggingface_utils
import image_processing

class ImageTaggerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(config.APP_NAME)
        self.geometry(config.GEOMETRY)

        self.q = queue.Queue()
        self.model = None
        self.image_dir = None
        self.stop_event = threading.Event()

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
        self.model_frame = ttk.LabelFrame(self, text="Model Selection")
        self.model_frame.pack(padx=10, pady=10, fill="x")
        self.config_frame = ttk.LabelFrame(self, text="Configuration & Execution")
        self.config_frame.pack(padx=10, pady=10, fill="x")
        self.progress_frame = ttk.LabelFrame(self, text="Progress & Status")
        self.progress_frame.pack(padx=10, pady=10, fill="x")

        self._create_model_widgets()
        self._create_config_widgets()
        self._create_progress_widgets()
        logging.info("GUI widgets created.")

    def _create_model_widgets(self):
        ttk.Label(self.model_frame, text="Model Task:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.model_task = ttk.Combobox(self.model_frame, values=["image-classification", "zero-shot-image-classification", "image-to-text"])
        self.model_task.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.model_task.current(0)
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
        self.categories_entry.insert(0, "Scenery, Portrait, Document, Animal")
        ttk.Label(self.config_frame, text="Enter custom keywords:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.keywords_entry = ttk.Entry(self.config_frame, width=80)
        self.keywords_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.keywords_entry.insert(0, "beach, sunset, dog, car, winter")
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
        if task == "image-to-text":
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
            self.image_dir = Path(dir_path)
            logging.info(f"User selected directory: {dir_path}")
            self.dir_label.config(text=str(self.image_dir))
            if self.model:
                self.start_button.config(state="normal")

    def start_processing(self):
        logging.info("User started image processing.")
        task = self.model_task.get()
        cats_str = self.categories_entry.get()
        keywords_str = self.keywords_entry.get()

        if not cats_str and task == "image-classification":
            messagebox.showerror("Error", "Categories are required for image classification.")
            return

        if not keywords_str and task == "zero-shot-image-classification":
            messagebox.showerror("Error", "Keywords are required for zero-shot classification.")
            return

        categories = [c.strip() for c in cats_str.split(",")]
        keywords = [k.strip() for k in keywords_str.split(",")]

        image_files = list(self.image_dir.rglob("*.jpg")) + list(self.image_dir.rglob("*.jpeg")) + list(self.image_dir.rglob("*.png"))

        if not image_files:
            logging.warning("Image processing started with no images found.")
            messagebox.showinfo("Info", "No image files found in the selected directory.")
            return

        self.start_button.config(state="disabled")
        self.progress_bar["maximum"] = len(image_files)
        self.progress_bar["value"] = 0
        logging.info(f"Starting processing for {len(image_files)} images.")
        threading.Thread(target=self.process_images_worker, args=(image_files, categories, keywords), daemon=True).start()

    def process_images_worker(self, image_files, categories, keywords):
        logging.info("Image processing worker started.")
        model_task = self.model_task.get()
        for i, image_path in enumerate(image_files):
            self.q.put(("progress", i + 1))
            try:
                image_processing.process_single_image(image_path, self.model, model_task, categories, keywords, self.q)
            except Exception as e:
                logging.exception(f"Error processing {image_path.name} in worker.")
                self.q.put(("error", f"Failed to process {image_path.name}: {e}"))
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
                self.status_label.config(text=f"Status: Model {self.model.model.name_or_path} loaded.")
                self.load_model_button.config(state="normal")
                self.model_progress_bar["value"] = 0
                if self.image_dir:
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
                shutil.rmtree(config.HF_CACHE_DIR)
                logging.info("Cache cleared successfully.")
                messagebox.showinfo("Success", "The model cache has been cleared.")
            except FileNotFoundError:
                logging.warning("Cache directory not found during clearing.")
                messagebox.showinfo("Info", "The cache directory does not exist.")
            except Exception as e:
                logging.exception("Failed to clear cache.")
                messagebox.showerror("Error", f"Failed to clear cache: {e}")