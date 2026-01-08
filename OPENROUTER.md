# OpenRouter Integration Guide

This application supports cloud-based image analysis via the **OpenRouter API**, allowing you to use state-of-the-art multimodal models without needing a powerful local GPU.

## Key Features

- **No Local GPU Required**: Runs purely on the cloud.
- **Access to Top Models**: Use GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro, and LLaVA via OpenRouter.
- **Pay-as-you-go**: Only pay for what you use with your OpenRouter API key.
- **Seamless Integration**: Works exactly like local models in the GUI.

## Setup

1. **Get an API Key**:
   - Sign up at [OpenRouter.ai](https://openrouter.ai/).
   - Create a new API key.
   - Ensure you have credits (some models are free, others are paid).

2. **Configure in App**:
   - Launch the application (`python main.py`).
   - In **Step 2 (Select AI Model)**, switch **Processing Mode** to **Cloud (API)**.
   - Select **Provider** as **OpenRouter**.
   - Enter your **API Key**.
   - Click **Test API Connection** to verify.

## Supported Tasks

The integration automatically adapts to the selected analysis type:

### 1. Auto-Tagging (Keywords)
- **Task**: `image-classification`
- **Behavior**: Generates a list of relevant tags/labels for the image.
- **Output**: Populates the **Keywords** field in metadata.

### 2. Categorization (Custom)
- **Task**: `zero-shot-image-classification`
- **Behavior**: Classifies the image into one of your custom categories.
- **Output**: Populates the **Category** field in metadata.
- **Note**: Requires you to enter **Categories** in Step 3.

### 3. Captioning (Description)
- **Task**: `image-to-text`
- **Behavior**: Generates a detailed description of the image content.
- **Output**: Populates the **Description/Caption** field in metadata.

## Recommended Models

The application will auto-select a good default model, but you can choose specific ones if available on OpenRouter:

- `openai/gpt-4o`: Best overall quality, higher cost.
- `anthropic/claude-3.5-sonnet`: Excellent for detailed descriptions.
- `google/gemini-1.5-pro`: Strong multimodal performance.
- `llava-hf/llava-v1.6-mistral-7b-hf`: Good open-source option.

## Troubleshooting

- **401 Unauthorized**: Check your API key.
- **402 Payment Required**: Check your OpenRouter credit balance.
- **404 Model Not Found**: The selected model ID might be incorrect or deprecated.
- **Timeout**: Large images or slow models may take time. The app has a 60s timeout.

## Privacy Note

Images are uploaded to OpenRouter for processing. Ensure you comply with OpenRouter's privacy policy and do not upload sensitive PII if not permitted.
