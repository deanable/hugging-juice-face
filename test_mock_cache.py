#!/usr/bin/env python3
"""
Test script to create mock cached models and verify the cache scanning functionality.
"""

import sys
import os
import json
from pathlib import Path

# Create mock cache structure
def create_mock_cache():
    """Create a mock cache with some sample models."""
    cache_base = Path("/home/engine/.cache/huggingface/hub")
    cache_base.mkdir(parents=True, exist_ok=True)
    
    # Create mock model directories
    mock_models = [
        {
            "model_id": "microsoft/resnet-50",
            "task": "image-classification",
            "config": {
                "model_type": "resnet",
                "pipeline_tag": "image-classification"
            }
        },
        {
            "model_id": "openai/clip-vit-base-patch32",
            "task": "zero-shot-image-classification", 
            "config": {
                "model_type": "clip",
                "pipeline_tag": "zero-shot-image-classification"
            }
        },
        {
            "model_id": "Salesforce/blip-image-captioning-base",
            "task": "image-to-text",
            "config": {
                "model_type": "blip",
                "pipeline_tag": "image-to-text"
            }
        }
    ]
    
    for mock_model in mock_models:
        # Create directory structure
        model_dir_name = f"models--{mock_model['model_id'].replace('/', '--')}"
        model_path = cache_base / model_dir_name
        snapshots_path = model_path / "snapshots"
        snapshots_path.mkdir(parents=True, exist_ok=True)
        
        # Create a snapshot directory
        snapshot_id = "abc123def456"
        snapshot_path = snapshots_path / snapshot_id
        snapshot_path.mkdir(exist_ok=True)
        
        # Create config.json
        config_path = snapshot_path / "config.json"
        with open(config_path, 'w') as f:
            json.dump(mock_model['config'], f)
            
        print(f"✅ Created mock model: {mock_model['model_id']}")
    
    print(f"🎯 Mock cache created with {len(mock_models)} models")
    return True

def test_with_mock_cache():
    """Test cache scanning with mock cached models."""
    print("🧪 Creating mock cache for testing...")
    
    if create_mock_cache():
        print("\n🔍 Testing cache scanning with mock models...")
        
        # Import and test the scanning functionality
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        
        from huggingface_utils import find_local_models_by_task
        import config
        
        tasks_to_test = [
            config.MODEL_TASK_IMAGE_CLASSIFICATION,
            config.MODEL_TASK_ZERO_SHOT,
            config.MODEL_TASK_IMAGE_TO_TEXT
        ]
        
        for task in tasks_to_test:
            print(f"\n📋 Scanning for task: {task}")
            try:
                local_models = find_local_models_by_task(task)
                print(f"✅ Found {len(local_models)} models for task '{task}'")
                
                if local_models:
                    print("📚 Models found:")
                    for model in local_models:
                        print(f"  - {model}")
                        
            except Exception as e:
                print(f"❌ Error scanning for task '{task}': {e}")

if __name__ == "__main__":
    test_with_mock_cache()