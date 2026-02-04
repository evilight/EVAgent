"""
Rate limiter utility for API calls.
"""

import asyncio
import time
from typing import Dict, Optional
from collections import defaultdict, deque


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    """
    
    def __init__(self, max_requests: int = 100, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
    
    async def acquire(self, key: str = "default") -> None:
        """
        Acquire a request permit, waiting if necessary.
        
        Args:
            key: Identifier for the rate limit bucket
        """
        async with self.locks[key]:
            now = time.time()
            requests = self.requests[key]
            
            # Remove old requests outside the time window
            while requests and requests[0] <= now - self.time_window:
                requests.popleft()
            
            # Check if we can make a request
            if len(requests) >= self.max_requests:
                # Calculate wait time
                oldest_request = requests[0]
                wait_time = self.time_window - (now - oldest_request) + 0.1
                
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    return await self.acquire(key)  # Retry
            
            # Record this request
            requests.append(now)
    
    def get_remaining_requests(self, key: str = "default") -> int:
        """
        Get the number of remaining requests for the current time window.
        
        Args:
            key: Identifier for the rate limit bucket
            
        Returns:
            Number of remaining requests
        """
        now = time.time()
        requests = self.requests[key]
        
        # Remove old requests
        while requests and requests[0] <= now - self.time_window:
            requests.popleft()
        
        return max(0, self.max_requests - len(requests))
    
    def get_reset_time(self, key: str = "default") -> Optional[float]:
        """
        Get the time when the rate limit window resets.
        
        Args:
            key: Identifier for the rate limit bucket
            
        Returns:
            Unix timestamp when the window resets, or None if no requests
        """
        requests = self.requests[key]
        if not requests:
            return None
        
        return requests[0] + self.time_window


class JiraRateLimiter(RateLimiter):
    """
    Specialized rate limiter for Jira API.
    
    Jira Cloud typically allows 1000 requests per hour for authenticated users.
    """
    
    def __init__(self):
        # Jira Cloud: 1000 requests per hour
        super().__init__(max_requests=1000, time_window=3600)
    
    async def acquire_with_backoff(self, key: str = "jira") -> None:
        """
        Acquire a request permit with exponential backoff for failed requests.
        
        Args:
            key: Identifier for the rate limit bucket
        """
        await self.acquire(key)
    
    def should_retry_after_error(self, status_code: int) -> bool:
        """
        Determine if a request should be retried based on HTTP status code.
        
        Args:
            status_code: HTTP status code
            
        Returns:
            True if the request should be retried
        """
        retry_codes = {429, 502, 503, 504}
        return status_code in retry_codes
    
    def get_retry_delay(self, attempt: int, base_delay: float = 1.0) -> float:
        """
        Calculate retry delay with exponential backoff.
        
        Args:
            attempt: Current attempt number (starting from 1)
            base_delay: Base delay in seconds
            
        Returns:
            Delay in seconds
        """
        return min(base_delay * (2 ** (attempt - 1)), 60.0)  # Cap at 60 seconds
