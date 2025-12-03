"""
Daminion DAMS API Client for retrieving and updating media items.
"""

import logging
import urllib.request
import urllib.parse
import urllib.error
import json
import atexit
import weakref
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile

class DaminionAPIError(Exception):
    """Custom exception for Daminion API errors."""
    pass

class DaminionAuthenticationError(DaminionAPIError):
    """Raised when authentication fails."""
    pass

class DaminionNetworkError(DaminionAPIError):
    """Raised when network operations fail."""
    pass

class DaminionRateLimitError(DaminionAPIError):
    """Raised when rate limit is exceeded."""
    pass

class DaminionClient:
    """Client for interacting with Daminion Server Web API.

    Supports context manager protocol for automatic cleanup:
        with DaminionClient(url, user, pass) as client:
            items = client.get_media_items()
    """

    _instances = weakref.WeakSet()

    def __init__(self, base_url: str, username: str, password: str, rate_limit: float = 0.1):
        """
        Initialize Daminion client.

        Args:
            base_url: Base URL of Daminion server (e.g., https://interiors.daminion.net)
            username: Daminion username
            password: Daminion password
            rate_limit: Minimum seconds between API calls (default: 0.1)
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.cookies = {}
        self.authenticated = False
        self.temp_dir = Path(tempfile.gettempdir()) / "daminion_cache"
        self.temp_dir.mkdir(exist_ok=True)
        self.rate_limit = rate_limit
        self._last_request_time = 0.0

        DaminionClient._instances.add(self)
        atexit.register(self.cleanup_temp_files)

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and cleanup resources."""
        self.cleanup_temp_files()
        return False

    def authenticate(self) -> bool:
        """
        Authenticate with Daminion server and store session cookies.

        Returns:
            True if authentication successful, False otherwise

        Raises:
            DaminionAPIError: If authentication fails
        """
        logging.info(f"[DAMINION] Starting authentication to {self.base_url}...")
        try:
            params = urllib.parse.urlencode({
                "userName": self.username,
                "password": self.password
            })
            login_url = f"{self.base_url}/api/UserManager/Login?{params}"
            logging.debug(f"[DAMINION] Login URL: {self.base_url}/api/UserManager/Login")

            request = urllib.request.Request(login_url, method='POST')
            logging.debug(f"[DAMINION] Sending POST request to login endpoint...")

            logging.debug(f"[DAMINION] Opening connection with 30s timeout...")
            with urllib.request.urlopen(request, timeout=30) as response:
                logging.info(f"[DAMINION] Received response with status: {response.status}")
                if response.status != 200:
                    raise DaminionAPIError(f"Login failed with status {response.status}")

                # Extract session cookies
                logging.debug(f"[DAMINION] Extracting session cookies from response headers...")
                for header, value in response.headers.items():
                    if header.lower() == 'set-cookie':
                        cookie_parts = value.split(';')[0].split('=', 1)
                        if len(cookie_parts) == 2:
                            self.cookies[cookie_parts[0]] = cookie_parts[1]
                            logging.debug(f"[DAMINION] Stored cookie: {cookie_parts[0]}")

                if not self.cookies:
                    raise DaminionAPIError("No session cookies received from server")

                self.authenticated = True
                logging.info(f"[DAMINION] [OK] Successfully authenticated to {self.base_url} as {self.username}")
                logging.info(f"[DAMINION] Session has {len(self.cookies)} cookie(s)")
                return True

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            logging.error(f"[DAMINION] [ERROR] Authentication failed: {error_msg}")
            raise DaminionAuthenticationError(f"Authentication failed: {error_msg}")
        except urllib.error.URLError as e:
            logging.error(f"[DAMINION] [ERROR] Network error during authentication: {e}")
            raise DaminionNetworkError(f"Network error: {e}")
        except Exception as e:
            logging.exception(f"[DAMINION] [ERROR] Unexpected authentication error")
            raise DaminionAuthenticationError(f"Authentication error: {e}")

    def _get_cookie_header(self) -> str:
        """Generate cookie header string from stored cookies."""
        return "; ".join([f"{k}={v}" for k, v in self.cookies.items()])

    def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        if self.rate_limit > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit:
                sleep_time = self.rate_limit - elapsed
                time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _make_request(self, endpoint: str, method: str = 'GET',
                     data: Optional[Dict] = None, timeout: int = 30) -> Dict:
        """
        Make authenticated API request with rate limiting.

        Args:
            endpoint: API endpoint (e.g., '/api/MediaItems/Get')
            method: HTTP method (GET, POST, etc.)
            data: Optional request body data
            timeout: Request timeout in seconds

        Returns:
            Response data as dictionary

        Raises:
            DaminionAuthenticationError: If not authenticated
            DaminionNetworkError: If network error occurs
            DaminionAPIError: If request fails
        """
        if not self.authenticated:
            raise DaminionAuthenticationError("Not authenticated. Call authenticate() first.")

        self._rate_limit()

        url = f"{self.base_url}{endpoint}"
        logging.debug(f"[DAMINION] API Request: {method} {endpoint}")

        try:
            request_data = None
            if data and method == 'POST':
                request_data = json.dumps(data).encode('utf-8')
                logging.debug(f"[DAMINION] Request body size: {len(request_data)} bytes")

            request = urllib.request.Request(url, data=request_data, method=method)
            request.add_header('Cookie', self._get_cookie_header())
            request.add_header('Content-Type', 'application/json')
            logging.debug(f"[DAMINION] Opening request with {timeout}s timeout...")

            with urllib.request.urlopen(request, timeout=timeout) as response:
                logging.debug(f"[DAMINION] Response status: {response.status}")
                body = response.read().decode('utf-8')
                logging.debug(f"[DAMINION] Response body size: {len(body)} bytes")
                result = json.loads(body)
                logging.debug(f"[DAMINION] [OK] API request successful")
                return result

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ''
            error_msg = f"HTTP {e.code}: {e.reason} - {error_body}"
            logging.error(f"[DAMINION] [ERROR] API request failed: {error_msg}")
            logging.error(f"[DAMINION] Failed endpoint: {method} {endpoint}")
            if e.code == 429:
                raise DaminionRateLimitError(f"Rate limit exceeded: {error_msg}")
            elif e.code in (401, 403):
                raise DaminionAuthenticationError(f"Authentication error: {error_msg}")
            raise DaminionAPIError(error_msg)
        except urllib.error.URLError as e:
            logging.error(f"[DAMINION] [ERROR] Network error: {e}")
            logging.error(f"[DAMINION] Failed endpoint: {method} {endpoint}")
            raise DaminionNetworkError(f"Network error: {e}")
        except json.JSONDecodeError as e:
            logging.error(f"[DAMINION] [ERROR] Invalid JSON response: {e}")
            raise DaminionAPIError(f"Invalid JSON response: {e}")
        except (DaminionAPIError, DaminionAuthenticationError, DaminionNetworkError, DaminionRateLimitError):
            raise
        except Exception as e:
            logging.exception(f"[DAMINION] [ERROR] Unexpected API request error: {url}")
            raise DaminionAPIError(f"Request error: {e}")

    def get_total_count(self) -> int:
        """
        Get total number of items in catalog.

        Returns:
            Total number of media items
        """
        logging.info(f"[DAMINION] Fetching total item count...")
        endpoint = "/api/MediaItems/GetCount"
        response = self._make_request(endpoint)
        total = response.get('data', 0)
        logging.info(f"[DAMINION] [OK] Total items in catalog: {total}")
        return total

    def get_media_items_by_ids(self, item_ids: List[int]) -> List[Dict]:
        """
        Retrieve specific media items by their IDs.

        Args:
            item_ids: List of item IDs to retrieve

        Returns:
            List of media items
        """
        if not item_ids:
            return []

        ids_str = ",".join(str(id) for id in item_ids)
        endpoint = f"/api/MediaItems/GetByIds?ids={ids_str}"
        response = self._make_request(endpoint)

        items = response.get('mediaItems', [])
        logging.info(f"Retrieved {len(items)} items from {len(item_ids)} IDs")
        return items

    def get_media_items(self, start_id: int = 1, batch_size: int = 100) -> Tuple[List[Dict], int]:
        """
        Retrieve media items from Daminion by ID range.

        Args:
            start_id: Starting ID (1-based)
            batch_size: Number of IDs to request

        Returns:
            Tuple of (list of media items, total count in catalog)

        Note:
            Daminion uses sequential IDs but not all IDs may exist.
            This method requests a range and returns only existing items.
        """
        total_count = self.get_total_count()
        item_ids = list(range(start_id, start_id + batch_size))
        items = self.get_media_items_by_ids(item_ids)

        logging.info(f"Retrieved {len(items)} items (catalog total: {total_count})")
        return items, total_count

    def get_all_items_paginated(self, batch_size: int = 100, max_items: Optional[int] = None) -> List[Dict]:
        """
        Retrieve all media items with pagination.

        Args:
            batch_size: Number of items to fetch per batch
            max_items: Maximum number of items to retrieve (None = all)

        Returns:
            List of all media items
        """
        logging.info(f"[DAMINION] ========== STARTING PAGINATED FETCH ==========")
        logging.info(f"[DAMINION] Batch size: {batch_size}, Max items: {max_items or 'all'}")

        total_count = self.get_total_count()
        all_items = []
        current_id = 1
        batch_num = 0

        if max_items:
            total_count = min(total_count, max_items)

        logging.info(f"[DAMINION] Target: {total_count} items from Daminion")
        logging.info(f"[DAMINION] Estimated batches: {(total_count // batch_size) + 1}")

        while len(all_items) < total_count and current_id < total_count + batch_size:
            batch_num += 1
            logging.info(f"[DAMINION] --- Batch {batch_num} ---")
            logging.info(f"[DAMINION] Requesting IDs {current_id} to {min(current_id + batch_size - 1, total_count + batch_size - 1)}")

            item_ids = list(range(current_id, min(current_id + batch_size, total_count + batch_size)))
            logging.debug(f"[DAMINION] Fetching {len(item_ids)} item IDs...")

            batch_items = self.get_media_items_by_ids(item_ids)
            logging.info(f"[DAMINION] [OK] Received {len(batch_items)} items in batch {batch_num}")

            all_items.extend(batch_items)
            current_id += batch_size

            logging.info(f"[DAMINION] Progress: {len(all_items)}/{total_count} items ({len(all_items)*100//total_count}%)")

            if max_items and len(all_items) >= max_items:
                all_items = all_items[:max_items]
                logging.info(f"[DAMINION] Reached max_items limit, stopping")
                break

            if not batch_items:
                logging.warning(f"[DAMINION] Empty batch received, stopping pagination")
                break

        logging.info(f"[DAMINION] ========== FETCH COMPLETE ==========")
        logging.info(f"[DAMINION] [OK] Retrieved total of {len(all_items)} items in {batch_num} batches")
        return all_items

    def get_shared_collections(self, index: int = 0, page_size: int = 100) -> List[Dict]:
        """Retrieve list of shared collections available on the server.

        Returns a list of collection metadata dictionaries. Uses the
        /api/SharedCollection/GetCollections endpoint.
        """
        endpoint = f"/api/SharedCollection/GetCollections?index={index}&pageSize={page_size}"
        try:
            response = self._make_request(endpoint)
            # response shape may vary; try common keys
            collections = response.get('collections') or response.get('items') or response.get('data') or response
            if isinstance(collections, dict):
                # sometimes API wraps in data/results
                return list(collections.values())
            return collections if isinstance(collections, list) else []
        except Exception as e:
            logging.exception("Failed to fetch shared collections")
            return []

    def get_shared_collection_items(self, collection_id: str | int, index: int = 0, page_size: int = 200) -> List[Dict]:
        """Retrieve items for a shared collection.

        Calls /api/SharedCollection/GetItems and expects a collection identifier value
        to be passed as a parameter. The exact server-side parameters may vary by
        Daminion version; we attempt common query names.
        """
        # try a couple of common parameter formats to support different server versions
        tried = [
            f"/api/SharedCollection/GetItems?id={collection_id}&index={index}&pageSize={page_size}",
            f"/api/SharedCollection/GetItems?collectionId={collection_id}&index={index}&pageSize={page_size}",
            f"/api/SharedCollection/PublicItems/{collection_id}/{index}/{page_size}/0/true"
        ]

        for endpoint in tried:
            try:
                response = self._make_request(endpoint)
                items = response.get('mediaItems') or response.get('items') or response.get('data') or response
                if isinstance(items, dict):
                    return list(items.values())
                if isinstance(items, list):
                    return items
            except Exception:
                continue

        logging.warning(f"Could not retrieve items for shared collection {collection_id}")
        return []

    def get_flagged_items(self, batch_size: int = 200, max_items: Optional[int] = None) -> List[Dict]:
        """Return items that appear to be flagged or rejected.

        This is implemented client-side using heuristics (filename / metadata checks)
        because not all Daminion servers provide a dedicated 'flagged' endpoint.
        """
        items = self.get_all_items_paginated(batch_size=batch_size, max_items=max_items)

        def is_flagged_item(it: Dict) -> bool:
            fname = (it.get('fileName') or '').lower()
            if any(tok in fname for tok in ['flag', 'reject', 'rejected']):
                return True
            for k in ('status', 'tags', 'keywords', 'description'):
                v = it.get(k)
                if isinstance(v, str) and any(tok in v.lower() for tok in ['flag', 'reject', 'rejected']):
                    return True
                if isinstance(v, list) and any(isinstance(x, str) and any(tok in x.lower() for tok in ['flag', 'reject', 'rejected']) for x in v):
                    return True
            return False

        return [it for it in items if is_flagged_item(it)]

    def get_untagged_items(self) -> Tuple[List[Dict], int]:
        """
        Retrieve media items that don't have all required metadata.

        Returns:
            Tuple of (list of media items, total count)

        Note:
            This endpoint returns items missing required metadata.
            May return empty if all items are properly tagged.
        """
        endpoint = "/api/MediaItems/MyItems"
        response = self._make_request(endpoint)

        items = response.get('mediaItems', [])
        total = response.get('totalCount', 0)

        logging.info(f"Retrieved {len(items)} untagged items")
        return items, total

    def download_thumbnail(self, item_id: str, width: int = 300,
                          height: int = 300) -> Optional[Path]:
        """
        Download thumbnail for a media item.

        Args:
            item_id: Media item ID
            width: Thumbnail width in pixels
            height: Thumbnail height in pixels

        Returns:
            Path to downloaded thumbnail file, or None if failed
        """
        if not self.authenticated:
            raise DaminionAPIError("Not authenticated")

        url = f"{self.base_url}/api/thumbnail/{item_id}/{width}/{height}"
        logging.debug(f"[DAMINION] Downloading thumbnail for item {item_id}...")

        try:
            request = urllib.request.Request(url)
            request.add_header('Cookie', self._get_cookie_header())

            logging.debug(f"[DAMINION] Opening thumbnail request with 30s timeout...")
            with urllib.request.urlopen(request, timeout=30) as response:
                # Save to temp file
                temp_file = self.temp_dir / f"{item_id}.jpg"
                data = response.read()
                logging.debug(f"[DAMINION] Downloaded {len(data)} bytes")

                with open(temp_file, 'wb') as f:
                    f.write(data)

                logging.debug(f"[DAMINION] [OK] Saved thumbnail to {temp_file}")
                return temp_file

        except Exception as e:
            logging.error(f"[DAMINION] [ERROR] Failed to download thumbnail for {item_id}: {e}")
            return None

    def batch_update_tags(self, item_ids: List[str], tags: Dict[str, List[str]], batch_size: int = 50) -> bool:
        """
        Update tags for multiple media items with automatic batching.

        Args:
            item_ids: List of media item IDs
            tags: Dictionary mapping tag field names to lists of values
                  Example: {"Keywords": ["sunset", "beach"], "Category": ["Scenery"]}
            batch_size: Number of items to update per batch (default: 50)

        Returns:
            True if all updates successful, False otherwise

        Note:
            Processes items in batches to avoid overwhelming the API.
        """
        if not item_ids:
            return True

        endpoint = "/api/ItemData/BatchChange"
        all_successful = True

        # Process in batches
        for i in range(0, len(item_ids), batch_size):
            batch = item_ids[i:i + batch_size]
            logging.debug(f"[DAMINION] Batch updating items {i+1} to {i+len(batch)}")

            data = {
                "mediaItemIds": batch,
                "tags": tags
            }

            try:
                response = self._make_request(endpoint, method='POST', data=data)
                success = response.get('success', False)

                if success:
                    logging.debug(f"[DAMINION] Successfully updated tags for batch of {len(batch)} items")
                else:
                    error = response.get('error', 'Unknown error')
                    logging.error(f"[DAMINION] Tag update failed for batch: {error}")
                    all_successful = False

            except (DaminionAPIError, DaminionNetworkError) as e:
                logging.error(f"[DAMINION] Batch update failed: {e}")
                all_successful = False

        if all_successful:
            logging.info(f"[DAMINION] Successfully updated tags for all {len(item_ids)} items")

        return all_successful

    def update_item_metadata(self, item_id: str, category: Optional[str] = None,
                           keywords: Optional[List[str]] = None) -> bool:
        """
        Update metadata for a single item.

        Args:
            item_id: Media item ID
            category: Category/classification for the item
            keywords: List of keywords to add

        Returns:
            True if successful, False otherwise
        """
        logging.debug(f"[DAMINION] Updating metadata for item {item_id}")
        logging.debug(f"[DAMINION] Category: {category}, Keywords: {keywords}")

        tags = {}

        if category:
            tags['Category'] = [category]

        if keywords:
            tags['Keywords'] = keywords

        if not tags:
            logging.warning(f"[DAMINION] No metadata to update for item {item_id}")
            return False

        result = self.batch_update_tags([item_id], tags)
        if result:
            logging.debug(f"[DAMINION] [OK] Metadata updated for item {item_id}")
        else:
            logging.warning(f"[DAMINION] [ERROR] Failed to update metadata for item {item_id}")
        return result

    def cleanup_temp_files(self):
        """Remove all cached thumbnail files."""
        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.glob("*.jpg"):
                    try:
                        file.unlink()
                    except OSError as e:
                        logging.warning(f"Failed to delete {file}: {e}")
                logging.debug("Cleaned up temporary thumbnail files")
        except Exception as e:
            logging.error(f"Failed to cleanup temp files: {e}")

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.cleanup_temp_files()
        except Exception:
            pass

    @classmethod
    def cleanup_all(cls):
        """Clean up all active client instances."""
        for client in list(cls._instances):
            try:
                client.cleanup_temp_files()
            except Exception:
                pass

    def test_connection(self) -> Dict[str, any]:
        """
        Test connection and return server statistics.

        Returns:
            Dictionary with connection status and server info
        """
        try:
            if not self.authenticated:
                self.authenticate()

            total = self.get_total_count()
            test_items = self.get_media_items_by_ids([1, 2, 3, 4, 5])

            return {
                'connected': True,
                'server': self.base_url,
                'username': self.username,
                'total_items': total,
                'sample_items': len(test_items),
                'api_responding': True
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
