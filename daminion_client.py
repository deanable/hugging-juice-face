"""
Daminion DAMS API Client for retrieving and updating media items.
"""

import logging
import urllib.request
import urllib.parse
import urllib.error
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile

class DaminionAPIError(Exception):
    """Custom exception for Daminion API errors."""
    pass

class DaminionClient:
    """Client for interacting with Daminion Server Web API."""

    def __init__(self, base_url: str, username: str, password: str):
        """
        Initialize Daminion client.

        Args:
            base_url: Base URL of Daminion server (e.g., https://interiors.daminion.net)
            username: Daminion username
            password: Daminion password
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.cookies = {}
        self.authenticated = False
        self.temp_dir = Path(tempfile.gettempdir()) / "daminion_cache"
        self.temp_dir.mkdir(exist_ok=True)

    def authenticate(self) -> bool:
        """
        Authenticate with Daminion server and store session cookies.

        Returns:
            True if authentication successful, False otherwise

        Raises:
            DaminionAPIError: If authentication fails
        """
        try:
            params = urllib.parse.urlencode({
                "userName": self.username,
                "password": self.password
            })
            login_url = f"{self.base_url}/api/UserManager/Login?{params}"

            request = urllib.request.Request(login_url, method='POST')

            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise DaminionAPIError(f"Login failed with status {response.status}")

                # Extract session cookies
                for header, value in response.headers.items():
                    if header.lower() == 'set-cookie':
                        cookie_parts = value.split(';')[0].split('=', 1)
                        if len(cookie_parts) == 2:
                            self.cookies[cookie_parts[0]] = cookie_parts[1]

                if not self.cookies:
                    raise DaminionAPIError("No session cookies received from server")

                self.authenticated = True
                logging.info(f"Successfully authenticated to {self.base_url} as {self.username}")
                return True

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            logging.error(f"Authentication failed: {error_msg}")
            raise DaminionAPIError(f"Authentication failed: {error_msg}")
        except Exception as e:
            logging.exception("Authentication error")
            raise DaminionAPIError(f"Authentication error: {e}")

    def _get_cookie_header(self) -> str:
        """Generate cookie header string from stored cookies."""
        return "; ".join([f"{k}={v}" for k, v in self.cookies.items()])

    def _make_request(self, endpoint: str, method: str = 'GET',
                     data: Optional[Dict] = None, timeout: int = 30) -> Dict:
        """
        Make authenticated API request.

        Args:
            endpoint: API endpoint (e.g., '/api/MediaItems/Get')
            method: HTTP method (GET, POST, etc.)
            data: Optional request body data
            timeout: Request timeout in seconds

        Returns:
            Response data as dictionary

        Raises:
            DaminionAPIError: If request fails
        """
        if not self.authenticated:
            raise DaminionAPIError("Not authenticated. Call authenticate() first.")

        url = f"{self.base_url}{endpoint}"

        try:
            request_data = None
            if data and method == 'POST':
                request_data = json.dumps(data).encode('utf-8')

            request = urllib.request.Request(url, data=request_data, method=method)
            request.add_header('Cookie', self._get_cookie_header())
            request.add_header('Content-Type', 'application/json')

            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode('utf-8')
                return json.loads(body)

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ''
            error_msg = f"HTTP {e.code}: {e.reason} - {error_body}"
            logging.error(f"API request failed: {error_msg}")
            raise DaminionAPIError(error_msg)
        except Exception as e:
            logging.exception(f"API request error: {url}")
            raise DaminionAPIError(f"Request error: {e}")

    def get_media_items(self, page_index: int = 0, page_size: int = 50) -> Tuple[List[Dict], int]:
        """
        Retrieve media items from Daminion.

        Args:
            page_index: Page number (0-based)
            page_size: Number of items per page

        Returns:
            Tuple of (list of media items, total count)

        Note:
            Current implementation returns totalCount but empty items array.
            This may require additional API parameters or different endpoint.
        """
        endpoint = f"/api/MediaItems/Get?pageIndex={page_index}&pageSize={page_size}"
        response = self._make_request(endpoint)

        items = response.get('mediaItems', [])
        total = response.get('totalCount', 0)

        logging.info(f"Retrieved {len(items)} items (total: {total})")
        return items, total

    def get_untagged_items(self) -> Tuple[List[Dict], int]:
        """
        Retrieve media items that don't have all required metadata.

        Returns:
            Tuple of (list of media items, total count)
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

        try:
            request = urllib.request.Request(url)
            request.add_header('Cookie', self._get_cookie_header())

            with urllib.request.urlopen(request, timeout=30) as response:
                # Save to temp file
                temp_file = self.temp_dir / f"{item_id}.jpg"
                with open(temp_file, 'wb') as f:
                    f.write(response.read())

                logging.info(f"Downloaded thumbnail for item {item_id}")
                return temp_file

        except Exception as e:
            logging.error(f"Failed to download thumbnail for {item_id}: {e}")
            return None

    def batch_update_tags(self, item_ids: List[str], tags: Dict[str, List[str]]) -> bool:
        """
        Update tags for multiple media items.

        Args:
            item_ids: List of media item IDs
            tags: Dictionary mapping tag field names to lists of values
                  Example: {"Keywords": ["sunset", "beach"], "Category": ["Scenery"]}

        Returns:
            True if update successful, False otherwise

        Note:
            Exact request format may need adjustment based on API requirements.
        """
        endpoint = "/api/ItemData/BatchChange"

        # Construct request body - format may need adjustment
        data = {
            "mediaItemIds": item_ids,
            "tags": tags
        }

        try:
            response = self._make_request(endpoint, method='POST', data=data)
            success = response.get('success', False)

            if success:
                logging.info(f"Successfully updated tags for {len(item_ids)} items")
            else:
                error = response.get('error', 'Unknown error')
                logging.error(f"Tag update failed: {error}")

            return success

        except Exception as e:
            logging.error(f"Batch update failed: {e}")
            return False

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
        tags = {}

        if category:
            tags['Category'] = [category]

        if keywords:
            tags['Keywords'] = keywords

        if not tags:
            logging.warning(f"No metadata to update for item {item_id}")
            return False

        return self.batch_update_tags([item_id], tags)

    def cleanup_temp_files(self):
        """Remove all cached thumbnail files."""
        try:
            for file in self.temp_dir.glob("*.jpg"):
                file.unlink()
            logging.info("Cleaned up temporary thumbnail files")
        except Exception as e:
            logging.error(f"Failed to cleanup temp files: {e}")

    def test_connection(self) -> Dict[str, any]:
        """
        Test connection and return server statistics.

        Returns:
            Dictionary with connection status and server info
        """
        try:
            if not self.authenticated:
                self.authenticate()

            items, total = self.get_media_items(page_index=0, page_size=1)

            return {
                'connected': True,
                'server': self.base_url,
                'username': self.username,
                'total_items': total,
                'api_responding': True
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
