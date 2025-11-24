"""
Processing report generation for image tagging operations.
Supports CSV and JSON export formats.
"""

import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

class ProcessingReport:
    """
    Generates reports for image processing operations.

    Example:
        >>> report = ProcessingReport()
        >>> report.add_result("image.jpg", "Interior", ["bedroom", "modern"], True)
        >>> report.export_csv("report.csv")
        >>> report.export_json("report.json")
    """

    def __init__(self):
        """Initialize an empty processing report."""
        self.results: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.model_name: str = ""
        self.model_task: str = ""
        self.total_images: int = 0
        self.successful: int = 0
        self.failed: int = 0

    def start_session(self, model_name: str, model_task: str, total_images: int) -> None:
        """
        Start a new processing session.

        Args:
            model_name: Name of the AI model used
            model_task: Type of task (classification, zero-shot, etc.)
            total_images: Total number of images to process
        """
        self.start_time = datetime.now()
        self.model_name = model_name
        self.model_task = model_task
        self.total_images = total_images
        self.results = []
        self.successful = 0
        self.failed = 0
        logging.info(f"Processing report session started: {model_name}, {total_images} images")

    def end_session(self) -> None:
        """End the current processing session."""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0
        logging.info(
            f"Processing report session ended: {self.successful} successful, "
            f"{self.failed} failed, {duration:.2f}s total"
        )

    def add_result(
        self,
        image_path: str,
        category: str,
        keywords: List[str],
        success: bool,
        error_message: Optional[str] = None,
        processing_time: float = 0.0,
        confidence: Optional[float] = None
    ) -> None:
        """
        Add a processing result to the report.

        Args:
            image_path: Path to the processed image
            category: Detected/assigned category
            keywords: Detected/assigned keywords
            success: Whether processing succeeded
            error_message: Error message if failed
            processing_time: Time taken to process this image (seconds)
            confidence: Confidence score (0-1) if applicable
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'image_path': image_path,
            'image_name': Path(image_path).name,
            'category': category,
            'keywords': keywords,
            'keyword_count': len(keywords),
            'success': success,
            'error_message': error_message,
            'processing_time_seconds': round(processing_time, 3),
            'confidence': round(confidence, 4) if confidence else None
        }

        self.results.append(result)

        if success:
            self.successful += 1
        else:
            self.failed += 1

        logging.debug(f"Added result for {Path(image_path).name}: success={success}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the processing session.

        Returns:
            Dictionary containing session summary statistics
        """
        duration = 0.0
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()

        total_processing_time = sum(r.get('processing_time_seconds', 0) for r in self.results)
        avg_time_per_image = total_processing_time / len(self.results) if self.results else 0

        return {
            'session_start': self.start_time.isoformat() if self.start_time else None,
            'session_end': self.end_time.isoformat() if self.end_time else None,
            'session_duration_seconds': round(duration, 2),
            'model_name': self.model_name,
            'model_task': self.model_task,
            'total_images': self.total_images,
            'processed': len(self.results),
            'successful': self.successful,
            'failed': self.failed,
            'success_rate': round(self.successful / len(self.results) * 100, 2) if self.results else 0,
            'total_processing_time_seconds': round(total_processing_time, 2),
            'average_time_per_image_seconds': round(avg_time_per_image, 3)
        }

    def export_csv(self, output_path: Path) -> bool:
        """
        Export the report to a CSV file.

        Args:
            output_path: Path where CSV file will be saved

        Returns:
            True if successful, False otherwise

        Example:
            >>> report.export_csv(Path("results.csv"))
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'timestamp', 'image_name', 'image_path', 'category',
                    'keywords', 'keyword_count', 'success', 'error_message',
                    'processing_time_seconds', 'confidence'
                ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for result in self.results:
                    row = result.copy()
                    row['keywords'] = ', '.join(row['keywords'])
                    writer.writerow(row)

            logging.info(f"Exported CSV report to {output_path}")
            return True

        except Exception as e:
            logging.exception(f"Failed to export CSV report to {output_path}")
            return False

    def export_json(self, output_path: Path, include_summary: bool = True) -> bool:
        """
        Export the report to a JSON file.

        Args:
            output_path: Path where JSON file will be saved
            include_summary: Whether to include session summary

        Returns:
            True if successful, False otherwise

        Example:
            >>> report.export_json(Path("results.json"), include_summary=True)
        """
        try:
            data = {
                'results': self.results
            }

            if include_summary:
                data['summary'] = self.get_summary()

            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2, ensure_ascii=False)

            logging.info(f"Exported JSON report to {output_path}")
            return True

        except Exception as e:
            logging.exception(f"Failed to export JSON report to {output_path}")
            return False

    def get_failed_images(self) -> List[Dict[str, Any]]:
        """
        Get list of images that failed processing.

        Returns:
            List of failed image results
        """
        return [r for r in self.results if not r['success']]

    def get_successful_images(self) -> List[Dict[str, Any]]:
        """
        Get list of images that were successfully processed.

        Returns:
            List of successful image results
        """
        return [r for r in self.results if r['success']]

    def get_images_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get all images tagged with a specific category.

        Args:
            category: Category name to filter by

        Returns:
            List of results matching the category
        """
        return [r for r in self.results if r['category'] == category]

    def get_images_with_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Get all images tagged with a specific keyword.

        Args:
            keyword: Keyword to filter by

        Returns:
            List of results containing the keyword
        """
        return [r for r in self.results if keyword in r['keywords']]

    def print_summary(self) -> None:
        """Print a formatted summary to console."""
        summary = self.get_summary()

        print("\n" + "="*60)
        print("PROCESSING REPORT SUMMARY")
        print("="*60)
        print(f"Model: {summary['model_name']}")
        print(f"Task: {summary['model_task']}")
        print(f"Duration: {summary['session_duration_seconds']}s")
        print(f"\nProcessed: {summary['processed']} / {summary['total_images']} images")
        print(f"Successful: {summary['successful']} ({summary['success_rate']}%)")
        print(f"Failed: {summary['failed']}")
        print(f"\nAverage time per image: {summary['average_time_per_image_seconds']}s")
        print("="*60 + "\n")

        if self.failed > 0:
            print("Failed images:")
            for result in self.get_failed_images():
                print(f"  - {result['image_name']}: {result['error_message']}")
            print()
