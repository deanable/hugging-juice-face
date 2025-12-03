"""
Connection pool manager for Daminion API clients.
Provides efficient connection reuse and management.
"""

import logging
import threading
import time
from typing import Optional, List
from queue import Queue, Empty, Full
from contextlib import contextmanager

from daminion_client import DaminionClient, DaminionAuthenticationError


class ConnectionPoolError(Exception):
    """Raised when connection pool operations fail."""
    pass


class PooledConnection:
    """Wrapper for a pooled connection with metadata."""

    def __init__(self, client: DaminionClient, pool: 'DaminionConnectionPool'):
        self.client = client
        self.pool = pool
        self.created_at = time.time()
        self.last_used = time.time()
        self.use_count = 0
        self.is_healthy = True

    def mark_used(self):
        """Mark connection as recently used."""
        self.last_used = time.time()
        self.use_count += 1

    def age(self) -> float:
        """Get connection age in seconds."""
        return time.time() - self.created_at

    def idle_time(self) -> float:
        """Get time since last use in seconds."""
        return time.time() - self.last_used

    def close(self):
        """Close the underlying connection."""
        try:
            self.client.cleanup_temp_files()
        except Exception as e:
            logging.error(f"Error closing connection: {e}")


class DaminionConnectionPool:
    """Thread-safe connection pool for Daminion clients.

    Features:
    - Min/max pool size
    - Connection reuse
    - Automatic connection recycling
    - Health checking
    - Connection timeout

    Usage:
        pool = DaminionConnectionPool(url, username, password, min_size=2, max_size=10)

        with pool.get_connection() as client:
            items = client.get_media_items()

        pool.close_all()
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        min_size: int = 2,
        max_size: int = 10,
        max_age: float = 3600.0,  # 1 hour
        max_idle: float = 300.0,  # 5 minutes
        connection_timeout: float = 30.0,
        rate_limit: float = 0.1
    ):
        """Initialize connection pool.

        Args:
            base_url: Daminion server URL
            username: Username
            password: Password
            min_size: Minimum number of connections to maintain
            max_size: Maximum number of connections
            max_age: Maximum connection age in seconds (recycled after)
            max_idle: Maximum idle time in seconds (recycled after)
            connection_timeout: Timeout to wait for available connection
            rate_limit: Rate limit for individual connections
        """
        self.base_url = base_url
        self.username = username
        self.password = password
        self.min_size = min_size
        self.max_size = max_size
        self.max_age = max_age
        self.max_idle = max_idle
        self.connection_timeout = connection_timeout
        self.rate_limit = rate_limit

        self._pool: Queue = Queue(maxsize=max_size)
        self._lock = threading.RLock()
        self._total_connections = 0
        self._closed = False

        # Initialize minimum connections
        self._initialize_pool()

        # Start maintenance thread
        self._maintenance_thread = threading.Thread(target=self._maintain_pool, daemon=True)
        self._maintenance_thread.start()

        logging.info(f"Connection pool initialized: {min_size}-{max_size} connections")

    def _create_connection(self) -> PooledConnection:
        """Create a new connection."""
        try:
            client = DaminionClient(
                self.base_url,
                self.username,
                self.password,
                rate_limit=self.rate_limit
            )
            # Authenticate immediately
            client.authenticate()

            conn = PooledConnection(client, self)
            logging.debug(f"Created new connection (total: {self._total_connections + 1})")
            return conn
        except Exception as e:
            logging.error(f"Failed to create connection: {e}")
            raise ConnectionPoolError(f"Failed to create connection: {e}")

    def _initialize_pool(self):
        """Initialize pool with minimum connections."""
        with self._lock:
            for _ in range(self.min_size):
                try:
                    conn = self._create_connection()
                    self._pool.put(conn, block=False)
                    self._total_connections += 1
                except (Full, ConnectionPoolError) as e:
                    logging.warning(f"Failed to initialize connection: {e}")

    def _is_connection_valid(self, conn: PooledConnection) -> bool:
        """Check if connection is still valid."""
        if not conn.is_healthy:
            return False
        if conn.age() > self.max_age:
            logging.debug(f"Connection too old: {conn.age():.1f}s > {self.max_age}s")
            return False
        if conn.idle_time() > self.max_idle:
            logging.debug(f"Connection idle too long: {conn.idle_time():.1f}s > {self.max_idle}s")
            return False
        return True

    @contextmanager
    def get_connection(self, timeout: Optional[float] = None):
        """Get a connection from the pool.

        Args:
            timeout: Timeout to wait for available connection

        Yields:
            DaminionClient instance

        Raises:
            ConnectionPoolError: If no connection available or pool closed
        """
        if self._closed:
            raise ConnectionPoolError("Connection pool is closed")

        timeout = timeout or self.connection_timeout
        conn = None

        try:
            # Try to get existing connection
            conn = self._pool.get(timeout=timeout)

            # Validate connection
            if not self._is_connection_valid(conn):
                logging.debug("Connection invalid, creating new one")
                conn.close()
                with self._lock:
                    self._total_connections -= 1
                conn = self._create_connection()
                with self._lock:
                    self._total_connections += 1

            conn.mark_used()
            yield conn.client

        except Empty:
            # No connection available, try to create new one if under max
            with self._lock:
                if self._total_connections < self.max_size:
                    try:
                        conn = self._create_connection()
                        self._total_connections += 1
                        conn.mark_used()
                        yield conn.client
                    except ConnectionPoolError:
                        raise
                else:
                    raise ConnectionPoolError(
                        f"Pool exhausted: {self._total_connections} connections in use"
                    )

        except Exception as e:
            # Mark connection as unhealthy
            if conn:
                conn.is_healthy = False
            logging.error(f"Error using connection: {e}")
            raise

        finally:
            # Return connection to pool
            if conn and conn.is_healthy:
                try:
                    self._pool.put(conn, block=False)
                except Full:
                    # Pool full, close connection
                    logging.debug("Pool full, closing excess connection")
                    conn.close()
                    with self._lock:
                        self._total_connections -= 1

    def _maintain_pool(self):
        """Maintenance thread to keep pool healthy."""
        while not self._closed:
            try:
                time.sleep(60)  # Run every minute

                with self._lock:
                    # Check pool size
                    current_size = self._pool.qsize()
                    logging.debug(f"Pool maintenance: {current_size}/{self._total_connections} connections")

                    # Ensure minimum size
                    if self._total_connections < self.min_size:
                        needed = self.min_size - self._total_connections
                        for _ in range(needed):
                            try:
                                conn = self._create_connection()
                                self._pool.put(conn, block=False)
                                self._total_connections += 1
                            except (ConnectionPoolError, Full):
                                break

            except Exception as e:
                logging.error(f"Pool maintenance error: {e}")

    def get_stats(self) -> dict:
        """Get pool statistics.

        Returns:
            Dictionary with pool stats
        """
        with self._lock:
            return {
                'total_connections': self._total_connections,
                'available_connections': self._pool.qsize(),
                'in_use_connections': self._total_connections - self._pool.qsize(),
                'min_size': self.min_size,
                'max_size': self.max_size,
                'is_closed': self._closed,
            }

    def close_all(self):
        """Close all connections in the pool."""
        self._closed = True
        logging.info("Closing connection pool...")

        # Drain the pool
        closed_count = 0
        while not self._pool.empty():
            try:
                conn = self._pool.get(block=False)
                conn.close()
                closed_count += 1
            except Empty:
                break

        with self._lock:
            self._total_connections = 0

        logging.info(f"Connection pool closed. Closed {closed_count} connections.")

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.close_all()
        return False

    def __del__(self):
        """Cleanup on deletion."""
        if not self._closed:
            self.close_all()
