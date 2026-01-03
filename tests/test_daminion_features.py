
import logging
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from daminion_client import DaminionClient
from settings_manager import SettingsManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_daminion_features():
    print("\n========== DAMINION FEATURE TEST ==========\n")
    
    # Load settings
    settings = SettingsManager(filename=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_settings.json"))
    url = settings.get('daminion_url', 'http://damserver/daminion') # Default local
    username = settings.get('daminion_username', 'admin')
    
    # Try to get password from registry
    password = settings.load_daminion_password_from_registry()
    
    if not password:
        print("⚠️ Password not found in registry. Please enter it:")
        password = input("Password: ").strip()

    print(f"Connecting to {url} as {username}...")
    
    try:
        client = DaminionClient(url, username, password)
        status = client.test_connection()
        
        if not status['connected']:
            print(f"❌ Connection failed: {status.get('error')}")
            return
            
        print("✅ Connection successful!")
        
        # 1. Test Shared Collections
        print("\n--- Testing Shared Collections ---")
        try:
            cols = client.get_shared_collections(index=0, page_size=5)
            print(f"Found {len(cols)} collections (top 5):")
            for c in cols:
                print(f" - ID: {c.get('id')}, Name: {c.get('name')}, Count: {c.get('count')}")
        except Exception as e:
            print(f"Failed to fetch collections: {e}")

        # 2. Test Fetching Items
        print("\n--- Testing Item Fetch ---")
        items = client.get_all_items_paginated(batch_size=10, max_items=10)
        print(f"Fetched {len(items)} sample items.")
        
        flagged_count = 0
        untagged_count = 0
        
        for item in items:
            print(f"Item {item.get('id')}: {item.get('fileName')}")
            
            # Check Flagged
            is_flagged = False
            for k, v in item.items():
                if isinstance(v, str) and 'flag' in v.lower():
                     is_flagged = True
                     break
            if is_flagged:
                flagged_count += 1
                
            # Check Untagged
            tags = item.get('tags', [])
            keywords = item.get('keywords', [])
            description = item.get('description', '')
            if not tags and not keywords and not description:
                 untagged_count += 1

        print(f"\nSummary in sample batch:")
        print(f"Flagged items: {flagged_count}")
        print(f"Untagged/Clean items: {untagged_count}")

    except Exception as e:
        print(f"❌ Test Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_daminion_features()
