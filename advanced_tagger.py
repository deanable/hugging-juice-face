import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
from pathlib import Path
from huggingface_hub import list_models, hf_hub_download
from transformers import pipeline
from PIL import Image
import piexif
from iptcinfo3 import IPTCInfo

class ImageTaggerGUI(tk.Tk):
    """
    A desktop application for automatically categorizing and tagging images
    using models from the Hugging Face Hub.
    """
    def __init__(self):
        super().__init__()
        self.title("Advanced Image Tagger")
        self.geometry("800x600")

        # Queue for thread-safe communication with the GUI
        self.q = queue.Queue()

        # To hold the loaded model and selected directory
        self.model = None
        self.image_dir = None

        # Create main frames for different sections of the GUI
        self.model_frame = ttk.LabelFrame(self, text="Model Selection")
        self.model_frame.pack(padx=10, pady=10, fill="x")

        self.config_frame = ttk.LabelFrame(self, text="Configuration & Execution")
        self.config_frame.pack(padx=10, pady=10, fill="x")

        self.progress_frame = ttk.LabelFrame(self, text="Progress & Status")
        self.progress_frame.pack(padx=10, pady=10, fill="x")

        # Create the widgets for each section
        self._create_model_widgets()
        self._create_config_widgets()
        self._create_progress_widgets()

        # Start processing the queue for messages from background threads
        self.after(100, self.process_queue)

    def _create_model_widgets(self):
        """Creates the widgets for the model selection frame."""
        # Model Task Dropdown
        ttk.Label(self.model_frame, text="Model Task:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.model_task = ttk.Combobox(self.model_frame, values=["image-classification", "zero-shot-image-classification"])
        self.model_task.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.model_task.current(0)

        # Find Models Button
        self.find_models_button = ttk.Button(self.model_frame, text="Find Models", command=self.find_models)
        self.find_models_button.grid(row=0, column=2, padx=5, pady=5)

        # Model Listbox
        self.model_listbox = tk.Listbox(self.model_frame, height=10)
        self.model_listbox.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        self.model_listbox.bind("<<ListboxSelect>>", self.show_model_info)

        # Model Info Text Area
        self.model_info_text = tk.Text(self.model_frame, height=10, wrap="word")
        self.model_info_text.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        # Load Model Button
        self.load_model_button = ttk.Button(self.model_frame, text="Load Selected Model", command=self.load_model)
        self.load_model_button.grid(row=3, column=0, columnspan=3, padx=5, pady=5)

    def _create_config_widgets(self):
        """Creates the widgets for the configuration and execution frame."""
        # Directory Selection
        self.select_dir_button = ttk.Button(self.config_frame, text="Select Image Directory", command=self.select_directory)
        self.select_dir_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.dir_label = ttk.Label(self.config_frame, text="No directory selected.")
        self.dir_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Categories Input
        ttk.Label(self.config_frame, text="Enter fixed categories:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.categories_entry = ttk.Entry(self.config_frame, width=80)
        self.categories_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.categories_entry.insert(0, "Scenery, Portrait, Document, Animal")

        # Keywords Input
        ttk.Label(self.config_frame, text="Enter custom keywords:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.keywords_entry = ttk.Entry(self.config_frame, width=80)
        self.keywords_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.keywords_entry.insert(0, "beach, sunset, dog, car, winter")

        # Start Processing Button
        self.start_button = ttk.Button(self.config_frame, text="Start Processing", state="disabled", command=self.start_processing)
        self.start_button.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

    def _create_progress_widgets(self):
        """Creates the widgets for the progress and status frame."""
        # Status Label
        self.status_label = ttk.Label(self.progress_frame, text="Status: Ready")
        self.status_label.pack(padx=5, pady=5, fill="x")

        # Progress Bar
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", length=100, mode="determinate")
        self.progress_bar.pack(padx=5, pady=5, fill="x")

    def find_models(self):
        """Starts a background thread to find models on the Hugging Face Hub."""
        self.status_label.config(text="Status: Finding models...")
        self.find_models_button.config(state="disabled")
        threading.Thread(target=self.find_models_worker, daemon=True).start()

    def find_models_worker(self):
        """Worker thread to fetch model list from Hugging Face Hub."""
        try:
            task = self.model_task.get()
            models = list_models(filter=task, sort="downloads", direction=-1)
            model_ids = [model.modelId for model in models]
            self.q.put(("models_found", model_ids))
        except Exception as e:
            self.q.put(("error", f"Failed to find models: {e}"))

    def show_model_info(self, event):
        """Starts a background thread to fetch the selected model's README."""
        selection = self.model_listbox.curselection()
        if not selection:
            return

        model_id = self.model_listbox.get(selection[0])
        self.status_label.config(text=f"Status: Fetching info for {model_id}...")
        threading.Thread(target=self.show_model_info_worker, args=(model_id,), daemon=True).start()

    def show_model_info_worker(self, model_id):
        """Worker thread to download a model's README file."""
        try:
            readme_path = hf_hub_download(repo_id=model_id, filename="README.md")
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_content = f.read()
            self.q.put(("model_info_found", readme_content))
        except Exception as e:
            # It's common for models to not have a README, so we just show a message.
            self.q.put(("model_info_found", f"Could not retrieve README for {model_id}.\n\n{e}"))

    def load_model(self):
        """Starts a background thread to load the selected model."""
        selection = self.model_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a model to load.")
            return

        model_id = self.model_listbox.get(selection[0])
        self.status_label.config(text=f"Status: Loading model {model_id}...")
        self.load_model_button.config(state="disabled")
        threading.Thread(target=self.load_model_worker, args=(model_id,), daemon=True).start()

    def load_model_worker(self, model_id):
        """Worker thread to load a model using the transformers pipeline."""
        try:
            task = self.model_task.get()
            model = pipeline(task, model=model_id)
            self.q.put(("model_loaded", model))
        except Exception as e:
            self.q.put(("error", f"Failed to load model: {e}"))

    def select_directory(self):
        """Opens a dialog to select an image directory."""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.image_dir = Path(dir_path)
            self.dir_label.config(text=str(self.image_dir))
            if self.model:
                self.start_button.config(state="normal")

    def start_processing(self):
        """Validates inputs and starts the image processing worker thread."""
        cats_str = self.categories_entry.get()
        keywords_str = self.keywords_entry.get()

        if not cats_str and self.model_task.get() == "image-classification":
            messagebox.showerror("Error", "Categories are required for image classification.")
            return

        if not keywords_str and self.model_task.get() == "zero-shot-image-classification":
            messagebox.showerror("Error", "Keywords are required for zero-shot classification.")
            return

        categories = [c.strip() for c in cats_str.split(",")]
        keywords = [k.strip() for k in keywords_str.split(",")]

        image_files = list(self.image_dir.rglob("*.jpg")) + \
                      list(self.image_dir.rglob("*.jpeg")) + \
                      list(self.image_dir.rglob("*.png"))

        if not image_files:
            messagebox.showinfo("Info", "No image files found in the selected directory.")
            return

        self.start_button.config(state="disabled")
        self.progress_bar["maximum"] = len(image_files)

        threading.Thread(target=self.process_images_worker, args=(image_files, categories, keywords), daemon=True).start()

    def process_images_worker(self, image_files, categories, keywords):
        """Worker thread to process a batch of images."""
        for i, image_path in enumerate(image_files):
            try:
                self.q.put(("progress", (i, f"Processing {image_path.name}")))
                self.process_single_image(image_path, categories, keywords)
            except Exception as e:
                self.q.put(("error", f"Failed to process {image_path.name}: {e}"))
        self.q.put(("progress_done", "Finished processing."))

    def process_single_image(self, image_path, categories, keywords):
        """Processes a single image to get category and keywords."""
        image = Image.open(image_path)

        category = ""
        new_keywords = []

        # Determine category for image-classification models
        if self.model_task.get() == "image-classification":
            result = self.model(image, candidate_labels=categories)
            category = max(result, key=lambda x: x['score'])['label']
        # Determine keywords for zero-shot models
        elif self.model_task.get() == "zero-shot-image-classification":
            result = self.model(image, candidate_labels=keywords)
            # Apply keywords that meet a confidence threshold
            for r in result:
                if r['score'] > 0.9:
                    new_keywords.append(r['label'])

        self.write_metadata(image_path, category, new_keywords)

    def write_metadata(self, image_path, category, keywords):
        """Writes the category and keywords to the image's IPTC and EXIF metadata."""
        # --- IPTC METADATA ---
        try:
            info = IPTCInfo(image_path, force=True)
            if category:
                info['object name'] = category
            if keywords:
                # Append new keywords without creating duplicates
                existing_keywords = [k.decode('utf-8') for k in info['keywords']]
                for k in keywords:
                    if k not in existing_keywords:
                        existing_keywords.append(k)
                info['keywords'] = existing_keywords
            info.save()
        except Exception as e:
            self.q.put(("error", f"Could not write IPTC for {image_path.name}: {e}"))

        # --- EXIF METADATA ---
        try:
            exif_dict = piexif.load(str(image_path))
            if category:
                exif_dict['0th'][piexif.ImageIFD.XPSubject] = category.encode('utf-16le')
            if keywords:
                # Append new keywords without creating duplicates
                existing_keywords_str = exif_dict['0th'].get(piexif.ImageIFD.XPKeywords, b'').decode('utf-16le').rstrip('\x00')
                existing_keywords = existing_keywords_str.split(';') if existing_keywords_str else []
                for k in keywords:
                    if k not in existing_keywords:
                        existing_keywords.append(k)
                exif_dict['0th'][piexif.ImageIFD.XPKeywords] = ";".join(existing_keywords).encode('utf-16le')

            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, str(image_path))
        except Exception as e:
            self.q.put(("error", f"Could not write EXIF for {image_path.name}: {e}"))

    def process_queue(self):
        """Processes messages from the queue to update the GUI."""
        try:
            message_type, data = self.q.get_nowait()
            if message_type == "models_found":
                self.model_listbox.delete(0, tk.END)
                for model_id in data:
                    self.model_listbox.insert(tk.END, model_id)
                self.status_label.config(text="Status: Found models. Select one to see details.")
                self.find_models_button.config(state="normal")
            elif message_type == "model_info_found":
                self.model_info_text.delete("1.0", tk.END)
                self.model_info_text.insert("1.0", data)
                self.status_label.config(text="Status: Model info loaded.")
            elif message_type == "model_loaded":
                self.model = data
                self.status_label.config(text=f"Status: Model {self.model.model.name_or_path} loaded.")
                self.load_model_button.config(state="normal")
                if self.image_dir:
                    self.start_button.config(state="normal")
            elif message_type == "error":
                # Show non-blocking errors in the status bar
                self.status_label.config(text=f"Status: Error - {data}")
                # Re-enable buttons that were disabled
                self.load_model_button.config(state="normal")
                self.find_models_button.config(state="normal")
            elif message_type == "progress":
                progress, status_text = data
                self.progress_bar["value"] = progress
                self.status_label.config(text=f"Status: {status_text}")
            elif message_type == "progress_done":
                self.progress_bar["value"] = self.progress_bar["maximum"]
                self.status_label.config(text=f"Status: {data}")
                self.start_button.config(state="normal")
        except queue.Empty:
            pass
        finally:
            # Schedule the next check
            self.after(100, self.process_queue)

if __name__ == "__main__":
    app = ImageTaggerGUI()
    app.mainloop()
