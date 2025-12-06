"""
Functions for processing images and writing metadata.
Enhanced with type hints, validation, and error handling.
"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Tuple, Any
from queue import Queue
from PIL import Image, UnidentifiedImageError
import piexif
from iptcinfo3 import IPTCInfo

import config

class ImageValidationError(Exception):
    """Raised when image validation fails."""
    pass

def validate_image(image_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Validate that an image file can be opened and processed.

    Args:
        image_path: Path to the image file

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> valid, error = validate_image(Path("test.jpg"))
        >>> if valid:
        ...     print("Image is valid")
    """
    try:
        if not image_path.exists():
            return False, "File does not exist"

        if not image_path.is_file():
            return False, "Path is not a file"

        if image_path.stat().st_size == 0:
            return False, "File is empty"

        if image_path.stat().st_size > config.MAX_IMAGE_SIZE_MB * 1024 * 1024:
            return False, f"File exceeds {config.MAX_IMAGE_SIZE_MB}MB limit"

        with Image.open(image_path) as img:
            img.verify()

        with Image.open(image_path) as img:
            img.load()

        return True, None

    except UnidentifiedImageError:
        return False, "Cannot identify image file"
    except PermissionError:
        return False, "Permission denied"
    except Exception as e:
        return False, f"Validation failed: {str(e)}"

def write_metadata_with_retry(
    image_path: Path,
    category: str,
    keywords: List[str],
    q: Queue,
    max_retries: int = 3,
    retry_delay: float = 0.5
) -> bool:
    """
    Write metadata to image with retry logic.

    Args:
        image_path: Path to the image file
        category: Category to write
        keywords: Keywords to write
        q: Queue for status messages
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        True if successful, False otherwise

    Example:
        >>> success = write_metadata_with_retry(
        ...     Path("image.jpg"),
        ...     "Interior",
        ...     ["bedroom", "modern"],
        ...     queue_obj
        ... )
    """
    for attempt in range(max_retries):
        try:
            return write_metadata(image_path, category, keywords, q)
        except Exception as e:
            if attempt < max_retries - 1:
                logging.warning(
                    f"Metadata write attempt {attempt + 1} failed for {image_path.name}: {e}. Retrying..."
                )
                time.sleep(retry_delay)
            else:
                logging.error(f"All metadata write attempts failed for {image_path.name}")
                q.put(("error", f"Failed to write metadata after {max_retries} attempts: {e}"))
                return False
    return False

def write_metadata(image_path: Path, category: str, keywords: List[str], q: Queue) -> bool:
    """
    Write category and keywords to the image's IPTC and EXIF metadata.

    Args:
        image_path: Path to the image file
        category: Category to write (empty string to skip)
        keywords: List of keywords to add
        q: Queue for status messages

    Returns:
        True if successful, False otherwise

    Raises:
        Exception: If metadata writing fails

    Example:
        >>> write_metadata(
        ...     Path("photo.jpg"),
        ...     "Portrait",
        ...     ["person", "outdoor"],
        ...     queue_obj
        ... )
    """
    iptc_success = False
    exif_success = False

    try:
        logging.info(f"Writing IPTC metadata to {image_path.name}")
        info = IPTCInfo(image_path, force=True)

        if category:
            info['object name'] = category

        if keywords:
            existing_keywords = [k.decode('utf-8') if isinstance(k, bytes) else k
                               for k in (info['keywords'] or [])]
            # Use set for O(1) lookups instead of O(n)
            existing_set = set(existing_keywords)
            for k in keywords:
                if k not in existing_set:
                    existing_keywords.append(k)
                    existing_set.add(k)
            info['keywords'] = existing_keywords

        info.save()
        iptc_success = True
        logging.debug(f"IPTC metadata written successfully for {image_path.name}")

    except Exception as e:
        logging.exception(f"Failed to write IPTC metadata for {image_path.name}")
        q.put(("error", f"Could not write IPTC for {image_path.name}: {e}"))

    try:
        logging.info(f"Writing EXIF metadata to {image_path.name}")
        exif_dict = piexif.load(str(image_path))

        if category:
            exif_dict['0th'][piexif.ImageIFD.XPSubject] = category.encode('utf-16le')

        if keywords:
            existing_keywords_bytes = exif_dict['0th'].get(piexif.ImageIFD.XPKeywords, b'')
            existing_keywords_str = existing_keywords_bytes.decode('utf-16le').rstrip('\x00') if existing_keywords_bytes else ''
            existing_keywords = existing_keywords_str.split(';') if existing_keywords_str else []

            # Use set for O(1) lookups instead of O(n)
            existing_set = set(existing_keywords)
            for k in keywords:
                if k not in existing_set:
                    existing_keywords.append(k)
                    existing_set.add(k)

            exif_dict['0th'][piexif.ImageIFD.XPKeywords] = ";".join(existing_keywords).encode('utf-16le')

        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(image_path))
        exif_success = True
        logging.debug(f"EXIF metadata written successfully for {image_path.name}")

    except Exception as e:
        logging.exception(f"Failed to write EXIF metadata for {image_path.name}")
        q.put(("error", f"Could not write EXIF for {image_path.name}: {e}"))

    return iptc_success or exif_success

def process_single_image(
    image_path: Path,
    model: Any,
    model_task: str,
    categories: List[str],
    keywords: List[str],
    q: Queue
) -> Tuple[bool, Optional[str]]:
    """
    Process a single image to extract category and keywords using AI model.

    Args:
        image_path: Path to the image file
        model: Loaded AI model pipeline
        model_task: Type of model task (classification, zero-shot, image-to-text)
        categories: List of candidate categories (for classification)
        keywords: List of candidate keywords (for zero-shot)
        q: Queue for status messages

    Returns:
        Tuple of (success, error_message)

    Raises:
        ImageValidationError: If image validation fails

    Example:
        >>> success, error = process_single_image(
        ...     Path("image.jpg"),
        ...     model,
        ...     "image-classification",
        ...     ["Interior", "Exterior"],
        ...     [],
        ...     queue_obj
        ... )
    """
    logging.info(f"Processing image: {image_path}")
    q.put(("status_update", f"Processing {image_path.name}..."))

    valid, error_msg = validate_image(image_path)
    if not valid:
        error_full = f"Image validation failed for {image_path.name}: {error_msg}"
        logging.error(error_full)
        q.put(("error", error_full))
        return False, error_msg

    try:
        image = Image.open(image_path)

        if image.mode not in ('RGB', 'RGBA', 'L'):
            image = image.convert('RGB')

    except Exception as e:
        error_msg = f"Failed to open image {image_path.name}: {e}"
        logging.exception(error_msg)
        q.put(("error", error_msg))
        return False, str(e)

    category = ""
    new_keywords = []

    try:
        if model_task == config.MODEL_TASK_IMAGE_CLASSIFICATION:
            result = model(image, candidate_labels=categories)
            if result:
                category = max(result, key=lambda x: x['score'])['label']
                confidence = max(result, key=lambda x: x['score'])['score']
                logging.info(f"Found category: '{category}' ({confidence:.2f}) for {image_path.name}")

        elif model_task == config.MODEL_TASK_ZERO_SHOT:
            result = model(image, candidate_labels=keywords)
            for r in result:
                if r['score'] > config.ZERO_SHOT_CONFIDENCE_THRESHOLD:
                    new_keywords.append(r['label'])
            logging.info(f"Found keywords: {new_keywords} for {image_path.name}")

        elif model_task == config.MODEL_TASK_IMAGE_TO_TEXT:
            # For VL models, providing a prompt is often necessary.
            prompt = "<|user|>\nDescribe the image.<|end|>\n<|assistant|>\n"
            result = model([{"image": image, "prompt": prompt}], generate_kwargs={"max_new_tokens": 200})
            if result and len(result) > 0:
                generated_text = result[0][0].get('generated_text', '')
                # Keywords are often comma-separated
                new_keywords = [
                    w.strip() for w in generated_text.split(',')
                    if len(w.strip()) > 2 and w.strip().lower() not in config.STOP_WORDS
                ][:config.MAX_KEYWORDS_PER_IMAGE]
                logging.info(f"Found keywords from generated text: {new_keywords} for {image_path.name}")

    except Exception as e:
        error_msg = f"Model inference failed for {image_path.name}: {e}"
        logging.exception(error_msg)
        q.put(("error", error_msg))
        return False, str(e)

    success = write_metadata_with_retry(image_path, category, new_keywords, q)

    return success, None if success else "Metadata write failed"
