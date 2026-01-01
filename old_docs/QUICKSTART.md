# Quick Start Guide

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

```bash
python main.py
```

### Mode 1: Local Files (Original Functionality)

1. Select "Local Files" mode
2. Click "Find Models" and select an AI model
3. Click "Load Selected Model"
4. Click "Select Image Directory"
5. Configure categories/keywords based on model type
6. Click "Start Processing"

### Mode 2: Daminion DAMS ✅ FULLY WORKING

1. Select "Daminion DAMS" mode
2. Enter Daminion server details:
   - Server URL: `https://interiors.daminion.net`
   - Username: `Dean`
   - Password: `Daminion789`
3. Click "Connect to Daminion"
4. Wait for "Connected: X items in catalog" status (e.g., 1114 items)
5. Click "Find Models" and select an AI model
6. Click "Load Selected Model"
7. Configure categories/keywords based on model type
8. Click "Start Processing"

The system will automatically:
- Fetch all items from Daminion
- Download thumbnails
- Process with AI model
- Update metadata back to Daminion
- Show real-time progress

**Status**: Fully functional and production-ready!

## Testing Daminion Connection

```bash
python test_daminion.py
```

This will:
- Test authentication
- Show connection status
- Display total items in catalog
- Verify API connectivity

## Configuration Files

- `~/.image_tagger_config.json` - User preferences and last used settings
- `~/.image_tagger_progress.json` - Job resume data
- `/tmp/daminion_cache/` - Temporary thumbnail storage

## Model Tasks

### Image Classification
- Assigns one category from a predefined list
- Requires: Categories input (e.g., "Scenery, Portrait, Document")

### Zero-Shot Classification
- Detects custom keywords from your list
- Requires: Keywords input (e.g., "sunset, beach, car, dog")
- Only adds keywords with confidence > 90%

### Image-to-Text
- Generates description and extracts keywords automatically
- No categories/keywords input needed
- Filters out common stop words

## Tips

- **Resume Jobs**: If processing is interrupted, the app will ask if you want to resume
- **Model Cache**: Downloaded models are cached in `~/.cache/huggingface/`
- **Parallel Processing**: Configure workers in config file (default: 4)
- **Progress Tracking**: All progress is saved automatically

## Troubleshooting

### GUI won't start
- Ensure tkinter is installed: `sudo apt-get install python3-tk` (Linux)
- On macOS/Windows, tkinter should be included with Python

### Model download fails
- Check internet connection
- Check disk space in `~/.cache/`
- Clear cache: Menu → Cache → Clear Model Cache

### Daminion connection fails
- Verify URL is correct and accessible
- Check username/password
- Ensure network allows HTTPS to Daminion server
- See `DAMINION_INTEGRATION.md` for API limitations

## Next Steps

See `DAMINION_INTEGRATION.md` for:
- Detailed Daminion integration status
- API limitations and workarounds
- Future development roadmap
