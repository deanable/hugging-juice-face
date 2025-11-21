"""
Progress tracking for image processing operations.
"""

import json
import logging
from pathlib import Path
from datetime import datetime

class ProgressTracker:
    """Tracks progress of image processing jobs."""

    def __init__(self, progress_file=None):
        if progress_file is None:
            progress_file = Path.home() / ".image_tagger_progress.json"
        self.progress_file = Path(progress_file)
        self.current_job = None

    def start_job(self, directory, total_images, model_name, model_task):
        """Start tracking a new job."""
        self.current_job = {
            "directory": str(directory),
            "total_images": total_images,
            "processed_images": [],
            "failed_images": [],
            "model_name": model_name,
            "model_task": model_task,
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        self._save()
        logging.info(f"Started progress tracking for {total_images} images in {directory}")

    def mark_processed(self, image_path):
        """Mark an image as successfully processed."""
        if self.current_job:
            self.current_job["processed_images"].append(str(image_path))
            self.current_job["last_updated"] = datetime.now().isoformat()
            self._save()

    def mark_failed(self, image_path, error_msg):
        """Mark an image as failed."""
        if self.current_job:
            self.current_job["failed_images"].append({
                "path": str(image_path),
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            })
            self.current_job["last_updated"] = datetime.now().isoformat()
            self._save()

    def complete_job(self):
        """Mark the current job as complete."""
        if self.current_job:
            self.current_job["completed_at"] = datetime.now().isoformat()
            self._save()
            logging.info(f"Job completed: {len(self.current_job['processed_images'])} processed, {len(self.current_job['failed_images'])} failed")
            self.current_job = None

    def load_job(self):
        """Load the last saved job."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    self.current_job = json.load(f)
                    if "completed_at" not in self.current_job:
                        logging.info(f"Loaded incomplete job from {self.progress_file}")
                        return self.current_job
                    else:
                        logging.info("Last job was completed.")
                        self.current_job = None
                        return None
            except Exception as e:
                logging.exception(f"Failed to load progress from {self.progress_file}")
                return None
        return None

    def get_unprocessed_images(self, all_images):
        """Get list of images that haven't been processed yet."""
        if not self.current_job:
            return all_images

        processed_set = set(self.current_job.get("processed_images", []))
        unprocessed = [img for img in all_images if str(img) not in processed_set]
        logging.info(f"Found {len(unprocessed)} unprocessed images out of {len(all_images)} total")
        return unprocessed

    def clear(self):
        """Clear the progress file."""
        try:
            if self.progress_file.exists():
                self.progress_file.unlink()
            self.current_job = None
            logging.info("Progress file cleared.")
        except Exception as e:
            logging.exception("Failed to clear progress file")

    def _save(self):
        """Save current job to file."""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_job, f, indent=2)
        except Exception as e:
            logging.exception(f"Failed to save progress to {self.progress_file}")
