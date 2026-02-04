"""
Base connector class for all data source connectors.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import aiohttp
from aiohttp import ClientSession, ClientResponse
from ..utils.rate_limiter import RateLimiter


class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors.
    
    Provides common functionality for authentication, rate limiting,
    error handling, and session management.
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize the base connector.
        
        Args:
            config: Configuration dictionary
            logger: Logger instance (optional)
        """
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.session: Optional[ClientSession] = None
        self.rate_limiter = RateLimiter()
        self._is_connected = False
    
    async def connect(self) -> None:
        """
        Establish connection to the data source.
        
        This method should be called before making any API requests.
        """
        if self._is_connected:
            return
        
        try:
            # Create HTTP session with appropriate headers and timeout
            timeout = self.config.get('timeout', 30)
            self.session = ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers=self._get_default_headers()
            )
            
            # Test connection
            await self._test_connection()
            self._is_connected = True
            self.logger.info(f"Connected to {self.__class__.__name__}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to {self.__class__.__name__}: {e}")
            await self.disconnect()
            raise
    
    async def disconnect(self) -> None:
        """
        Close connection and clean up resources.
        """
        if self.session:
            await self.session.close()
            self.session = None
        
        self._is_connected = False
        self.logger.info(f"Disconnected from {self.__class__.__name__}")
    
    @abstractmethod
    async def _test_connection(self) -> None:
        """
        Test the connection to the data source.
        
        Should raise an exception if the connection fails.
        """
        pass
    
    @abstractmethod
    def _get_default_headers(self) -> Dict[str, str]:
        """
        Get default HTTP headers for requests.
        
        Returns:
            Dictionary of default headers
        """
        pass
    
    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with rate limiting and retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Request URL
            params: Query parameters
            data: Request body data
            headers: Additional headers
            retry_count: Number of retry attempts
            
        Returns:
            Response data as dictionary
            
        Raises:
            Exception: If request fails after all retries
        """
        if not self._is_connected:
            raise RuntimeError(f"Not connected to {self.__class__.__name__}")
        
        # Apply rate limiting
        await self.rate_limiter.acquire(self.__class__.__name__)
        
        # Merge headers
        request_headers = self._get_default_headers()
        if headers:
            request_headers.update(headers)
        
        last_exception = None
        
        for attempt in range(retry_count + 1):
            try:
                self.logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                async with self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=request_headers
                ) as response:
                    # Handle successful responses
                    if response.status == 200:
                        return await self._parse_response(response)
                    
                    # Handle rate limiting
                    elif response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        self.logger.warning(f"Rate limited, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    # Handle client errors
                    elif 400 <= response.status < 500:
                        error_text = await response.text()
                        raise Exception(f"Client error {response.status}: {error_text}")
                    
                    # Handle server errors (retry)
                    elif 500 <= response.status < 600:
                        error_text = await response.text()
                        last_exception = Exception(f"Server error {response.status}: {error_text}")
                        
                        if attempt < retry_count:
                            delay = min(2 ** attempt, 30)  # Exponential backoff, max 30s
                            self.logger.warning(f"Server error, retrying in {delay} seconds")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise last_exception
                    
                    else:
                        error_text = await response.text()
                        raise Exception(f"Unexpected status {response.status}: {error_text}")
            
            except asyncio.TimeoutError:
                last_exception = Exception(f"Request timeout after {self.config.get('timeout', 30)}s")
                if attempt < retry_count:
                    self.logger.warning(f"Timeout, retrying (attempt {attempt + 1})")
                    continue
                else:
                    raise last_exception
            
            except Exception as e:
                last_exception = e
                if attempt < retry_count:
                    self.logger.warning(f"Request failed, retrying: {e}")
                    await asyncio.sleep(1)
                    continue
                else:
                    raise last_exception
        
        # This should never be reached
        raise last_exception or Exception("Request failed for unknown reason")
    
    async def _parse_response(self, response: ClientResponse) -> Dict[str, Any]:
        """
        Parse HTTP response based on content type.
        
        Args:
            response: HTTP response object
            
        Returns:
            Parsed response data
        """
        content_type = response.headers.get('content-type', '').lower()
        
        if 'application/json' in content_type:
            return await response.json()
        elif 'text/' in content_type:
            return {'text': await response.text()}
        else:
            return {'data': await response.read()}
    
    @abstractmethod
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch data from the data source.
        
        Args:
            **kwargs: Additional parameters for data fetching
            
        Returns:
            List of data items
        """
        pass
    
    def is_connected(self) -> bool:
        """
        Check if the connector is connected.
        
        Returns:
            True if connected, False otherwise
        """
        return self._is_connected
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
