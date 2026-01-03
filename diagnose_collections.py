
import logging
from daminion_client import DaminionClient
import json
import sys

# Setup basic logging to console
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def diagnose():
    print("="*60)
    print("Daminion Collections Diagnostic Info")
    print("="*60)

    # Use provided credentials
    url = "http://damserver/daminion"
    user = "admin"
    password = "admin"
    
    print(f"    URL: {url}")
    print(f"    User: {user}")

    # 2. Connect
    print("\n[2] Connecting...")
    client = DaminionClient(url, user, password)
    try:
        if client.authenticate():
            print("    Authentication Successful!")
        else:
            print("    Authentication Failed!")
            return
    except Exception as e:
        print(f"    Authentication Error: {e}")
        return

    # 3. Fetch Shared Collections
    print("\n[3] Fetching Shared Collections (Raw Response)...")
    
    # We want to see the RAW response from _make_request to see what the structure is
    endpoint = f"/api/SharedCollection/GetCollections?index=0&pageSize=100"
    try:
        response = client._make_request(endpoint)
        print("    RAW RESPONSE:")
        print(json.dumps(response, indent=2))
        
        print("\n    Analyzing structure:")
        if isinstance(response, list):
            print("    -> Type is LIST. (Client expects list or dict with 'collections'/'items'/'data')")
        elif isinstance(response, dict):
            print("    -> Type is DICT.")
            keys = list(response.keys())
            print(f"    -> Keys: {keys}")
        else:
            print(f"    -> Type is {type(response)}")

    except Exception as e:
        print(f"    Error fetching collections: {e}")

if __name__ == "__main__":
    diagnose()
