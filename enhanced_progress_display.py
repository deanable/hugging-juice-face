"""
Enhanced progress display for the modern CustomTkinter GUI.
Provides granular, accurate progress indication with detailed staging.
"""

import customtkinter as ctk
from typing import Optional, Callable
import time
from enhanced_progress import (
    GranularProgress, ProgressStage, EnhancedProgressTracker,
    get_current_progress, get_progress_tracker
)


class EnhancedProgressDisplay(ctk.CTkFrame):
    """Enhanced progress display with granular stages and detailed metrics."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Progress tracking
        self.progress_tracker: Optional[EnhancedProgressTracker] = None
        self.update_callback: Optional[Callable] = None
        self.last_update_time = 0
        self.update_interval = 100  # ms
        
        # Create UI components
        self._create_progress_ui()
        
        # Start update loop
        self.after(self.update_interval, self._update_progress_display)
    
    def _create_progress_ui(self):
        """Create the enhanced progress UI components."""
        
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text="📊 Enhanced Progress Monitor",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.title_label.pack(anchor="w", padx=20, pady=(15, 10))
        
        # Main progress bar
        self.main_progress_bar = ctk.CTkProgressBar(self)
        self.main_progress_bar.pack(fill="x", padx=40, pady=(0, 5))
        self.main_progress_bar.set(0)
        
        # Progress percentage and stage
        self.progress_info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_info_frame.pack(fill="x", padx=40, pady=(0, 15))
        
        self.percentage_label = ctk.CTkLabel(
            self.progress_info_frame,
            text="0.0%",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.percentage_label.pack(side="left")
        
        self.stage_label = ctk.CTkLabel(
            self.progress_info_frame,
            text="Idle",
            text_color="gray"
        )
        self.stage_label.pack(side="right")
        
        # Detailed progress information
        self.details_frame = ctk.CTkFrame(self)
        self.details_frame.pack(fill="both", expand=True, padx=40, pady=(0, 15))
        
        # Current operation info
        self.operation_frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        self.operation_frame.pack(fill="x", padx=15, pady=(10, 5))
        
        self.current_operation_label = ctk.CTkLabel(
            self.operation_frame,
            text="🎯 Current Operation: Ready",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.current_operation_label.pack(anchor="w")
        
        self.operation_details_label = ctk.CTkLabel(
            self.operation_frame,
            text="Waiting to start...",
            text_color="gray",
            wraplength=600,
            justify="left"
        )
        self.operation_details_label.pack(anchor="w", pady=(2, 0))
        
        # Progress statistics
        self.stats_frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=15, pady=(5, 10))
        
        # Left column stats
        self.stats_left_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.stats_left_frame.pack(side="left", fill="x", expand=True)
        
        self.progress_label = ctk.CTkLabel(
            self.stats_left_frame,
            text="📈 Progress: 0/0 items",
            font=ctk.CTkFont(size=11)
        )
        self.progress_label.pack(anchor="w")
        
        self.elapsed_label = ctk.CTkLabel(
            self.stats_left_frame,
            text="⏱️ Elapsed: 0.0s",
            font=ctk.CTkFont(size=11)
        )
        self.elapsed_label.pack(anchor="w", pady=(2, 0))
        
        # Right column stats
        self.stats_right_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.stats_right_frame.pack(side="right", fill="x")
        
        self.remaining_label = ctk.CTkLabel(
            self.stats_right_frame,
            text="⏳ Remaining: --",
            font=ctk.CTkFont(size=11)
        )
        self.remaining_label.pack(anchor="e")
        
        self.speed_label = ctk.CTkLabel(
            self.stats_right_frame,
            text="🚀 Speed: --",
            font=ctk.CTkFont(size=11)
        )
        self.speed_label.pack(anchor="e", pady=(2, 0))
        
        # Stage-specific progress bars
        self.stage_progress_frame = ctk.CTkFrame(self)
        self.stage_progress_frame.pack(fill="x", padx=40, pady=(0, 10))
        
        self.stage_progress_label = ctk.CTkLabel(
            self.stage_progress_frame,
            text="🎭 Stage Progress:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.stage_progress_label.pack(anchor="w", padx=15, pady=(10, 5))
        
        self.stage_progress_bar = ctk.CTkProgressBar(self.stage_progress_frame)
        self.stage_progress_bar.pack(fill="x", padx=15, pady=(0, 10))
        self.stage_progress_bar.set(0)
        
        self.stage_status_label = ctk.CTkLabel(
            self.stage_progress_frame,
            text="No active stage",
            text_color="gray",
            font=ctk.CTkFont(size=10)
        )
        self.stage_status_label.pack(anchor="w", padx=15, pady=(0, 10))
        
        # Download progress (for model downloads)
        self.download_frame = ctk.CTkFrame(self)
        self.download_frame.pack(fill="x", padx=40, pady=(0, 10))
        
        self.download_label = ctk.CTkLabel(
            self.download_frame,
            text="📥 Download Progress:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.download_label.pack(anchor="w", padx=15, pady=(10, 5))
        
        self.download_progress_bar = ctk.CTkProgressBar(self.download_frame)
        self.download_progress_bar.pack(fill="x", padx=15, pady=(0, 5))
        self.download_progress_bar.set(0)
        
        self.download_info_label = ctk.CTkLabel(
            self.download_frame,
            text="No downloads in progress",
            text_color="gray",
            font=ctk.CTkFont(size=10)
        )
        self.download_info_label.pack(anchor="w", padx=15, pady=(0, 10))
        
        # Processing sub-stages (for image processing)
        self.sub_stages_frame = ctk.CTkFrame(self)
        self.sub_stages_frame.pack(fill="x", padx=40, pady=(0, 10))
        
        self.sub_stages_label = ctk.CTkLabel(
            self.sub_stages_frame,
            text="🔄 Processing Sub-Stages:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.sub_stages_label.pack(anchor="w", padx=15, pady=(10, 5))
        
        # Sub-stage progress indicators
        self.sub_stages_list_frame = ctk.CTkFrame(self.sub_stages_frame, fg_color="transparent")
        self.sub_stages_list_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.sub_stage_items = {}
        sub_stage_names = [
            "downloading_thumbnail", "loading_image", "ai_inference", 
            "extracting_results", "updating_metadata"
        ]
        
        for i, stage_name in enumerate(sub_stage_names):
            stage_frame = ctk.CTkFrame(self.sub_stages_list_frame, fg_color="transparent")
            stage_frame.pack(fill="x", pady=1)
            
            stage_progress = ctk.CTkProgressBar(stage_frame, height=8)
            stage_progress.pack(fill="x", padx=(0, 10))
            stage_progress.set(0)
            
            stage_label = ctk.CTkLabel(
                stage_frame,
                text=f"  {stage_name.replace('_', ' ').title()}: 0%",
                font=ctk.CTkFont(size=9),
                anchor="w"
            )
            stage_label.pack(fill="x")
            
            self.sub_stage_items[stage_name] = {
                'progress': stage_progress,
                'label': stage_label,
                'active': False
            }
    
    def set_progress_tracker(self, tracker: EnhancedProgressTracker):
        """Set the progress tracker to monitor."""
        self.progress_tracker = tracker
    
    def set_update_callback(self, callback: Callable[[GranularProgress], None]):
        """Set callback for progress updates."""
        self.update_callback = callback
    
    def _update_progress_display(self):
        """Update the progress display with current information."""
        try:
            current_progress = get_current_progress()
            
            # Rate limit updates to avoid UI lag
            current_time = time.time() * 1000  # Convert to ms
            if current_time - self.last_update_time < self.update_interval:
                self.after(self.update_interval, self._update_progress_display)
                return
            
            self.last_update_time = current_time
            
            # Update main progress bar
            self.main_progress_bar.set(current_progress.percentage / 100.0)
            self.percentage_label.configure(text=f"{current_progress.percentage:.1f}%")
            
            # Update stage information
            self._update_stage_display(current_progress)
            
            # Update operation details
            self._update_operation_display(current_progress)
            
            # Update statistics
            self._update_statistics_display(current_progress)
            
            # Update stage-specific progress
            self._update_stage_progress(current_progress)
            
            # Update download progress
            self._update_download_progress(current_progress)
            
            # Update processing sub-stages
            self._update_processing_sub_stages(current_progress)
            
            # Call update callback if set
            if self.update_callback:
                self.update_callback(current_progress)
            
        except Exception as e:
            print(f"Error updating progress display: {e}")
        
        # Schedule next update
        self.after(self.update_interval, self._update_progress_display)
    
    def _update_stage_display(self, progress: GranularProgress):
        """Update stage information display."""
        stage_names = {
            ProgressStage.IDLE: "🟢 Idle",
            ProgressStage.CONNECTING: "🔗 Connecting",
            ProgressStage.DOWNLOADING_MODEL: "📥 Downloading Model",
            ProgressStage.LOADING_MODEL: "⚡ Loading Model",
            ProgressStage.INITIALIZING: "🔧 Initializing",
            ProgressStage.PROCESSING_IMAGES: "🖼️ Processing Images",
            ProgressStage.ANALYZING_IMAGE: "🤖 AI Analysis",
            ProgressStage.APPLYING_TAGS: "🏷️ Applying Tags",
            ProgressStage.UPDATING_METADATA: "💾 Updating Metadata",
            ProgressStage.FINALIZING: "🎯 Finalizing",
            ProgressStage.COMPLETE: "✅ Complete",
            ProgressStage.ERROR: "❌ Error"
        }
        
        stage_text = stage_names.get(progress.stage, progress.stage.value)
        if progress.sub_stage:
            stage_text += f" - {progress.sub_stage}"
        
        self.stage_label.configure(text=stage_text)
        
        # Color coding based on stage
        if progress.stage == ProgressStage.COMPLETE:
            color = "green"
        elif progress.stage == ProgressStage.ERROR:
            color = "red"
        elif progress.stage in [ProgressStage.PROCESSING_IMAGES, ProgressStage.DOWNLOADING_MODEL]:
            color = "blue"
        else:
            color = "gray"
        
        self.stage_label.configure(text_color=color)
    
    def _update_operation_display(self, progress: GranularProgress):
        """Update operation details display."""
        if progress.message:
            self.current_operation_label.configure(text=f"🎯 Current Operation: {progress.message}")
        
        # Detailed operation info based on current stage
        if progress.stage == ProgressStage.DOWNLOADING_MODEL:
            if progress.total_bytes and progress.bytes_downloaded:
                downloaded_mb = progress.bytes_downloaded / (1024 * 1024)
                total_mb = progress.total_bytes / (1024 * 1024)
                self.operation_details_label.configure(
                    text=f"Downloading {progress.current_file} ({downloaded_mb:.1f}/{total_mb:.1f} MB)"
                )
        
        elif progress.stage == ProgressStage.PROCESSING_IMAGES:
            if progress.total > 0:
                percentage = (progress.current / progress.total) * 100
                self.operation_details_label.configure(
                    text=f"Processing image {progress.current}/{progress.total} ({percentage:.1f}%)"
                )
        
        elif progress.stage == ProgressStage.ANALYZING_IMAGE:
            self.operation_details_label.configure(
                text=f"Running AI analysis on {progress.current_file or 'current image'}"
            )
        
        elif progress.stage == ProgressStage.UPDATING_METADATA:
            self.operation_details_label.configure(
                text=f"Updating metadata for item {progress.current}/{progress.total}"
            )
    
    def _update_statistics_display(self, progress: GranularProgress):
        """Update statistics display."""
        # Progress info
        if progress.total > 0:
            self.progress_label.configure(text=f"📈 Progress: {progress.current}/{progress.total} items")
        else:
            self.progress_label.configure(text="📈 Progress: --")
        
        # Elapsed time
        elapsed_text = f"⏱️ Elapsed: {progress.elapsed_seconds:.1f}s"
        self.elapsed_label.configure(text=elapsed_text)
        
        # Remaining time
        if progress.estimated_remaining_seconds:
            remaining = progress.estimated_remaining_seconds
            if remaining < 60:
                remaining_text = f"⏳ Remaining: {remaining:.1f}s"
            elif remaining < 3600:
                remaining_text = f"⏳ Remaining: {remaining/60:.1f}m"
            else:
                hours = remaining / 3600
                minutes = (remaining % 3600) / 60
                remaining_text = f"⏳ Remaining: {hours:.1f}h {minutes:.1f}m"
        else:
            remaining_text = "⏳ Remaining: --"
        
        self.remaining_label.configure(text=remaining_text)
        
        # Speed information
        if progress.speed_bps:
            if self.progress_tracker and self.progress_tracker.current_stage == ProgressStage.DOWNLOADING_MODEL:
                # Download speed
                speed_mbps = progress.speed_bps / (1024 * 1024)
                speed_text = f"🚀 Speed: {speed_mbps:.1f} MB/s"
            else:
                # Processing speed
                speed_text = f"🚀 Speed: {progress.speed_bps:.2f} items/s"
            self.speed_label.configure(text=speed_text)
        else:
            self.speed_label.configure(text="🚀 Speed: --")
    
    def _update_stage_progress(self, progress: GranularProgress):
        """Update stage-specific progress bar."""
        if progress.stage in [ProgressStage.PROCESSING_IMAGES, ProgressStage.ANALYZING_IMAGE, 
                             ProgressStage.DOWNLOADING_MODEL, ProgressStage.LOADING_MODEL]:
            
            # Calculate stage-specific progress
            if progress.stage == ProgressStage.PROCESSING_IMAGES and progress.total > 0:
                stage_progress = progress.current / progress.total
            elif progress.stage == ProgressStage.DOWNLOADING_MODEL and progress.total_bytes:
                stage_progress = progress.bytes_downloaded / progress.total_bytes
            else:
                # Use estimated progress for other stages
                elapsed = time.time() - (self.progress_tracker.stage_start_time or time.time())
                stage_progress = min(elapsed / 5.0, 1.0)  # Assume 5 seconds max for setup stages
            
            self.stage_progress_bar.set(stage_progress)
            self.stage_status_label.configure(
                text=f"{progress.stage.value}: {stage_progress * 100:.1f}%",
                text_color="blue"
            )
        else:
            self.stage_progress_bar.set(0)
            self.stage_status_label.configure(
                text="No active stage",
                text_color="gray"
            )
    
    def _update_download_progress(self, progress: GranularProgress):
        """Update download-specific progress display."""
        if progress.stage == ProgressStage.DOWNLOADING_MODEL and progress.total_bytes:
            # Show download progress
            self.download_frame.pack(fill="x", padx=40, pady=(0, 10))
            
            self.download_progress_bar.set(progress.bytes_downloaded / progress.total_bytes)
            
            downloaded_mb = progress.bytes_downloaded / (1024 * 1024)
            total_mb = progress.total_bytes / (1024 * 1024)
            percentage = (progress.bytes_downloaded / progress.total_bytes) * 100
            
            download_info = f"{progress.current_file or 'model files'}: {downloaded_mb:.1f}/{total_mb:.1f} MB ({percentage:.1f}%)"
            self.download_info_label.configure(text=download_info)
        else:
            # Hide download progress when not downloading
            self.download_frame.pack_forget()
    
    def _update_processing_sub_stages(self, progress: GranularProgress):
        """Update processing sub-stage indicators."""
        if progress.stage == ProgressStage.PROCESSING_IMAGES:
            # Show sub-stages when processing
            self.sub_stages_frame.pack(fill="x", padx=40, pady=(0, 10))
            
            # Highlight current sub-stage and show its progress
            for stage_name, items in self.sub_stage_items.items():
                is_active = (self.progress_tracker and 
                           self.progress_tracker.current_processing_sub_stage == stage_name)
                
                items['active'] = is_active
                
                if is_active and self.progress_tracker:
                    # Show progress for active sub-stage
                    sub_progress = self.progress_tracker.processing_sub_stage_progress / 100.0
                    items['progress'].set(sub_progress)
                    items['label'].configure(
                        text=f"  {stage_name.replace('_', ' ').title()}: {sub_progress * 100:.1f}%",
                        text_color="blue"
                    )
                else:
                    # Show completion for completed sub-stages
                    items['progress'].set(1.0 if not is_active else 0.0)
                    items['label'].configure(
                        text=f"  {stage_name.replace('_', ' ').title()}: {'✅' if not is_active else '0%'}",
                        text_color="green" if not is_active else "gray"
                    )
        else:
            # Hide sub-stages when not processing
            self.sub_stages_frame.pack_forget()


def create_enhanced_progress_display(parent) -> EnhancedProgressDisplay:
    """Create an enhanced progress display widget."""
    return EnhancedProgressDisplay(parent)


def setup_enhanced_progress_monitoring(gui_instance, progress_display: EnhancedProgressDisplay):
    """Setup enhanced progress monitoring for a GUI instance."""
    # Get the global progress tracker
    tracker = get_progress_tracker()
    progress_display.set_progress_tracker(tracker)
    
    # Setup callback for GUI updates
    def on_progress_update(progress: GranularProgress):
        # Update GUI status indicators
        if hasattr(gui_instance, 'status_label') and gui_instance.status_label:
            status_text = f"🎯 {progress.message}" if progress.message else "Ready"
            gui_instance.status_label.configure(text=status_text)
        
        # Update main progress bar if available
        if hasattr(gui_instance, 'progress_bar') and gui_instance.progress_bar:
            gui_instance.progress_bar.set(progress.percentage / 100.0)
        
        # Update progress label if available
        if hasattr(gui_instance, 'progress_label') and gui_instance.progress_label:
            if progress.total > 0:
                progress_text = f"Processing: {progress.current}/{progress.total} images"
                if progress.current_file:
                    progress_text += f" | {progress.current_file}"
                gui_instance.progress_label.configure(text=progress_text)
        
        # Update time label if available
        if hasattr(gui_instance, 'time_label') and gui_instance.time_label:
            time_text = f"⏱️ Time: {progress.elapsed_seconds:.1f}s"
            gui_instance.time_label.configure(text=time_text)
    
    progress_display.set_update_callback(on_progress_update)
    return tracker