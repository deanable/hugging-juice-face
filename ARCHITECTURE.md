```
# Architecture Documentation

## System Overview

The Advanced Image Tagger is a desktop application that uses AI models to automatically tag images with categories and keywords. It supports both local file processing and integration with Daminion DAMS (Digital Asset Management System).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE (Tkinter)                        │
│                                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  Step 1  │  │  Step 2  │  │  Step 3  │  │  Step 4  │             │
│  │ Source   │  │  Model   │  │  Config  │  │ Process  │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
└───────┼─────────────┼─────────────┼─────────────┼───────────────────┘
        │             │             │             │
        │             │             │             │
┌───────▼─────────────▼─────────────▼─────────────▼───────────────────────┐
│                        APPLICATION CORE                                  │
│                                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │   Config    │  │   Progress   │  │   Report    │  │   Logging    │ │
│  │  Manager    │  │   Tracker    │  │  Generator  │  │   Config     │ │
│  │             │  │              │  │             │  │              │ │
│  │ • Validated │  │ • Job State  │  │ • CSV/JSON  │  │ • File+Con   │ │
│  │ • Pydantic  │  │ • Resume     │  │ • Stats     │  │ • Rotating   │ │
│  └─────────────┘  └──────────────┘  └─────────────┘  └──────────────┘ │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    WORKER THREAD POOL                            │  │
│  │                                                                  │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐ │  │
│  │  │  Model     │  │  Image     │  │  Daminion  │  │  Other   │ │  │
│  │  │  Workers   │  │  Workers   │  │  Workers   │  │  Workers │ │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └──────────┘ │  │
│  │                                                                  │  │
│  │  • ThreadPoolExecutor (max 4-16 workers)                        │  │
│  │  • Queue-based communication                                    │  │
│  │  • Progress reporting                                           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                │             │                    │
                │             │                    │
┌───────────────▼─────────────▼────────────────────▼──────────────────────┐
│                       INTEGRATION LAYER                                  │
│                                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────────┐  │
│  │  Hugging Face  │  │  Image Meta    │  │     Daminion DAMS        │  │
│  │   API Client   │  │  data Writer   │  │       API Client         │  │
│  │                │  │                │  │                          │  │
│  │ • Model Search │  │ • IPTC/EXIF    │  │ • REST API               │  │
│  │ • Download     │  │ • Validation   │  │ • Session Mgmt           │  │
│  │ • Pipeline     │  │ • Retry Logic  │  │ • Rate Limiting          │  │
│  │                │  │                │  │ • Connection Pool        │  │
│  │                │  │                │  │ • Async Support          │  │
│  └────────────────┘  └────────────────┘  └──────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                │                                          │
                │                                          │
┌───────────────▼──────────────────────────────────────────▼───────────────┐
│                        EXTERNAL SERVICES                                 │
│                                                                          │
│  ┌─────────────────────┐              ┌─────────────────────────────┐  │
│  │   Hugging Face Hub  │              │   Daminion Server           │  │
│  │                     │              │                             │  │
│  │ • Model Repository  │              │ • Media Items API           │  │
│  │ • Model Downloads   │              │ • Metadata API              │  │
│  │ • Model Info        │              │ • Collections API           │  │
│  └─────────────────────┘              └─────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

## Module Structure

### GUI Layer (`gui_*.py`)

```
gui_main.py (Main Window)
    ├── State Management
    ├── Queue Processing
    ├── Menu Handlers
    └── Worker Launchers

gui_steps.py (UI Components)
    ├── CollapsiblePane Widget
    ├── Step 1: Source Selection
    ├── Step 2: Model Selection
    ├── Step 3: Configuration
    ├── Step 4: Processing
    └── Progress Display

gui_handlers.py (Event Handlers)
    ├── Mode Change Handlers
    ├── Selection Handlers
    ├── Filtering Logic
    ├── State Updates
    └── Utility Functions

gui_workers.py (Background Tasks)
    ├── Model Operations
    ├── Daminion Operations
    ├── Image Processing
    └── Collection Management
```

### Core Logic Layer

```
image_processing.py
    ├── Image Validation
    ├── IPTC Metadata Writer
    ├── EXIF Metadata Writer
    ├── AI Model Integration
    └── Retry Logic

daminion_client.py (Sync)
    ├── Authentication
    ├── Session Management
    ├── API Wrappers
    ├── Rate Limiting
    ├── Resource Cleanup
    └── Error Handling

daminion_async.py (Async)
    ├── Async/Await API
    ├── aiohttp Integration
    ├── Concurrent Requests
    ├── Async File I/O
    └── Connection Management

daminion_pool.py
    ├── Connection Pooling
    ├── Connection Reuse
    ├── Health Checking
    ├── Automatic Recycling
    └── Pool Maintenance

huggingface_utils.py
    ├── Model Search
    ├── Model Download
    ├── Progress Reporting
    ├── Cache Management
    └── Pipeline Creation
```

### Configuration Layer

```
config.py
    └── Application Constants

config_schema.py (Pydantic)
    ├── ProcessingConfig
    ├── ModelConfig
    ├── DaminionConfig
    ├── TaggingConfig
    ├── DirectoryConfig
    └── AppConfig (Composite)

config_manager.py
    ├── Config Persistence
    ├── Validation Integration
    ├── Legacy Compatibility
    └── Default Values
```

### Reporting Layer

```
progress_tracker.py
    ├── Job State Tracking
    ├── Resume Capability
    ├── JSON Persistence
    └── Progress Reporting

report_generator.py
    ├── CSV Export
    ├── JSON Export
    ├── Statistics
    └── Summary Generation
```

## Data Flow

### Local Image Processing Flow

```
1. User selects directory
       │
       ▼
2. Scan for images (*.jpg, *.jpeg, *.png)
       │
       ▼
3. Apply scope filter (collection/flagged/untagged)
       │
       ▼
4. Create worker threads (ThreadPoolExecutor)
       │
       ▼
5. For each image (parallel):
   ├─ Validate image file
   ├─ Load image (PIL)
   ├─ Run AI model inference
   ├─ Extract category/keywords
   ├─ Write IPTC metadata
   ├─ Write EXIF metadata
   └─ Update progress
       │
       ▼
6. Generate report (CSV/JSON)
```

### Daminion Processing Flow

```
1. User connects to Daminion server
       │
       ▼
2. Authenticate (get session cookies)
       │
       ▼
3. Fetch items based on scope:
   ├─ Collection → get_shared_collection_items()
   ├─ Flagged → get_flagged_items()
   └─ Untagged → get_untagged_items()
       │
       ▼
4. For each item:
   ├─ Download thumbnail
   ├─ Load image (PIL)
   ├─ Run AI model inference
   ├─ Extract category/keywords
   └─ Update item metadata via API
       │
       ▼
5. Cleanup temp files
       │
       ▼
6. Generate report
```

### Configuration Flow

```
1. Load JSON config from ~/.image_tagger_config.json
       │
       ▼
2. Parse as dict
       │
       ▼
3. Validate with Pydantic schemas
   ├─ Valid → Use validated config
   └─ Invalid → Use defaults + log warnings
       │
       ▼
4. Provide to application
       │
       ▼
5. On changes:
   ├─ Validate new values
   ├─ Update config object
   └─ Save to JSON
```

## Threading Model

### Main Thread
- Runs Tkinter event loop
- Processes queue messages
- Updates UI
- Handles user input

### Worker Threads
- Model download/loading
- Image processing (parallel)
- API requests
- File I/O operations

### Queue Communication
```
Worker → Queue → Main Thread

Message Types:
- model_loaded: Model ready
- progress: Processing update
- status_update: Status message
- error: Error occurred
- daminion_connected: Connection established
- progress_done: Processing complete
```

## Connection Management

### Synchronous Client
```python
# Simple usage
client = DaminionClient(url, user, pass)
try:
    items = client.get_media_items()
finally:
    client.cleanup_temp_files()

# Context manager (recommended)
with DaminionClient(url, user, pass) as client:
    items = client.get_media_items()
```

### Connection Pool
```python
# Pool manages multiple connections
pool = DaminionConnectionPool(
    url, user, pass,
    min_size=2,
    max_size=10
)

# Get connection from pool
with pool.get_connection() as client:
    items = client.get_media_items()

pool.close_all()
```

### Async Client
```python
# Async/await for concurrent operations
async with AsyncDaminionClient(url, user, pass) as client:
    # Fetch multiple batches concurrently
    items = await client.get_all_items_paginated(batch_size=100)

    # Process concurrently
    tasks = [client.update_item_metadata(id, cat, kw) for id in item_ids]
    results = await asyncio.gather(*tasks)
```

## Error Handling Strategy

### Exception Hierarchy
```
Exception
  └─ DaminionAPIError (base)
       ├─ DaminionAuthenticationError (401, 403)
       ├─ DaminionNetworkError (network issues)
       └─ DaminionRateLimitError (429)

Exception
  └─ ImageValidationError
       ├─ File not found
       ├─ Invalid format
       └─ Size exceeded
```

### Error Recovery
1. **Network errors**: Retry with exponential backoff
2. **Rate limit**: Wait and retry
3. **Authentication**: Re-authenticate
4. **Validation**: Skip and continue
5. **Fatal**: Log and terminate gracefully

## Performance Optimizations

### File Scanning
- **Before**: Multiple `rglob()` calls per extension
- **After**: Single directory walk with set lookup
- **Improvement**: ~3x faster

### Keyword Deduplication
- **Before**: `O(n²)` list lookups
- **After**: `O(n)` set lookups
- **Improvement**: Dramatic with large keyword lists

### API Batching
- Automatic batching of large requests
- Prevents timeouts
- Better error handling per batch

### Connection Pooling
- Reuse authenticated connections
- Reduce authentication overhead
- Better resource utilization

### Async Operations
- Concurrent API requests
- Non-blocking I/O
- Better throughput

## Configuration Schema

```python
AppConfig
  ├─ processing: ProcessingConfig
  │    ├─ max_concurrent_workers: int (1-16)
  │    ├─ zero_shot_threshold: float (0.0-1.0)
  │    ├─ max_image_size_mb: int (1-500)
  │    └─ max_keywords_per_image: int (1-100)
  │
  ├─ model: ModelConfig
  │    ├─ last_model_task: str
  │    ├─ last_model_id: Optional[str]
  │    └─ model_search_limit: int (10-500)
  │
  ├─ daminion: DaminionConfig
  │    ├─ url: str
  │    ├─ username: str
  │    ├─ rate_limit: float (0.0-5.0)
  │    ├─ batch_size: int (1-200)
  │    └─ timeout: int (5-300)
  │
  ├─ tagging: TaggingConfig
  │    ├─ default_categories: str
  │    └─ default_keywords: str
  │
  └─ directory: DirectoryConfig
       └─ last_directory: Optional[Path]
```

## Security Considerations

### Authentication
- Session cookies stored in memory only
- Automatic cleanup on exit
- Re-authentication on 401/403

### API Keys
- Hugging Face tokens (optional)
- Never logged or persisted
- Environment variable support

### File Operations
- Temp files in secure location
- Automatic cleanup with `atexit`
- Path validation to prevent traversal

### Network
- HTTPS preferred
- Timeout enforcement
- Rate limiting

## Scalability

### Current Limitations
- Single machine
- Limited by local resources
- UI blocking during long operations

### Scaling Strategies
1. **Horizontal**: Process images on multiple machines
2. **Async UI**: Separate UI and processing
3. **Distributed**: Use task queue (Celery, RQ)
4. **Cloud**: Deploy workers to cloud
5. **Database**: Use Supabase for state/progress

## Dependencies

### Core
- `transformers` - AI model loading
- `torch` - Neural network backend
- `Pillow` - Image processing
- `huggingface_hub` - Model downloads

### Metadata
- `piexif` - EXIF metadata
- `iptcinfo3` - IPTC metadata

### Validation
- `pydantic` - Configuration schemas

### Async
- `aiohttp` - Async HTTP client
- `aiofiles` - Async file I/O

### GUI
- `tkinter` - UI framework (built-in)

## Deployment

### Local Installation
```bash
# Clone repository
git clone <repo>
cd image-tagger

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

### Configuration
- Config file: `~/.image_tagger_config.json`
- Progress file: `~/.image_tagger_progress.json`
- Model cache: `~/.cache/huggingface/hub`
- Logs: `image_tagger_YYYYMMDD_HHMMSS.log`

## Testing Strategy

### Unit Tests
- Individual function testing
- Mock external dependencies
- Test error conditions

### Integration Tests
- End-to-end workflows
- Real API interactions (test server)
- Database operations

### Performance Tests
- Large directory scanning
- Concurrent processing
- Memory usage profiling

## Monitoring & Observability

### Logging
- File: Rotating logs (10MB, 5 backups)
- Console: Real-time output
- Levels: DEBUG, INFO, WARNING, ERROR

### Metrics
- Images processed
- Success/failure rates
- Processing time per image
- Model inference time
- API call latency

### Reports
- CSV: Detailed per-image results
- JSON: Structured data with summary
- Summary: Quick statistics

## Future Enhancements

### Near-term
- Web UI (React/Vue)
- REST API for remote access
- Docker containerization
- Kubernetes deployment

### Long-term
- Multi-user support
- Role-based access control
- Cloud storage integration (S3, GCS)
- Custom model training
- Video support
- Real-time processing
- Mobile app

## Maintenance

### Regular Tasks
- Update dependencies
- Clear old logs
- Clear model cache (if needed)
- Backup configuration

### Troubleshooting
1. Check logs for errors
2. Verify configuration validity
3. Test network connectivity
4. Validate file permissions
5. Check disk space

## Resources

### Documentation
- `README.md` - Getting started
- `ARCHITECTURE.md` - This file
- `MODULE_GUIDE.md` - Developer guide
- `REFACTORING_SUMMARY.md` - Recent changes

### Code Organization
- 4 GUI modules (~1700 lines)
- 3 API client variations (~900 lines)
- 8 supporting modules (~1000 lines)
- Total: ~3600 lines (well-organized)

---

Last Updated: 2025-01-03
Version: 2.0 (Post-Refactoring)
