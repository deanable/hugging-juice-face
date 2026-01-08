#!/usr/bin/env python3
"""
Test script to verify cache scanning functionality works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from huggingface_utils import find_local_models_by_task, get_cache_dir
from pathlib import Path
import config

def test_cache_scanning():
    """Test the cache scanning functionality."""
    print("🧪 Testing cache scanning functionality...")
    
    # Test 1: Check cache directory exists
    cache_dir = get_cache_dir()
    print(f"📁 Cache directory: {cache_dir}")
    
    if Path(cache_dir).exists():
        print(f"✅ Cache directory exists")
        
        # List what's in the cache
        cache_path = Path(cache_dir)
        model_dirs = list(cache_path.glob("models--*"))
        print(f"📊 Found {len(model_dirs)} model directories in cache")
        
        if model_dirs:
            print("📋 Model directories found:")
            for model_dir in model_dirs[:5]:  # Show first 5
                print(f"  - {model_dir.name}")
            if len(model_dirs) > 5:
                print(f"  ... and {len(model_dirs) - 5} more")
    else:
        print(f"⚠️ Cache directory does not exist")
    
    # Test 2: Test scanning for different tasks
    tasks_to_test = [
        config.MODEL_TASK_IMAGE_CLASSIFICATION,
        config.MODEL_TASK_ZERO_SHOT,
        config.MODEL_TASK_IMAGE_TO_TEXT
    ]
    
    print(f"\n🔍 Testing model scanning for different tasks...")
    
    for task in tasks_to_test:
        print(f"\n📋 Scanning for task: {task}")
        try:
            local_models = find_local_models_by_task(task)
            print(f"✅ Found {len(local_models)} models for task '{task}'")
            
            if local_models:
                print("📚 Models found:")
                for model in local_models[:3]:  # Show first 3
                    print(f"  - {model}")
                if len(local_models) > 3:
                    print(f"  ... and {len(local_models) - 3} more")
            else:
                print("ℹ️ No models found for this task")
                
        except Exception as e:
            print(f"❌ Error scanning for task '{task}': {e}")
    
    print(f"\n🎯 Cache scanning test completed!")

if __name__ == "__main__":
    test_cache_scanning()