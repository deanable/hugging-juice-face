# AI-Powered Image Tagger

## Overview

A modern, AI-powered application for tagging images using Hugging Face models. It supports local file processing and Daminion DAMS integration.

## Key Features

- **Multi-Mode Processing**:
    - **Local Files**: Process images from a local directory.
    - **Daminion DAMS**: Direct integration with Daminion server to fetch, tag, and update metadata.
- **AI Models**:
    - **Image Classification**: Assigns categories (e.g., "Scenery", "Portrait").
    - **Zero-Shot Classification**: Detects custom keywords with high confidence.
    - **Image-to-Text**: Generates descriptive captions and keywords.
- **Modern GUI**: Built with CustomTkinter for a sleek, dark/light mode compatible interface.
- **Enhanced Progress Tracking**: Real-time visualization of download and processing stages.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd <repository-folder>
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Running the Application

```bash
python main.py
```

### Mode 1: Local Files

1.  Select "Local Files" mode.
2.  **Find Models**: Search and select an AI model.
3.  **Load Model**: Download and load the model into memory.
4.  **Select Source**: Choose a folder containing images.
5.  **Configure**: Set categories or keywords depending on the model task.
6.  **Process**: Start tagging. Results are saved to a report and can be exported.

### Mode 2: Daminion DAMS

1.  Select "Daminion DAMS" mode.
2.  **Connect**: Enter Server URL, Username, and Password.
3.  **Select Collection**: Choose a collection or process all items.
4.  **Load Model**: Select and load an AI model.
5.  **Process**: The system will fetch items, download thumbnails, tag them, and update Daminion metadata automatically.

## Configuration

- **User Preferences**: Saved in `~/.image_tagger_config.json`.
- **Model Cache**: stored in `~/.cache/huggingface/`.

## Development

- **Build**: Use `build_windows.bat` to create a standalone Windows executable.
- **Tests**: Run `pytest` to execute the test suite.

## Integration Details

### Daminion Integration
- Fully functional read/write integration.
- Authenticates via ASP.NET cookies.
- Batches updates to `BatchChange` endpoint.
- Handles thumbnail downloads and temp file cleanup.

### Progress Tracking
- Granular tracking for model downloads (file-level) and image processing (sub-stages like inference, metadata update).

## License

[MIT License](LICENSE)
