"""
Functions for processing images and writing metadata.
"""

import logging
from PIL import Image
import piexif
from iptcinfo3 import IPTCInfo

from config import STOP_WORDS

def write_metadata(image_path, category, keywords, q):
    """Writes the category and keywords to the image's IPTC and EXIF metadata."""
    try:
        logging.info(f"Writing IPTC metadata to {image_path.name}")
        info = IPTCInfo(image_path, force=True)
        if category:
            info['object name'] = category
        if keywords:
            existing_keywords = [k.decode('utf-8') for k in info['keywords']]
            for k in keywords:
                if k not in existing_keywords:
                    existing_keywords.append(k)
            info['keywords'] = existing_keywords
        info.save()
    except Exception as e:
        logging.exception(f"Failed to write IPTC metadata for {image_path.name}")
        q.put(("error", f"Could not write IPTC for {image_path.name}: {e}"))

    try:
        logging.info(f"Writing EXIF metadata to {image_path.name}")
        exif_dict = piexif.load(str(image_path))
        if category:
            exif_dict['0th'][piexif.ImageIFD.XPSubject] = category.encode('utf-16le')
        if keywords:
            existing_keywords_str = exif_dict['0th'].get(piexif.ImageIFD.XPKeywords, b'').decode('utf-16le').rstrip('\x00')
            existing_keywords = existing_keywords_str.split(';') if existing_keywords_str else []
            for k in keywords:
                if k not in existing_keywords:
                    existing_keywords.append(k)
            exif_dict['0th'][piexif.ImageIFD.XPKeywords] = ";".join(existing_keywords).encode('utf-16le')
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(image_path))
    except Exception as e:
        logging.exception(f"Failed to write EXIF metadata for {image_path.name}")
        q.put(("error", f"Could not write EXIF for {image_path.name}: {e}"))

def process_single_image(image_path, model, model_task, categories, keywords, q):
    """Processes a single image to get category and keywords."""
    logging.info(f"Processing image: {image_path}")
    q.put(("status_update", f"Processing {image_path.name}..."))
    image = Image.open(image_path)

    category = ""
    new_keywords = []

    if model_task == "image-classification":
        result = model(image, candidate_labels=categories)
        category = max(result, key=lambda x: x['score'])['label']
        logging.info(f"Found category: '{category}' for {image_path.name}")
    elif model_task == "zero-shot-image-classification":
        result = model(image, candidate_labels=keywords)
        for r in result:
            if r['score'] > 0.9:
                new_keywords.append(r['label'])
        logging.info(f"Found keywords: {new_keywords} for {image_path.name}")
    elif model_task == "image-to-text":
        result = model(image)
        generated_text = result[0]['generated_text']
        words = generated_text.lower().split()
        new_keywords = [word for word in words if word.isalpha() and word not in STOP_WORDS]
        logging.info(f"Found keywords from generated text: {new_keywords} for {image_path.name}")

    write_metadata(image_path, category, new_keywords, q)
