"""Utilities for interacting with the Hugging Face Hub."""

import logging
import os
import shutil
from pathlib import Path
from functools import partial
from tqdm import tqdm
from huggingface_hub import list_models, hf_hub_download, snapshot_download, HfApi
from huggingface_hub.constants import HUGGINGFACE_HUB_CACHE
from requests.exceptions import HTTPError
from transformers import pipeline, AutoConfig, AutoTokenizer
from threading import RLock
import config
import json

class TqdmToQueue(tqdm):
    """A custom tqdm class that sends progress updates to a queue."""
    _lock = RLock()
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
        with TqdmToQueue._lock:
            TqdmToQueue._overall_downloaded_bytes += n
            if TqdmToQueue._q and TqdmToQueue._update_type:
                TqdmToQueue._q.put((TqdmToQueue._update_type, (TqdmToQueue._overall_downloaded_bytes, TqdmToQueue._overall_total_size)))

    @classmethod
    def get_lock(cls):
        return cls._lock

    @classmethod
    def reset_overall_progress(cls):
        with cls._lock:
            cls._overall_downloaded_bytes = 0

    @classmethod
    def set_overall_total_size(cls, size):
        with cls._lock:
            cls._overall_total_size = size

def get_cache_dir():
    """Returns the Hugging Face cache directory."""
    return HUGGINGFACE_HUB_CACHE

def clear_cache():
    """Clears the Hugging Face Hub cache directory."""
    cache_path = Path(HUGGINGFACE_HUB_CACHE)
    if cache_path.exists():
        shutil.rmtree(cache_path)
        logging.info("Hugging Face cache cleared.")

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
        latest_snapshot = sorted(snapshots)[-1]
        
        if model_info.siblings:
            for file_info in model_info.siblings:
                if file_info.rfilename.endswith(config.MODEL_FILE_EXCLUSIONS):
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
        # Limit results to reduce network load and UI clutter
        models = list_models(filter=task, sort="downloads", direction=-1, limit=config.MODEL_SEARCH_LIMIT)
        downloaded_models = []
        for model in models or []:
            if is_model_downloaded(model.id):
                downloaded_models.append(model.id)
        logging.info(f"Found {len(downloaded_models)} downloaded models.")
        return downloaded_models
    except Exception as e:
        logging.exception("Failed to find downloaded models.")
        return []

def find_models_worker(task, q):
    """Worker thread to fetch model list from Hugging Face Hub."""
    logging.info(f"Searching for models with task: '{task}'")
    try:
        # Request the top N models by downloads to keep the UI responsive.
        models = list_models(filter=task, sort="downloads", direction=-1, limit=config.MODEL_SEARCH_LIMIT)
        model_ids = [model.id for model in models or []][:config.MODEL_SEARCH_LIMIT]
        downloaded_models = [model_id for model_id in model_ids if is_model_downloaded(model_id)]
        logging.info(f"Found {len(model_ids)} models.")
        q.put(("models_found", (model_ids, downloaded_models)))
    except Exception as e:
        logging.exception("Failed to find models.")
        q.put(("error", f"Failed to find models: {e}"))

def find_local_models_by_task(task: str) -> list[str]:
    """
    Finds locally cached models compatible with a given task by scanning the cache.

    Args:
        task: The pipeline task to filter by (e.g., 'image-classification').

    Returns:
        A list of model IDs that are cached locally and support the task.
    """
    local_models = []
    cache_path = Path(HUGGINGFACE_HUB_CACHE)
    if not cache_path.exists():
        logging.warning("Hugging Face cache directory not found.")
        return []

    logging.info(f"Scanning cache for local models for task: {task}")
    for model_dir in cache_path.glob("models--*"):
        if not model_dir.is_dir():
            continue

        model_id = model_dir.name[len("models--"):
].replace("--", "/")
        try:
            # Check for a config.json in the latest snapshot
            snapshot_dirs = [d for d in (model_dir / "snapshots").iterdir() if d.is_dir()]
            if not snapshot_dirs:
                continue

            latest_snapshot = max(snapshot_dirs, key=lambda p: p.stat().st_mtime)
            config_path = latest_snapshot / "config.json"

            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    model_config = json.load(f)
                
                # Check if the model supports the task via its pipeline_tag or architectures
                if model_config.get("pipeline_tag") == task:
                    local_models.append(model_id)
        except Exception as e:
            logging.debug(f"Could not inspect model {model_id}: {e}")
            continue
    
    logging.info(f"Found {len(local_models)} local models for task '{task}'.")
    return local_models


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
    """Worker thread to load a model with enhanced granular progress reporting."""
    logging.info(f"Starting model load for: {model_id}")
    
    # Import enhanced progress tracking
    try:
        from enhanced_progress import set_progress_stage, ProgressStage, get_progress_tracker
        has_enhanced_progress = True
    except ImportError:
        has_enhanced_progress = False
    
    if has_enhanced_progress:
        # Initialize enhanced progress tracking
        tracker = get_progress_tracker()
        tracker.start_tracking()
        set_progress_stage(ProgressStage.CONNECTING, sub_stage=f"Connecting to Hugging Face Hub for {model_id}")
    
    try:
        if not is_model_downloaded(model_id):
            # Send initial status
            q.put(("status_update", f"Starting download of model {model_id}..."))
            logging.info(f"Downloading model files for {model_id}...")
            
            if has_enhanced_progress:
                set_progress_stage(ProgressStage.DOWNLOADING_MODEL, sub_stage="Getting model information")

            # Get model info to calculate total size
            api = HfApi()
            model_info = api.model_info(repo_id=model_id)
            total_model_size = sum(sibling.size for sibling in (model_info.siblings or []) if sibling.size is not None)

            q.put(("total_model_size", total_model_size))
            logging.info(f"Total model size for {model_id}: {total_model_size} bytes.")
            
            if has_enhanced_progress:
                set_progress_stage(ProgressStage.DOWNLOADING_MODEL, sub_stage="Preparing download")
                tracker.total_bytes = total_model_size
            
            TqdmToQueue.reset_overall_progress()
            TqdmToQueue.set_overall_total_size(total_model_size)
            TqdmToQueue._q = q
            TqdmToQueue._update_type = "model_download_progress"
            
            if has_enhanced_progress:
                set_progress_stage(ProgressStage.DOWNLOADING_MODEL, sub_stage="Downloading model files")
            
            # Enhanced download progress tracking
            total_files = len(model_info.siblings) if model_info.siblings else 0
            downloaded_files = 0
            
            def enhanced_progress_callback(current_file, bytes_downloaded):
                """Enhanced progress callback with file-level tracking."""
                downloaded_files += 1
                
                # Send enhanced progress update
                q.put({
                    'type': 'model_download_progress',
                    'progress': bytes_downloaded / total_model_size if total_model_size > 0 else 0,
                    'bytes_downloaded': bytes_downloaded,
                    'total_bytes': total_model_size,
                    'current_file': current_file,
                    'downloaded_files': downloaded_files,
                    'total_files': total_files,
                    'status': f"Downloading {current_file} ({downloaded_files}/{total_files})"
                })
                
                if has_enhanced_progress:
                    tracker.update_download_progress(
                        bytes_downloaded, 
                        total_model_size, 
                        current_file,
                        0.0  # Speed would be calculated externally
                    )
            
            # Download with enhanced progress tracking
            local_model_path = snapshot_download(
                repo_id=model_id,
                tqdm_class=TqdmToQueue, # type: ignore
            )
            
            if has_enhanced_progress:
                set_progress_stage(ProgressStage.DOWNLOADING_MODEL, sub_stage="Download completed")
            
            logging.info(f"Model download complete for {model_id}.")
            q.put(("status_update", f"Model download completed for {model_id}"))
        else:
            logging.info(f"Model {model_id} is already downloaded.")
            
            if has_enhanced_progress:
                set_progress_stage(ProgressStage.DOWNLOADING_MODEL, sub_stage="Model already downloaded")
            
            # Get the latest snapshot path
            model_cache_dir = get_model_cache_dir(model_id)
            snapshot_dir = os.path.join(model_cache_dir, 'snapshots')
            latest_snapshot = os.listdir(snapshot_dir)[-1]
            local_model_path = os.path.join(snapshot_dir, latest_snapshot)

        if has_enhanced_progress:
            set_progress_stage(ProgressStage.LOADING_MODEL, sub_stage="Initializing AI model")
        
        q.put(("status_update", f"Initializing model {model_id}..."))
        logging.info(f"Initializing pipeline for {model_id}...")
        # Basic compatibility check: ensure config.json has a model_type for transformers pipelines
        try:
            cfg_path = os.path.join(local_model_path, "config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as cf:
                    cfg = json.load(cf)
                if "model_type" not in cfg:
                    raise ValueError(
                        f"Model {model_id} does not appear to be a standard transformers model (missing 'model_type' in {cfg_path})."
                        " The model may require a custom loader (e.g., OpenCLIP/timm) and cannot be loaded with the default pipeline."
                    )
        except ValueError:
            raise
        except Exception:
            # If we can't inspect the config for any reason, proceed to let pipeline raise a clear error.
            pass
        if has_enhanced_progress:
            set_progress_stage(ProgressStage.LOADING_MODEL, sub_stage="Loading AI pipeline")
        
        # Basic compatibility check: ensure config.json has a model_type for transformers pipelines
        try:
            cfg_path = os.path.join(local_model_path, "config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as cf:
                    cfg = json.load(cf)
                if "model_type" not in cfg:
                    raise ValueError(
                        f"Model {model_id} does not appear to be a standard transformers model (missing 'model_type' in {cfg_path})."
                        " The model may require a custom loader (e.g., OpenCLIP/timm) and cannot be loaded with the default pipeline."
                    )
        except ValueError:
            raise
        except Exception:
            # If we can't inspect the config for any reason, proceed to let pipeline raise a clear error.
            pass
        
        # Try to load tokenizer with failover to slow tokenizer if fast fails (fixes Qwen2-VL local load issue)
        tokenizer = None
        try:
            tokenizer = AutoTokenizer.from_pretrained(local_model_path)
        except Exception:
            try:
                logging.info("Default/Fast tokenizer load failed, trying use_fast=False...")
                tokenizer = AutoTokenizer.from_pretrained(local_model_path, use_fast=False)
            except Exception as e:
                logging.warning(f"Failed to load tokenizer (fast and slow): {e}")

        if tokenizer:
            model = pipeline(task, model=local_model_path, tokenizer=tokenizer)
        else:
            model = pipeline(task, model=local_model_path)
        
        if has_enhanced_progress:
            set_progress_stage(ProgressStage.COMPLETE, sub_stage="Model loaded successfully")
        
        logging.info(f"Model pipeline loaded successfully for: {model_id}")
        q.put(("model_loaded", {"model": model, "model_name": model_id}))

    except Exception as e:
        logging.exception(f"Failed to load model: {model_id}")
        
        if has_enhanced_progress:
            get_progress_tracker().mark_error(f"Model loading failed: {e}")
        
        q.put(("error", f"Failed to load model: {e}"))


def find_models_by_task(task):
    """Synchronous helper to find models for a given task.

    Returns a tuple: (model_ids, downloaded_models)
    """
    logging.info(f"Searching for models (sync) with task: '{task}'")
    try:
        # Limit to the top N models to avoid overwhelming the UI and reduce network usage
        models = list_models(filter=task, sort="downloads", direction=-1, limit=config.MODEL_SEARCH_LIMIT)
        model_ids = [model.id for model in models or []][:config.MODEL_SEARCH_LIMIT]
        downloaded_models = [mid for mid in model_ids if is_model_downloaded(mid)]
        logging.info(f"Found {len(model_ids)} models (sync). {len(downloaded_models)} cached locally.")
        return model_ids, downloaded_models
    except Exception as e:
        logging.exception("Failed to find models (sync).")
        return [], []


def get_model_info(model_id):
    """Return the README (or a helpful message) for a model synchronously."""
    logging.info(f"Fetching README (sync) for model: {model_id}")
    try:
        readme_path = hf_hub_download(repo_id=model_id, filename="README.md")
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.warning(f"Could not retrieve README for {model_id}. Error: {e}")
        return f"Could not retrieve README for {model_id}.\n\n{e}"


def load_model(model_id, task, progress_queue=None):
    """Synchronous model loader that mirrors the behavior of the worker version.

    If `progress_queue` is provided, status updates will be posted to it using
    the same message types the GUI expects.
    Returns the initialized pipeline object.
    """
    logging.info(f"Starting synchronous model load for: {model_id}")
    try:
        q = progress_queue
        if q:
            q.put(("status_update", f"Downloading/initializing model {model_id}..."))

        if not is_model_downloaded(model_id):
            logging.info(f"Downloading model files for {model_id} (sync)...")
            api = HfApi()
            model_info = api.model_info(repo_id=model_id)
            total_model_size = sum(sibling.size for sibling in (model_info.siblings or []) if sibling.size is not None)
            if q:
                q.put(("total_model_size", total_model_size))

            TqdmToQueue.reset_overall_progress()
            TqdmToQueue.set_overall_total_size(total_model_size)
            if q:
                TqdmToQueue._q = q
                TqdmToQueue._update_type = "model_download_progress"

            local_model_path = snapshot_download(
                repo_id=model_id,
                tqdm_class=TqdmToQueue, # type: ignore
            )
            logging.info(f"Model download complete for {model_id} (sync).")
        else:
            logging.info(f"Model {model_id} is already downloaded (sync).")
            model_cache_dir = get_model_cache_dir(model_id)
            snapshot_dir = os.path.join(model_cache_dir, 'snapshots')
            latest_snapshot = os.listdir(snapshot_dir)[-1]
            local_model_path = os.path.join(snapshot_dir, latest_snapshot)

        if q:
            q.put(("status_update", f"Initializing model {model_id}..."))
        # Basic compatibility check: ensure config.json has a model_type for transformers pipelines
        try:
            cfg_path = os.path.join(local_model_path, "config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as cf:
                    cfg = json.load(cf)
                if "model_type" not in cfg:
                    raise ValueError(
                        f"Model {model_id} does not appear to be a standard transformers model (missing 'model_type' in {cfg_path})."
                        " The model may require a custom loader (e.g., OpenCLIP/timm) and cannot be loaded with the default pipeline."
                    )
        except ValueError:
            raise
        except Exception:
            # If we can't inspect the config for any reason, proceed to let pipeline raise a clear error.
            pass
        # Try to load tokenizer with failover to slow tokenizer if fast fails (fixes Qwen2-VL local load issue)
        tokenizer = None
        try:
            tokenizer = AutoTokenizer.from_pretrained(local_model_path)
        except Exception:
            try:
                logging.info("Default/Fast tokenizer load failed, trying use_fast=False...")
                tokenizer = AutoTokenizer.from_pretrained(local_model_path, use_fast=False)
            except Exception as e:
                logging.warning(f"Failed to load tokenizer (fast and slow): {e}")
        
        if tokenizer:
            model = pipeline(task, model=local_model_path, tokenizer=tokenizer)
        else:
            model = pipeline(task, model=local_model_path)

        logging.info(f"Model pipeline loaded successfully (with pre-loaded tokenizer) for: {model_id} (sync)")
        return model
        logging.info(f"Model pipeline loaded successfully for: {model_id} (sync)")
        return model

    except Exception as e:
        logging.exception(f"Failed to load model (sync): {model_id}")
        if progress_queue:
            progress_queue.put(("error", f"Failed to load model: {e}"))
        raise
