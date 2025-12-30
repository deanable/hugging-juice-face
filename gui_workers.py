"""
Worker thread functions for the Image Tagger application.
Handles background processing to keep the GUI responsive.
"""

import logging
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

import config
import huggingface_utils
import image_processing
from daminion_client import DaminionAPIError


def connect_daminion_worker(gui_instance, url, username, password):
    """Worker thread for Daminion connection.

    Args:
        gui_instance: Reference to main GUI instance
        url: Daminion server URL
        username: Username
        password: Password
    """
    logging.info(f"[GUI] ========== DAMINION CONNECTION WORKER STARTED ==========")
    logging.info(f"[GUI] URL: {url}")
    logging.info(f"[GUI] Username: {username}")

    try:
        from daminion_client import DaminionClient

        logging.info(f"[GUI] Creating DaminionClient instance...")
        client = DaminionClient(url, username, password)

        logging.info(f"[GUI] Testing connection to Daminion server...")
        status = client.test_connection()
        logging.info(f"[GUI] Connection test result: {status}")

        if status['connected']:
            logging.info(f"[GUI] ✓ Connection successful!")
            gui_instance.daminion_client = client

            logging.debug(f"[GUI] Saving connection config...")
            gui_instance.config_manager.set('daminion_url', url)
            gui_instance.config_manager.set('daminion_username', username)
            gui_instance.config_manager.save_config()

            logging.info(f"[GUI] Notifying GUI of successful connection...")
            gui_instance.q.put({'type': 'daminion_connected', 'status': status})

            try:
                logging.info(f"[GUI] Fetching shared collections...")
                cols = client.get_shared_collections(index=0, page_size=200)
                logging.info(f"[GUI] Retrieved {len(cols) if cols else 0} shared collections")
                gui_instance.q.put({'type': 'daminion_collections', 'collections': cols})
            except Exception as coll_error:
                logging.warning(f"[GUI] Failed to fetch collections: {coll_error}")

            logging.info(f"[GUI] ========== CONNECTION WORKER COMPLETE ==========")
        else:
            error_msg = status.get('error', 'Unknown error')
            logging.error(f"[GUI] ✗ Connection failed: {error_msg}")
            gui_instance.q.put({'type': 'daminion_error', 'error': error_msg})

    except Exception as e:
        logging.exception(f"[GUI] ✗ Daminion connection worker exception")
        gui_instance.q.put({'type': 'daminion_error', 'error': str(e)})


def find_models_worker(gui_instance):
    """Worker thread for finding models.

    Args:
        gui_instance: Reference to main GUI instance
    """
    try:
        task = gui_instance.model_task.get()
        model_ids, downloaded_models = huggingface_utils.find_models_by_task(task)
        gui_instance.q.put({'type': 'models_found', 'models': (model_ids, downloaded_models)})
        logging.info(f"Found {len(model_ids)} models for task {task}.")
    except Exception as e:
        logging.exception("Failed to find models.")
        gui_instance.q.put({'type': 'error', 'error': f"Failed to find models: {e}"})



def show_model_info_worker(gui_instance, model_id):
    """Worker thread for fetching model info.

    Args:
        gui_instance: Reference to main GUI instance
        model_id: Model ID to fetch info for
    """
    try:
        info = huggingface_utils.get_model_info(model_id)
        gui_instance.q.put({'type': 'model_info_found', 'info': info})
    except Exception as e:
        logging.exception(f"Failed to fetch model info for {model_id}.")
        gui_instance.q.put({'type': 'error', 'error': f"Failed to fetch model info: {e}"})


def load_model_worker(gui_instance, model_id, device=-1):
    """Worker thread for loading model.

    Args:
        gui_instance: Reference to main GUI instance
        model_id: Model ID to load
        device: Device ID (-1 for CPU, 0 for CUDA, "mps" for MPS)
    """
    try:
        task = gui_instance.model_task.get()
        token = gui_instance.config_manager.get('hf_token')
        
        # Pass device to load_model
        model = huggingface_utils.load_model(model_id, task, progress_queue=gui_instance.q, token=token, device=device)
        
        gui_instance.q.put({'type': 'model_loaded', 'model': model, 'model_name': model_id})
        logging.info(f"Model {model_id} loaded successfully on device {device}.")
    except Exception as e:
        logging.exception(f"Failed to load model {model_id}.")
        gui_instance.q.put({'type': 'error', 'error': f"Failed to load model: {e}"})


def find_local_models_worker(gui_instance):
    """Worker thread to find locally cached models.

    Args:
        gui_instance: Reference to main GUI instance
    """
    try:
        task = gui_instance.model_task.get()
        logging.info(f"Scanning local cache for models with task: '{task}'")
        local_models = huggingface_utils.find_local_models_by_task(task)
        gui_instance.q.put({'type': 'models_found', 'models': (local_models, local_models)})
    except Exception as e:
        logging.exception("Failed to find local models from cache.")
        gui_instance.q.put({'type': 'error', 'error': f"Failed to scan local model cache: {e}"})


def process_daminion_worker(gui_instance, categories, keywords, items=None, device=-1, batch_size=8, truncation=True, threshold=0.0):
    """Worker thread for processing Daminion items.

    Args:
        gui_instance: Reference to main GUI instance
        categories: List of categories for classification
        keywords: List of keywords for zero-shot
        items: Pre-filtered items list (optional)
        device: Device ID (unused here as model is already loaded with device)
        batch_size: Batch size (unused for now as we process one by one due to API latency)
        truncation: Whether to truncate inputs
        threshold: Confidence threshold
    """
    logging.info(f"[GUI] ========== DAMINION PROCESSING WORKER STARTED ==========")
    logging.info(f"[GUI] Params: Batch={batch_size}, Trunc={truncation}, Thr={threshold}")
    
    # ... (rest of Daminion logic remains mostly same, but we should use the new threshold)
    # For now, keeping the existing Daminion logic structure but updating signatures.
    # Ideally Daminion should also be batched, but that requires refactoring DaminionClient heavily.
    # We will just use the threshold in the loop.

    model_task = gui_instance.model_task.get()
    
    if not gui_instance.daminion_client:
        gui_instance.q.put({'type': 'error', 'error': "Daminion client not initialized"})
        return

    if not gui_instance.model:
        gui_instance.q.put({'type': 'error', 'error': "Model not loaded"})
        return

    try:
        # Fetch items logic...
        if items is None:
            gui_instance.q.put({'type': 'status_update', 'status': "Fetching items from Daminion..."})
            items = gui_instance.daminion_client.get_all_items_paginated(batch_size=100, max_items=None)
        
        # Flatten and validate...
        if items:
            valid_items = []
            if isinstance(items[0], list):
                for sublist in items:
                    if isinstance(sublist, list):
                        valid_items.extend(sublist)
                    else:
                        valid_items.append(sublist)
            else:
                valid_items = items
            items = [item for item in valid_items if isinstance(item, dict)]

        if not items:
            gui_instance.q.put({'type': 'error', 'error': "No valid items to process"})
            return

        gui_instance.q.put({'type': 'progress_max', 'total': len(items)})
        
        completed_count = 0
        failed_count = 0

        for idx, item in enumerate(items, 1):
            if gui_instance.stop_event.is_set():
                break

            try:
                item_id = item.get('id')
                filename = item.get('fileName', f'item_{item_id}')
                gui_instance.q.put({'type': 'status_update', 'status': f"Processing {filename}..."})
                
                thumb_path = gui_instance.daminion_client.download_thumbnail(item_id)
                if not thumb_path or not thumb_path.exists():
                    failed_count += 1
                    continue

                image = Image.open(thumb_path)
                
                # Use pipeline directly (simulating single item batch)
                # Note: Model is already on device.
                
                if model_task == config.MODEL_TASK_IMAGE_CLASSIFICATION:
                    result = gui_instance.model(image, candidate_labels=categories)
                    # Use helper
                    cat, _ = image_processing.extract_tags_from_result(result, model_task, threshold)
                    if cat:
                        logging.info(f"[GUI] ✓ Item {item_id}: Category={cat}")
                        gui_instance.daminion_client.update_item_metadata(str(item_id), category=cat)

                elif model_task == config.MODEL_TASK_ZERO_SHOT:
                    result = gui_instance.model(image, candidate_labels=keywords)
                    _, kws = image_processing.extract_tags_from_result(result, model_task, threshold)
                    if kws:
                        logging.info(f"[GUI] ✓ Item {item_id}: Keywords={kws}")
                        gui_instance.daminion_client.update_item_metadata(str(item_id), keywords=kws)

                elif model_task == config.MODEL_TASK_IMAGE_TO_TEXT:
                    # Provide prompt for VL models
                    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": "Describe the image."}]}]
                    prompt = gui_instance.model.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                    result = gui_instance.model(image, prompt=prompt, generate_kwargs={"max_new_tokens": 200})
                    _, kws = image_processing.extract_tags_from_result(result, model_task, threshold)
                    if kws:
                        logging.info(f"[GUI] ✓ Item {item_id}: Generated={kws}")
                        gui_instance.daminion_client.update_item_metadata(str(item_id), keywords=kws)

                completed_count += 1
                gui_instance.q.put({'type': 'progress', 'current': completed_count, 'total': len(items)})

            except Exception as e:
                failed_count += 1
                logging.exception(f"[GUI] Error processing item {item.get('id')}")

        gui_instance.daminion_client.cleanup_temp_files()
        gui_instance.q.put({'type': 'progress_done', 'processed_count': completed_count, 'error_count': failed_count})

    except Exception as e:
        logging.exception(f"[GUI] Daminion processing failed")
        gui_instance.q.put({'type': 'error', 'error': f"Daminion processing failed: {e}"})


def process_images_worker(gui_instance, image_files, categories, keywords, device=-1, batch_size=8, truncation=True, threshold=0.0):
    """Worker thread for processing local images using batch processing.

    Args:
        gui_instance: Reference to main GUI instance
        image_files: List of image file paths
        categories: List of categories for classification
        keywords: List of keywords for zero-shot
        device: Device ID (unused here as model is already loaded with device)
        batch_size: Batch size for inference
        truncation: Whether to truncate inputs
        threshold: Confidence threshold
    """
    logging.info(f"Image processing worker started. Batch size: {batch_size}")
    model_task = gui_instance.model_task.get()
    
    total_images = len(image_files)
    completed_count = 0
    error_count = 0
    
    gui_instance.q.put({'type': 'progress_max', 'total': total_images})
    gui_instance.q.put({'type': 'status_update', 'status': f"Processing {total_images} images..."})

    # Prepare batches
    for i in range(0, total_images, batch_size):
        if gui_instance.stop_event.is_set():
            break
            
        batch_paths = image_files[i : i + batch_size]
        batch_images = []
        valid_paths = []
        
        # Load images for batch
        for path in batch_paths:
            try:
                # Validation
                valid, _ = image_processing.validate_image(path)
                if valid:
                    # Open and convert to RGB
                    img = Image.open(path)
                    if img.mode not in ('RGB', 'RGBA', 'L'):
                        img = img.convert('RGB')
                    batch_images.append(img)
                    valid_paths.append(path)
                else:
                    error_count += 1
                    logging.warning(f"Skipping invalid image: {path}")
            except Exception as e:
                error_count += 1
                logging.error(f"Failed to load image {path}: {e}")

        if not batch_images:
            continue

        try:
            # Run inference on batch
            # Note: We pass the list of PIL images directly to the pipeline.
            # Transformers pipeline handles batching internally if we pass a list, 
            # but we are doing the chunking ourselves to update UI.
            
            gui_instance.q.put({'type': 'status_update', 'status': f"Inference on batch {i//batch_size + 1}..."})
            
            # Additional kwargs based on task
            kwargs = {"batch_size": len(batch_images), "truncation": truncation}
            
            if model_task == config.MODEL_TASK_IMAGE_CLASSIFICATION:
                kwargs["candidate_labels"] = categories
                results = gui_instance.model(batch_images, **kwargs)
                
            elif model_task == config.MODEL_TASK_ZERO_SHOT:
                kwargs["candidate_labels"] = keywords
                results = gui_instance.model(batch_images, **kwargs)
                
            elif model_task == config.MODEL_TASK_IMAGE_TO_TEXT:
                # Need prompts for each image
                messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": "Describe the image."}]}]
                prompt = gui_instance.model.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                # Pipeline call for list of inputs
                # For VL, inputs are often list of dicts or just prompt/image pairs.
                # Standard pipeline for image-to-text might just take images if no prompt needed, 
                # but for chat-based models (Llava/Qwen), we need the prompt structure.
                # It's tricky to batch prompts + images in the standard pipeline API sometimes.
                # We'll try passing list of inputs.
                inputs = [{"image": img, "prompt": prompt} for img in batch_images]
                kwargs["generate_kwargs"] = {"max_new_tokens": 200}
                results = gui_instance.model(inputs, **kwargs)

            # Process results
            for path, result in zip(valid_paths, results):
                try:
                    cat, kws = image_processing.extract_tags_from_result(result, model_task, threshold)
                    
                    if cat or kws:
                        success = image_processing.write_metadata_with_retry(path, cat, kws, gui_instance.q)
                        if success:
                            logging.info(f"Tagged {path.name}: {cat} {kws}")
                        else:
                            error_count += 1
                    else:
                        logging.info(f"No tags found for {path.name} above threshold {threshold}")
                        
                    completed_count += 1
                    
                except Exception as write_err:
                    error_count += 1
                    logging.error(f"Error writing metadata for {path}: {write_err}")

            gui_instance.q.put({'type': 'progress', 'current': completed_count, 'total': total_images})

        except Exception as e:
            logging.exception(f"Batch inference failed: {e}")
            error_count += len(batch_images)

    gui_instance.progress_tracker.complete_job()
    gui_instance.q.put({
        'type': 'progress_done', 
        'status': "Finished processing.",
        'processed_count': completed_count,
        'error_count': error_count
    })
    logging.info("Image processing worker finished.")


def refresh_daminion_collections_worker(gui_instance):
    """Worker thread to refresh shared collections.

    Args:
        gui_instance: Reference to main GUI instance
    """
    try:
        if not gui_instance.daminion_client:
            gui_instance.q.put({'type': 'error', 'error': "Daminion client not initialized"})
            return

        collections = gui_instance.daminion_client.get_shared_collections(index=0, page_size=200)
        gui_instance.q.put({'type': 'daminion_collections', 'collections': collections})
        gui_instance.q.put({'type': 'status_update', 'status': f"Found {len(collections)} shared collections on server."})
    except Exception as e:
        logging.exception("Failed to refresh collections")
        gui_instance.q.put({'type': 'error', 'error': f"Failed to fetch collections: {e}"})
