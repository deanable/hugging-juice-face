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
            gui_instance.q.put(("daminion_connected", status))

            try:
                logging.info(f"[GUI] Fetching shared collections...")
                cols = client.get_shared_collections(index=0, page_size=200)
                logging.info(f"[GUI] Retrieved {len(cols) if cols else 0} shared collections")
                gui_instance.q.put(("daminion_collections", cols))
            except Exception as coll_error:
                logging.warning(f"[GUI] Failed to fetch collections: {coll_error}")

            logging.info(f"[GUI] ========== CONNECTION WORKER COMPLETE ==========")
        else:
            error_msg = status.get('error', 'Unknown error')
            logging.error(f"[GUI] ✗ Connection failed: {error_msg}")
            gui_instance.q.put(("daminion_error", error_msg))

    except Exception as e:
        logging.exception(f"[GUI] ✗ Daminion connection worker exception")
        gui_instance.q.put(("daminion_error", str(e)))


def find_models_worker(gui_instance):
    """Worker thread for finding models.

    Args:
        gui_instance: Reference to main GUI instance
    """
    try:
        task = gui_instance.model_task.get()
        model_ids, downloaded_models = huggingface_utils.find_models_by_task(task)
        gui_instance.q.put(("models_found", (model_ids, downloaded_models)))
        logging.info(f"Found {len(model_ids)} models for task {task}.")
    except Exception as e:
        logging.exception("Failed to find models.")
        gui_instance.q.put(("error", f"Failed to find models: {e}"))


def show_model_info_worker(gui_instance, model_id):
    """Worker thread for fetching model info.

    Args:
        gui_instance: Reference to main GUI instance
        model_id: Model ID to fetch info for
    """
    try:
        info = huggingface_utils.get_model_info(model_id)
        gui_instance.q.put(("model_info_found", info))
    except Exception as e:
        logging.exception(f"Failed to fetch model info for {model_id}.")
        gui_instance.q.put(("error", f"Failed to fetch model info: {e}"))


def load_model_worker(gui_instance, model_id):
    """Worker thread for loading model.

    Args:
        gui_instance: Reference to main GUI instance
        model_id: Model ID to load
    """
    try:
        task = gui_instance.model_task.get()
        model = huggingface_utils.load_model(model_id, task, progress_queue=gui_instance.q)
        gui_instance.q.put(("model_loaded", model))
        logging.info(f"Model {model_id} loaded successfully.")
    except Exception as e:
        logging.exception(f"Failed to load model {model_id}.")
        gui_instance.q.put(("error", f"Failed to load model: {e}"))


def find_local_models_worker(gui_instance):
    """Worker thread to find locally cached models.

    Args:
        gui_instance: Reference to main GUI instance
    """
    try:
        task = gui_instance.model_task.get()
        logging.info(f"Scanning local cache for models with task: '{task}'")
        local_models = huggingface_utils.find_local_models_by_task(task)
        gui_instance.q.put(("models_found", (local_models, local_models)))
    except Exception as e:
        logging.exception("Failed to find local models from cache.")
        gui_instance.q.put(("error", f"Failed to scan local model cache: {e}"))


def process_daminion_worker(gui_instance, categories, keywords, items=None):
    """Worker thread for processing Daminion items.

    Args:
        gui_instance: Reference to main GUI instance
        categories: List of categories for classification
        keywords: List of keywords for zero-shot
        items: Pre-filtered items list (optional)
    """
    logging.info(f"[GUI] ========== DAMINION PROCESSING WORKER STARTED ==========")
    logging.info(f"[GUI] Categories: {categories}")
    logging.info(f"[GUI] Keywords: {keywords}")
    logging.info(f"[GUI] Pre-filtered items: {len(items) if items else 'None (will fetch all)'}")

    model_task = gui_instance.model_task.get()
    logging.info(f"[GUI] Model task: {model_task}")

    if not gui_instance.daminion_client:
        logging.error(f"[GUI] ✗ Daminion client not initialized!")
        gui_instance.q.put(("error", "Daminion client not initialized"))
        return

    if not gui_instance.model:
        logging.error(f"[GUI] ✗ Model not loaded!")
        gui_instance.q.put(("error", "Model not loaded"))
        return

    try:
        if items is None:
            logging.info(f"[GUI] No pre-filtered items, fetching all from Daminion...")
            gui_instance.q.put(("status_update", "Fetching items from Daminion..."))
            items = gui_instance.daminion_client.get_all_items_paginated(batch_size=100, max_items=None)
            logging.info(f"[GUI] ✓ Fetched {len(items)} items from Daminion")

        if not items:
            logging.error(f"[GUI] ✗ No items retrieved from Daminion")
            gui_instance.q.put(("error", "No items retrieved from Daminion"))
            return

        # Ensure items is a list, even if the API call returned None
        if items is None:
            items = []

        # Validate and flatten items
        if items and isinstance(items[0], list):
            logging.warning(f"[GUI] Items is a list of lists, flattening...")
            flat_items = []
            for sublist in items:
                if isinstance(sublist, list):
                    flat_items.extend(sublist)
                else:
                    flat_items.append(sublist)
            items = flat_items

        valid_items = [item for item in items if isinstance(item, dict)]
        items = valid_items
        logging.info(f"[GUI] Valid items after filtering: {len(items)}")

        if not items:
            logging.error(f"[GUI] No valid items after validation")
            gui_instance.q.put(("error", "No valid items to process"))
            return

        gui_instance.q.put(("progress_max", len(items)))
        gui_instance.q.put(("status_update", f"Processing {len(items)} items..."))

        completed_count = 0
        failed_count = 0

        logging.info(f"[GUI] ========== STARTING ITEM PROCESSING LOOP ==========")

        for idx, item in enumerate(items, 1):
            if gui_instance.stop_event.is_set():
                logging.warning(f"[GUI] Stop event detected, aborting processing")
                break

            try:
                item_id = item.get('id')
                filename = item.get('fileName', f'item_{item_id}')

                logging.info(f"[GUI] --- Processing item {idx}/{len(items)}: {filename} (ID: {item_id}) ---")
                gui_instance.q.put(("status_update", f"Processing {filename}..."))

                thumb_path = gui_instance.daminion_client.download_thumbnail(item_id)

                if not thumb_path or not thumb_path.exists():
                    logging.error(f"[GUI] ✗ Failed to download thumbnail for item {item_id}")
                    failed_count += 1
                    continue

                image = Image.open(thumb_path)
                result = None

                if model_task == config.MODEL_TASK_IMAGE_CLASSIFICATION:
                    result = gui_instance.model(image, candidate_labels=categories)
                    if result:
                        category = result[0]['label']
                        confidence = result[0]['score']
                        logging.info(f"[GUI] ✓ Item {item_id}: Category={category} (confidence={confidence:.2f})")
                        gui_instance.daminion_client.update_item_metadata(str(item_id), category=category)

                elif model_task == config.MODEL_TASK_ZERO_SHOT:
                    result = gui_instance.model(image, candidate_labels=keywords)
                    if result:
                        detected_keywords = [r['label'] for r in result if r['score'] > 0.9]
                        if detected_keywords:
                            logging.info(f"[GUI] ✓ Item {item_id}: Keywords={detected_keywords}")
                            gui_instance.daminion_client.update_item_metadata(
                                str(item_id), keywords=detected_keywords
                            )

                elif model_task == config.MODEL_TASK_IMAGE_TO_TEXT:
                    # For VL models like Qwen, providing a prompt is often necessary.
                    # We pass the image and a generic prompt to guide the generation.
                    prompt = "<|user|>\nDescribe the image.<|end|>\n<|assistant|>\n"
                    result = gui_instance.model([{"image": image, "prompt": prompt}], generate_kwargs={"max_new_tokens": 200})
                    if result and len(result) > 0:
                        generated_text = result[0][0].get('generated_text', '')
                        generated_keywords = [w.strip() for w in generated_text.split(',') if len(w.strip()) > 2][:15]
                        logging.info(f"[GUI] ✓ Item {item_id}: Generated keywords={generated_keywords}")
                        gui_instance.daminion_client.update_item_metadata(
                            str(item_id), keywords=generated_keywords
                        )

                completed_count += 1
                logging.info(f"[GUI] ✓ Item {idx}/{len(items)} processed successfully")
                gui_instance.q.put(("progress", completed_count))

            except Exception as e:
                failed_count += 1
                logging.exception(f"[GUI] ✗ Error processing Daminion item {item.get('id')}")
                gui_instance.q.put(("error", f"Failed to process item: {e}"))

        logging.info(f"[GUI] ========== ITEM PROCESSING LOOP COMPLETE ==========")
        logging.info(f"[GUI] Total processed: {completed_count}")
        logging.info(f"[GUI] Total failed: {failed_count}")

        gui_instance.daminion_client.cleanup_temp_files()
        gui_instance.q.put(("progress_done", f"Finished processing {completed_count} Daminion items."))
        logging.info(f"[GUI] ========== DAMINION PROCESSING WORKER COMPLETE ==========")

    except Exception as e:
        logging.exception(f"[GUI] ✗ CRITICAL: Daminion processing worker failed")
        gui_instance.q.put(("error", f"Daminion processing failed: {e}"))


def process_images_worker(gui_instance, image_files, categories, keywords):
    """Worker thread for processing local images.

    Args:
        gui_instance: Reference to main GUI instance
        image_files: List of image file paths
        categories: List of categories for classification
        keywords: List of keywords for zero-shot
    """
    logging.info("Image processing worker started.")
    model_task = gui_instance.model_task.get()
    max_workers = gui_instance.config_manager.get('max_concurrent_workers', 4)

    completed_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_image = {
            executor.submit(
                image_processing.process_single_image,
                image_path, gui_instance.model, model_task, categories, keywords, gui_instance.q
            ): image_path for image_path in image_files
        }

        for future in as_completed(future_to_image):
            image_path = future_to_image[future]
            start_time = time.time()
            completed_count += 1
            gui_instance.q.put(("progress", completed_count))

            try:
                success, error = future.result()
                processing_time = time.time() - start_time

                if success:
                    gui_instance.progress_tracker.mark_processed(image_path)
                    gui_instance.report.add_result(
                        str(image_path), "", [], True, None, processing_time
                    )
                else:
                    error_msg = error or "Unknown error"
                    gui_instance.progress_tracker.mark_failed(image_path, error_msg)
                    gui_instance.report.add_result(
                        str(image_path), "", [], False, error_msg, processing_time
                    )

            except Exception as e:
                logging.exception(f"Error processing {image_path.name} in worker.")
                error_msg = str(e)
                processing_time = time.time() - start_time

                gui_instance.progress_tracker.mark_failed(image_path, error_msg)
                gui_instance.report.add_result(
                    str(image_path), "", [], False, error_msg, processing_time
                )
                gui_instance.q.put(("error", f"Failed to process {image_path.name}: {e}"))

    gui_instance.progress_tracker.complete_job()
    gui_instance.q.put(("progress_done", "Finished processing."))
    logging.info("Image processing worker finished.")


def refresh_daminion_collections_worker(gui_instance):
    """Worker thread to refresh shared collections.

    Args:
        gui_instance: Reference to main GUI instance
    """
    try:
        if not gui_instance.daminion_client:
            gui_instance.q.put(("error", "Daminion client not initialized"))
            return

        collections = gui_instance.daminion_client.get_shared_collections(index=0, page_size=200)
        gui_instance.q.put(("daminion_collections", collections))
        gui_instance.q.put(("status_update", f"Found {len(collections)} shared collections on server."))
    except Exception as e:
        logging.exception("Failed to refresh collections")
        gui_instance.q.put(("error", f"Failed to fetch collections: {e}"))
