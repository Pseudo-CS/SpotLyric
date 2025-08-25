import os
import json
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

CACHE_FILE = "search_cache.json"
CACHE_EXPIRATION = timedelta(days=30)  # 1 month expiration

def load_cache() -> Dict[str, Tuple[list, datetime, dict]]:
    """Load cache from file"""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                # Convert string timestamps back to datetime objects
                return {
                    key: (results, datetime.fromisoformat(timestamp), bookmarks)
                    for key, (results, timestamp, bookmarks) in cache_data.items()
                }
    except Exception as e:
        print(f"Error loading cache: {e}")
    return {}

def save_cache(cache: Dict[str, Tuple[list, datetime, dict]]):
    """Save cache to file"""
    try:
        # Convert datetime objects to ISO format strings for JSON serialization
        cache_data = {
            key: (results, timestamp.isoformat(), bookmarks)
            for key, (results, timestamp, bookmarks) in cache.items()
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
    except Exception as e:
        print(f"Error saving cache: {e}")

def get_cache_key(song_name: str, artist_name: str) -> str:
    """Generate a unique cache key for a song and artist"""
    return f"{song_name.lower()}_{artist_name.lower()}"

def get_cached_results(song_name: str, artist_name: str) -> Tuple[Optional[list], dict]:
    """Get cached results if they exist and haven't expired"""
    cache = load_cache()
    cache_key = get_cache_key(song_name, artist_name)
    
    if cache_key in cache:
        results, timestamp, bookmarks = cache[cache_key]
        if datetime.now() - timestamp < CACHE_EXPIRATION:
            print(f"Using cached results for {song_name} - {artist_name}")
            return results, bookmarks
        else:
            # Remove expired entry
            del cache[cache_key]
            save_cache(cache)
    return None, {}

def cache_results(song_name: str, artist_name: str, results: list, bookmarks: dict = None):
    """Cache search results with current timestamp and bookmarks"""
    cache = load_cache()
    cache_key = get_cache_key(song_name, artist_name)
    cache[cache_key] = (results, datetime.now(), bookmarks or {})
    save_cache(cache)
    print(f"Cached results for {song_name} - {artist_name}")

def cleanup_expired_cache():
    """Remove expired entries from cache"""
    cache = load_cache()
    current_time = datetime.now()
    expired_keys = [
        key for key, (_, timestamp, _) in cache.items()
        if current_time - timestamp >= CACHE_EXPIRATION
    ]
    
    if expired_keys:
        for key in expired_keys:
            del cache[key]
        save_cache(cache)
        print(f"Cleaned up {len(expired_keys)} expired cache entries")

# Initialize cache file if it doesn't exist
if not os.path.exists(CACHE_FILE):
    save_cache({})

# Clean up expired cache entries on startup
cleanup_expired_cache()
