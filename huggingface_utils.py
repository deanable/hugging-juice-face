"""Utilities for interacting with the Hugging Face Hub."""

import logging
import os
from functools import partial
from tqdm import tqdm
from huggingface_hub import list_models, hf_hub_download, snapshot_download, HfApi
from huggingface_hub.constants import HUGGINGFACE_HUB_CACHE
from requests.exceptions import HTTPError
from transformers import pipeline
from threading import RLock

class TqdmToQueue(tqdm):
    """A custom tqdm class that sends progress updates to a queue."""
    _lock = None
    _q = None
    _update_type = None
    _overall_total_size = 0
    _overall_downloaded_bytes = 0

    def __init__(self, *args, **kwargs):
        if 'q' in kwargs:
            TqdmToQueue._q = kwargs.pop('q')
        if 'update_type' in kwargs:
            TqdmToQueue._update_type = kwargs.pop('update_type')
        super().__init__(*args, **kwargs)

    def update(self, n=1):
        super().update(n)
        TqdmToQueue._overall_downloaded_bytes += n
        if TqdmToQueue._q and TqdmToQueue._update_type:
            TqdmToQueue._q.put((TqdmToQueue._update_type, (TqdmToQueue._overall_downloaded_bytes, TqdmToQueue._overall_total_size)))

    @classmethod
    def get_lock(cls):
        if cls._lock is None:
            cls._lock = RLock()
        return cls._lock

    @classmethod
    def reset_overall_progress(cls):
        cls._overall_downloaded_bytes = 0

    @classmethod
    def set_overall_total_size(cls, size):
        cls._overall_total_size = size

def get_model_cache_dir(model_id):
    """Returns the cache directory for a given model."""
    return os.path.join(HUGGINGFACE_HUB_CACHE, f"models--{model_id.replace('/', '--')}")

def is_model_downloaded(model_id):
    """Check if a model is fully downloaded."""
    try:
        api = HfApi()
        model_info = api.model_info(repo_id=model_id)
        model_cache_dir = get_model_cache_dir(model_id)
        # Check for snapshot directory
        snapshot_dir = os.path.join(model_cache_dir, 'snapshots')
        if not os.path.exists(snapshot_dir):
            return False
        # Get the latest snapshot
        snapshots = os.listdir(snapshot_dir)
        if not snapshots:
            return False
        latest_snapshot = snapshots[-1]
        
        for file_info in model_info.siblings:
            # Ignore some files
            if file_info.rfilename.endswith(('.gitattributes', 'README.md')):
                continue
            file_path = os.path.join(snapshot_dir, latest_snapshot, file_info.rfilename)
            if not os.path.exists(file_path):
                logging.info(f"Model {model_id} is not fully downloaded. Missing file: {file_info.rfilename}")
                return False
        return True
    except HTTPError as e:
        if e.response.status_code == 404:
            logging.warning(f"Model not found on Hub: {model_id}")
        else:
            logging.error(f"HTTPError checking model {model_id}: {e}")
        return False
    except Exception as e:
        logging.error(f"Error checking if model {model_id} is downloaded: {e}")
        return False

def get_downloaded_models(task):
    """Get a list of downloaded models for a given task."""
    logging.info(f"Searching for downloaded models with task: '{task}'")
    try:
        models = list_models(filter=task, sort="downloads", direction=-1)
        downloaded_models = []
        for model in models:
            if is_model_downloaded(model.modelId):
                downloaded_models.append(model.modelId)
        logging.info(f"Found {len(downloaded_models)} downloaded models.")
        return downloaded_models
    except Exception as e:
        logging.exception("Failed to find downloaded models.")
        return []

def find_models_worker(task, q):
    """Worker thread to fetch model list from Hugging Face Hub."""
    logging.info(f"Searching for models with task: '{task}'")
    logging.info(f"Searching for models with task: '{task}'")
    try:
        models = list_models(filter=task, sort="downloads", direction=-1)
        model_ids = [model.modelId for model in models]
        downloaded_models = [model_id for model_id in model_ids if is_model_downloaded(model_id)]
        logging.info(f"Found {len(model_ids)} models.")
        q.put(("models_found", (model_ids, downloaded_models)))
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
        if not is_model_downloaded(model_id):
            q.put(("status_update", f"Downloading model {model_id}..."))
            logging.info(f"Downloading model files for {model_id}...")

            # Get model info to calculate total size
            api = HfApi()
            model_info = api.model_info(repo_id=model_id)
            total_model_size = sum(sibling.size for sibling in model_info.siblings if sibling.size is not None)
            q.put(("total_model_size", total_model_size))
            logging.info(f"Total model size for {model_id}: {total_model_size} bytes.")
            
            TqdmToQueue.reset_overall_progress()
            TqdmToQueue.set_overall_total_size(total_model_size)
            TqdmToQueue._q = q
            TqdmToQueue._update_type = "model_download_progress"

            local_model_path = snapshot_download(
                repo_id=model_id,
                tqdm_class=TqdmToQueue,
            )
            logging.info(f"Model download complete for {model_id}.")
        else:
            logging.info(f"Model {model_id} is already downloaded.")
            # Get the latest snapshot path
            model_cache_dir = get_model_cache_dir(model_id)
            snapshot_dir = os.path.join(model_cache_dir, 'snapshots')
            latest_snapshot = os.listdir(snapshot_dir)[-1]
            local_model_path = os.path.join(snapshot_dir, latest_snapshot)

        q.put(("status_update", f"Initializing model {model_id}..."))
        logging.info(f"Initializing pipeline for {model_id}...")
        model = pipeline(task, model=local_model_path)
        logging.info(f"Model pipeline loaded successfully for: {model_id}")
        q.put(("model_loaded", model))

    except Exception as e:
        logging.exception(f"Failed to load model: {model_id}")
        q.put(("error", f"Failed to load model: {e}"))