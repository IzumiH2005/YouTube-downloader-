import time
from typing import Dict, Any, Optional, List
from collections import OrderedDict

class Cache:
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._search_cache: OrderedDict = OrderedDict()
        self._download_queue: Dict[int, List[str]] = {}
        self._results_cache: Dict[str, List[Dict]] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
    def get_search_results(self, query: str) -> Optional[List[Dict]]:
        """Get cached search results"""
        if query in self._results_cache:
            # Check if cache is still valid
            if time.time() - self._cache_timestamps[query] < 24 * 60 * 60:
                return self._results_cache[query]
            else:
                # Remove expired cache
                del self._results_cache[query]
                del self._cache_timestamps[query]
        return None

    def set_search_results(self, query: str, results: List[Dict]):
        """Cache search results"""
        self._results_cache[query] = results
        self._cache_timestamps[query] = time.time()
        
        # Remove oldest entries if cache is too large
        while len(self._results_cache) > self.max_size:
            oldest_query = min(self._cache_timestamps, key=self._cache_timestamps.get)
            del self._results_cache[oldest_query]
            del self._cache_timestamps[oldest_query]

    def add_to_download_queue(self, user_id: int, video_id: str) -> int:
        """Add video to user's download queue"""
        if user_id not in self._download_queue:
            self._download_queue[user_id] = []
            
        self._download_queue[user_id].append(video_id)
        return len(self._download_queue[user_id])

    def get_next_download(self, user_id: int) -> Optional[str]:
        """Get next video from user's download queue"""
        if user_id in self._download_queue and self._download_queue[user_id]:
            return self._download_queue[user_id].pop(0)
        return None
