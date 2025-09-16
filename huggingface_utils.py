
"""Utilities for interacting with the Hugging Face Hub."""

import logging
from functools import partial
from tqdm import tqdm
from huggingface_hub import list_models, hf_hub_download, snapshot_download
from transformers import pipeline
from threading import RLock

class TqdmToQueue(tqdm):
    """A custom tqdm class that sends progress updates to a queue."""
    _lock = None
    _q = None
    _update_type = None

    def __init__(self, *args, **kwargs):
        if 'q' in kwargs:
            TqdmToQueue._q = kwargs.pop('q')
        if 'update_type' in kwargs:
            TqdmToQueue._update_type = kwargs.pop('update_type')
        super().__init__(*args, **kwargs)

    def update(self, n=1):
        super().update(n)
        if TqdmToQueue._q and TqdmToQueue._update_type:
            TqdmToQueue._q.put((TqdmToQueue._update_type, (self.n, self.total)))

    @classmethod
    def get_lock(cls):
        if cls._lock is None:
            cls._lock = RLock()
        return cls._lock

def find_models_worker(task, q):
    """Worker thread to fetch model list from Hugging Face Hub."""
    logging.info(f"Searching for models with task: '{task}'")
    try:
        models = list_models(filter=task, sort="downloads", direction=-1)
        model_ids = [model.modelId for model in models]
        logging.info(f"Found {len(model_ids)} models.")
        q.put(("models_found", model_ids))
    except Exception as e:
        logging.exception("Failed to find models.")
        q.put(("error", f"Failed to find models: {e}"))

def show_model_info_worker(model_id, q):
    """Worker thread to download a model's README file."""
    logging.info(f"Fetching README for model: {model_id}")
    try:
        readme_path = hf_hub_download(repo_id=model_id, filename="README.md")
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()
        logging.info(f"Successfully fetched README for model: {model_id}")
        q.put(("model_info_found", readme_content))
    except Exception as e:
        logging.warning(f"Could not retrieve README for {model_id}. Error: {e}")
        q.put(("model_info_found", f"Could not retrieve README for {model_id}.\n\n{e}"))

def load_model_with_progress(model_id, task, q):
    """Worker thread to load a model with progress reporting."""
    logging.info(f"Starting model load for: {model_id}")
    try:
        q.put(("status_update", f"Downloading model {model_id}..."))
        logging.info(f"Downloading model files for {model_id}...")
        
        TqdmToQueue._q = q
        TqdmToQueue._update_type = "model_download_progress"

        local_model_path = snapshot_download(
            repo_id=model_id,
            tqdm_class=TqdmToQueue,
        )
        logging.info(f"Model download complete for {model_id}.")

        q.put(("status_update", f"Initializing model {model_id}..."))
        logging.info(f"Initializing pipeline for {model_id}...")
        model = pipeline(task, model=local_model_path)
        logging.info(f"Model pipeline loaded successfully for: {model_id}")
        q.put(("model_loaded", model))

    except Exception as e:
        logging.exception(f"Failed to load model: {model_id}")
        q.put(("error", f"Failed to load model: {e}"))
