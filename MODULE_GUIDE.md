# Module Organization Guide

## Quick Reference

This guide helps you find where specific functionality is located after the refactoring.

## GUI Modules

### gui_main.py (648 lines)
**Main application window and coordination**

Contains:
- `ImageTaggerGUI` - Main window class
- Queue processing (`process_queue()`)
- Menu handlers (cache, reports)
- Worker thread launchers
- State management

**When to edit:**
- Modifying main window structure
- Adding new menu items
- Changing queue message handling
- Adding new worker thread launchers

---

### gui_steps.py (425 lines)
**UI component creation**

Contains:
- `CollapsiblePane` - Collapsible widget class
- `create_step1_source()` - Image source selection UI
- `create_step2_model()` - Model selection UI
- `create_step3_config()` - Configuration UI
- `create_step4_process()` - Processing controls UI
- `create_progress_section()` - Progress display UI

**When to edit:**
- Changing step layouts
- Adding new UI widgets to steps
- Modifying field labels or text
- Adjusting UI spacing/styling

---

### gui_workers.py (336 lines)
**Background worker threads**

Contains:
- `connect_daminion_worker()` - Daminion connection
- `find_models_worker()` - Model search
- `show_model_info_worker()` - Model info fetch
- `load_model_worker()` - Model loading
- `process_daminion_worker()` - Daminion item processing
- `process_images_worker()` - Local image processing
- `refresh_daminion_collections_worker()` - Collection refresh

**When to edit:**
- Changing background task logic
- Adding new worker functions
- Modifying processing algorithms
- Changing thread behavior

---

### gui_handlers.py (349 lines)
**Event handlers and utilities**

Contains:
- `filter_local_images()` - Image filtering by scope
- `filter_daminion_items()` - Daminion item filtering
- `scan_image_directory()` - Efficient directory scanning
- `update_step_states()` - UI state management
- `update_task_description()` - Task description updates
- `calculate_time_remaining()` - ETA calculation
- Event handlers: `on_model_task_change()`, `on_mode_change()`, `on_scope_change()`
- Selection handlers: `select_directory()`, `select_collection()`

**When to edit:**
- Changing event handling logic
- Modifying UI state updates
- Adding new filtering logic
- Changing utility functions

---

## Core Modules

### daminion_client.py (24KB)
**Daminion DAMS API client**

Key Features:
- ✅ Context manager support (`with` statement)
- ✅ Automatic resource cleanup with `atexit`
- ✅ Rate limiting (configurable)
- ✅ Batch processing
- ✅ Specific exception types

Exception Types:
- `DaminionAPIError` - Base exception
- `DaminionAuthenticationError` - Auth failures
- `DaminionNetworkError` - Network issues
- `DaminionRateLimitError` - Rate limit exceeded

Key Methods:
- `authenticate()` - Login to server
- `get_media_items()` - Fetch items by ID range
- `get_all_items_paginated()` - Fetch all with pagination
- `get_untagged_items()` - Fetch untagged items
- `get_flagged_items()` - Fetch flagged items
- `get_shared_collections()` - List collections
- `get_shared_collection_items()` - Items from collection
- `batch_update_tags()` - Update multiple items (with batching)
- `update_item_metadata()` - Update single item
- `download_thumbnail()` - Download image thumbnail
- `cleanup_temp_files()` - Clean cached thumbnails

Usage:
```python
# With context manager (recommended)
with DaminionClient(url, user, pass) as client:
    items = client.get_untagged_items()

# Manual cleanup
client = DaminionClient(url, user, pass)
try:
    items = client.get_untagged_items()
finally:
    client.cleanup_temp_files()
```

---

### image_processing.py (9.5KB)
**Image processing and metadata writing**

Key Features:
- ✅ Validation before processing
- ✅ Retry logic
- ✅ IPTC and EXIF metadata support
- ✅ Optimized keyword deduplication (O(1) lookups)

Functions:
- `validate_image()` - Pre-processing validation
- `write_metadata()` - Write metadata to image
- `write_metadata_with_retry()` - With retry logic
- `process_single_image()` - Full processing pipeline

Exception Types:
- `ImageValidationError` - Validation failures

---

## Supporting Modules

### config.py
**Application configuration constants**

Contains:
- App settings (name, geometry)
- Model search settings
- Image processing settings
- Network settings
- Cache settings
- Stop words list

### config_manager.py
**User preferences manager**

Manages:
- Last used model
- Default categories/keywords
- Directory history
- Processing settings

Stored in: `~/.image_tagger_config.json`

### progress_tracker.py
**Job progress tracking**

Manages:
- Job state (started, processed, failed)
- Resume functionality
- Progress persistence

Stored in: `~/.image_tagger_progress.json`

### report_generator.py
**Processing reports**

Features:
- CSV export
- JSON export
- Summary statistics
- Failed image tracking

### huggingface_utils.py
**Hugging Face model utilities**

Functions:
- Model search
- Model download with progress
- Model info retrieval
- Cache management

### logging_config.py
**Logging configuration**

Features:
- File and console logging
- Rotating file handler (10MB, 5 backups)
- Timestamped log files

---

## Common Tasks

### Adding a new UI step
1. Add step creation function to `gui_steps.py`
2. Add collapsible pane in `gui_main._create_widgets()`
3. Add status label update in `gui_handlers.update_step_states()`

### Adding a new worker function
1. Create worker function in `gui_workers.py`
2. Add launcher method in `gui_main.py`
3. Add queue message handling in `gui_main.process_queue()`

### Adding a new menu item
1. Add menu command in `gui_main._create_menu()`
2. Add handler method in `gui_main.py`

### Modifying image filtering
1. Edit `gui_handlers.filter_local_images()` or `gui_handlers.filter_daminion_items()`
2. Test with different scopes (collection, flagged, untagged)

### Adding new Daminion API call
1. Add method to `daminion_client.py` (use `_make_request()`)
2. Ensure proper error handling with specific exceptions
3. Respect rate limiting (automatically handled)
4. Add logging

---

## File Size Reference

```
gui_main.py         27KB  (Main window)
daminion_client.py  24KB  (API client)
gui_steps.py        16KB  (UI components)
gui_workers.py      14KB  (Background tasks)
gui_handlers.py     13KB  (Event handlers)
image_processing.py  9.5KB (Image processing)
```

**Total GUI code:** ~70KB across 4 modules (was 72KB in single file)

---

## Import Structure

```python
# Main application
main.py
  └── gui_main.py
       ├── gui_steps.py
       ├── gui_workers.py
       └── gui_handlers.py

# Core functionality
gui_workers.py
  ├── daminion_client.py
  ├── image_processing.py
  └── huggingface_utils.py

# Configuration
gui_main.py
  ├── config.py
  ├── config_manager.py
  ├── progress_tracker.py
  └── report_generator.py
```

---

## Testing Checklist

When making changes, test these areas:

**UI:**
- [ ] All steps load correctly
- [ ] Collapsible panes work
- [ ] All buttons respond
- [ ] Progress updates display
- [ ] Status messages appear

**Local Processing:**
- [ ] Directory selection
- [ ] Model search/load
- [ ] Category/keyword input
- [ ] Image processing
- [ ] Metadata writing
- [ ] Resume functionality

**Daminion:**
- [ ] Server connection
- [ ] Item fetching
- [ ] Collection listing
- [ ] Scope filtering (collection, flagged, untagged)
- [ ] Metadata updates
- [ ] Thumbnail download/cleanup

**Resource Management:**
- [ ] Temp files cleaned up
- [ ] No file handle leaks
- [ ] Memory doesn't grow unbounded
- [ ] Graceful shutdown

**Error Handling:**
- [ ] Invalid inputs handled
- [ ] Network errors caught
- [ ] Clear error messages
- [ ] No crashes

---

## Quick Tips

1. **Finding functionality:** Use your editor's search across `gui_*.py` files
2. **Adding features:** Start with `gui_handlers.py` for logic, `gui_steps.py` for UI
3. **Debugging:** Check logs, they're comprehensive and time-stamped
4. **Resource leaks:** Use context managers (`with` statement) when possible
5. **Performance:** Profile before optimizing - existing optimizations are in place

---

## Backup

The original monolithic `gui.py` is backed up as `gui_old.py` (72KB).

To revert to old version:
```bash
mv gui_old.py gui.py
# Update main.py to import from 'gui' instead of 'gui_main'
```
