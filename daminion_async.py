"""
Async/await version of Daminion API client.
Provides non-blocking I/O operations for better performance.
"""

import logging
import json
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile

from daminion_client import (
    DaminionAPIError,
    DaminionAuthenticationError,
    DaminionNetworkError,
    DaminionRateLimitError
)


class AsyncDaminionClient:
    """Async version of Daminion API client.

    Uses aiohttp for async HTTP requests and aiofiles for async file operations.

    Usage:
        async with AsyncDaminionClient(url, user, pass) as client:
            items = await client.get_media_items()
    """

    def __init__(self, base_url: str, username: str, password: str, rate_limit: float = 0.1):
        """Initialize async Daminion client.

        Args:
            base_url: Daminion server URL
            username: Username
            password: Password
            rate_limit: Minimum seconds between API calls
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
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests

    async def __aenter__(self):
        """Enter async context manager."""
        self._session = aiohttp.ClientSession()
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        await self.cleanup_temp_files()
        if self._session:
            await self._session.close()
        return False

    async def _rate_limit_wait(self):
        """Enforce rate limiting between API calls."""
        if self.rate_limit > 0:
            elapsed = asyncio.get_event_loop().time() - self._last_request_time
            if elapsed < self.rate_limit:
                sleep_time = self.rate_limit - elapsed
                await asyncio.sleep(sleep_time)
        self._last_request_time = asyncio.get_event_loop().time()

    async def authenticate(self) -> bool:
        """Authenticate with Daminion server.

        Returns:
            True if authentication successful

        Raises:
            DaminionAuthenticationError: If authentication fails
        """
        logging.info(f"[ASYNC DAMINION] Starting authentication to {self.base_url}...")

        if not self._session:
            self._session = aiohttp.ClientSession()

        try:
            url = f"{self.base_url}/api/UserManager/Login"
            params = {
                "userName": self.username,
                "password": self.password
            }

            async with self._session.post(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    raise DaminionAuthenticationError(f"Login failed with status {response.status}")

                # Extract session cookies
                for cookie in response.cookies.values():
                    self.cookies[cookie.key] = cookie.value

                if not self.cookies:
                    raise DaminionAuthenticationError("No session cookies received from server")

                self.authenticated = True
                logging.info(f"[ASYNC DAMINION] Successfully authenticated")
                return True

        except aiohttp.ClientError as e:
            logging.error(f"[ASYNC DAMINION] Network error during authentication: {e}")
            raise DaminionNetworkError(f"Network error: {e}")
        except asyncio.TimeoutError:
            logging.error(f"[ASYNC DAMINION] Authentication timeout")
            raise DaminionNetworkError("Authentication timeout")
        except Exception as e:
            logging.exception(f"[ASYNC DAMINION] Unexpected authentication error")
            raise DaminionAuthenticationError(f"Authentication error: {e}")

    async def _make_request(self, endpoint: str, method: str = 'GET',
                           data: Optional[Dict] = None, timeout: int = 30) -> Dict:
        """Make authenticated API request.

        Args:
            endpoint: API endpoint
            method: HTTP method
            data: Optional request body data
            timeout: Request timeout in seconds

        Returns:
            Response data as dictionary

        Raises:
            DaminionAPIError: If request fails
        """
        if not self.authenticated:
            raise DaminionAuthenticationError("Not authenticated. Call authenticate() first.")

        if not self._session:
            raise DaminionAPIError("Session not initialized")

        await self._rate_limit_wait()

        url = f"{self.base_url}{endpoint}"
        logging.debug(f"[ASYNC DAMINION] API Request: {method} {endpoint}")

        async with self._semaphore:
            try:
                request_kwargs = {
                    'url': url,
                    'cookies': self.cookies,
                    'timeout': aiohttp.ClientTimeout(total=timeout)
                }

                if data and method == 'POST':
                    request_kwargs['json'] = data

                async with self._session.request(method, **request_kwargs) as response:
                    body = await response.text()

                    if response.status == 429:
                        raise DaminionRateLimitError(f"Rate limit exceeded: {response.status}")
                    elif response.status in (401, 403):
                        raise DaminionAuthenticationError(f"Authentication error: {response.status}")
                    elif response.status >= 400:
                        raise DaminionAPIError(f"HTTP {response.status}: {body}")

                    result = json.loads(body)
                    logging.debug(f"[ASYNC DAMINION] API request successful")
                    return result

            except aiohttp.ClientError as e:
                logging.error(f"[ASYNC DAMINION] Network error: {e}")
                raise DaminionNetworkError(f"Network error: {e}")
            except asyncio.TimeoutError:
                logging.error(f"[ASYNC DAMINION] Request timeout")
                raise DaminionNetworkError("Request timeout")
            except json.JSONDecodeError as e:
                logging.error(f"[ASYNC DAMINION] Invalid JSON response: {e}")
                raise DaminionAPIError(f"Invalid JSON response: {e}")
            except (DaminionAPIError, DaminionAuthenticationError, DaminionNetworkError, DaminionRateLimitError):
                raise
            except Exception as e:
                logging.exception(f"[ASYNC DAMINION] Unexpected API request error")
                raise DaminionAPIError(f"Request error: {e}")

    async def get_total_count(self) -> int:
        """Get total number of items in catalog.

        Returns:
            Total number of media items
        """
        endpoint = "/api/MediaItems/GetCount"
        response = await self._make_request(endpoint)
        total = response.get('data', 0)
        return total

    async def get_media_items_by_ids(self, item_ids: List[int]) -> List[Dict]:
        """Retrieve specific media items by their IDs.

        Args:
            item_ids: List of item IDs to retrieve

        Returns:
            List of media items
        """
        if not item_ids:
            return []

        ids_str = ",".join(str(id) for id in item_ids)
        endpoint = f"/api/MediaItems/GetByIds?ids={ids_str}"
        response = await self._make_request(endpoint)

        items = response.get('mediaItems', [])
        return items

    async def get_all_items_paginated(self, batch_size: int = 100,
                                     max_items: Optional[int] = None) -> List[Dict]:
        """Retrieve all media items with pagination.

        Args:
            batch_size: Number of items to fetch per batch
            max_items: Maximum number of items to retrieve (None = all)

        Returns:
            List of all media items
        """
        total_count = await self.get_total_count()
        all_items = []
        current_id = 1

        if max_items:
            total_count = min(total_count, max_items)

        # Create tasks for parallel batch fetching
        tasks = []
        while current_id < total_count + batch_size:
            item_ids = list(range(current_id, min(current_id + batch_size, total_count + batch_size)))
            tasks.append(self.get_media_items_by_ids(item_ids))
            current_id += batch_size

            # Process in chunks to avoid overwhelming the server
            if len(tasks) >= 5:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in batch_results:
                    if isinstance(result, Exception):
                        logging.error(f"Batch fetch failed: {result}")
                    elif isinstance(result, list):
                        all_items.extend(result)
                tasks = []

        # Process remaining tasks
        if tasks:
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in batch_results:
                if isinstance(result, Exception):
                    logging.error(f"Batch fetch failed: {result}")
                elif isinstance(result, list):
                    all_items.extend(result)

        if max_items:
            all_items = all_items[:max_items]

        return all_items

    async def download_thumbnail(self, item_id: str, width: int = 300,
                                 height: int = 300) -> Optional[Path]:
        """Download thumbnail for a media item.

        Args:
            item_id: Media item ID
            width: Thumbnail width in pixels
            height: Thumbnail height in pixels

        Returns:
            Path to downloaded thumbnail file, or None if failed
        """
        if not self.authenticated or not self._session:
            raise DaminionAPIError("Not authenticated")

        url = f"{self.base_url}/api/thumbnail/{item_id}/{width}/{height}"

        try:
            async with self._session.get(url, cookies=self.cookies, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    return None

                temp_file = self.temp_dir / f"{item_id}.jpg"
                data = await response.read()

                async with aiofiles.open(temp_file, 'wb') as f:
                    await f.write(data)

                return temp_file

        except Exception as e:
            logging.error(f"[ASYNC DAMINION] Failed to download thumbnail for {item_id}: {e}")
            return None

    async def batch_update_tags(self, item_ids: List[str], tags: Dict[str, List[str]],
                               batch_size: int = 50) -> bool:
        """Update tags for multiple media items with batching.

        Args:
            item_ids: List of media item IDs
            tags: Dictionary mapping tag field names to lists of values
            batch_size: Number of items to update per batch

        Returns:
            True if all updates successful
        """
        if not item_ids:
            return True

        endpoint = "/api/ItemData/BatchChange"
        all_successful = True

        # Create update tasks
        tasks = []
        for i in range(0, len(item_ids), batch_size):
            batch = item_ids[i:i + batch_size]
            data = {
                "mediaItemIds": batch,
                "tags": tags
            }
            tasks.append(self._make_request(endpoint, method='POST', data=data))

        # Execute all batches concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logging.error(f"Batch update {i} failed: {result}")
                all_successful = False
            elif isinstance(result, dict) and not result.get('success', False):
                logging.error(f"Batch update {i} failed: {result.get('error', 'Unknown error')}")
                all_successful = False

        return all_successful

    async def update_item_metadata(self, item_id: str, category: Optional[str] = None,
                                  keywords: Optional[List[str]] = None) -> bool:
        """Update metadata for a single item.

        Args:
            item_id: Media item ID
            category: Category/classification for the item
            keywords: List of keywords to add

        Returns:
            True if successful
        """
        tags = {}
        if category:
            tags['Category'] = [category]
        if keywords:
            tags['Keywords'] = keywords

        if not tags:
            return False

        return await self.batch_update_tags([item_id], tags)

    async def cleanup_temp_files(self):
        """Remove all cached thumbnail files."""
        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.glob("*.jpg"):
                    try:
                        file.unlink()
                    except OSError as e:
                        logging.warning(f"Failed to delete {file}: {e}")
        except Exception as e:
            logging.error(f"Failed to cleanup temp files: {e}")

    async def test_connection(self) -> Dict[str, any]:
        """Test connection and return server statistics.

        Returns:
            Dictionary with connection status and server info
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            total = await self.get_total_count()
            test_items = await self.get_media_items_by_ids([1, 2, 3, 4, 5])

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
