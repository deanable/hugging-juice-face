"""
Test script for Daminion API client.
"""

import sys
from daminion_client import DaminionClient, DaminionAPIError
from logging_config import setup_logging
import logging

def main():
    setup_logging()

    print("="*60)
    print("Daminion API Client Test")
    print("="*60)

    # Initialize client
    client = DaminionClient(
        base_url="https://interiors.daminion.net",
        username="",
        password=""
    )

    try:
        # Test connection
        print("\n1. Testing connection...")
        status = client.test_connection()

        if status['connected']:
            print(f"   ✓ Connected to {status['server']}")
            print(f"   ✓ User: {status['username']}")
            print(f"   ✓ Total items in catalog: {status['total_items']}")
        else:
            print(f"   ✗ Connection failed: {status['error']}")
            return

        # Get media items
        print("\n2. Fetching first batch of media items (IDs 1-100)...")
        items, total = client.get_media_items(start_id=1, batch_size=100)
        print(f"   Items returned: {len(items)}")
        print(f"   Total count in catalog: {total}")

        if len(items) > 0:
            print(f"\n3. Sample items:")
            for i, item in enumerate(items[:3]):
                print(f"   {i+1}. ID={item.get('id')}: {item.get('fileName', 'N/A')}")

            print(f"\n4. Testing thumbnail download...")
            first_item = items[0]
            item_id = first_item.get('id')

            if item_id:
                thumb_path = client.download_thumbnail(item_id)
                if thumb_path:
                    print(f"   ✓ Thumbnail saved to: {thumb_path}")
                    print(f"   File exists: {thumb_path.exists()}")
                    print(f"   File size: {thumb_path.stat().st_size} bytes")
                else:
                    print(f"   ✗ Failed to download thumbnail")
        else:
            print("\n   Note: No items returned")

        # Get untagged items
        print("\n5. Fetching untagged items...")
        untagged, untagged_total = client.get_untagged_items()
        print(f"   Untagged items: {len(untagged)} (total: {untagged_total})")

        print("\n" + "="*60)
        print("Test complete!")
        print("="*60)

    except DaminionAPIError as e:
        print(f"\n✗ Daminion API Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        logging.exception("Test failed")
        sys.exit(1)
    finally:
        client.cleanup_temp_files()

if __name__ == "__main__":
    main()
