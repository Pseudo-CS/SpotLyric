from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
from langdetect import detect
from serpapi import GoogleSearch
from googlesearch import search
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import pathlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse

load_dotenv()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Spotify credentials
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = "https://spotlyric.onrender.com/callback"

# SerpAPI credentials
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "6b1c5ada495ea534107a4ac5807851e770c104235fa4e198d8d7f5beeaebeb31")

# Cache configuration
CACHE_FILE = "search_cache.json"
CACHE_EXPIRATION = timedelta(days=30)  # 1 month expiration

# Initialize Spotify client
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="user-read-currently-playing user-read-playback-state"
)

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

def get_cached_results(song_name: str, artist_name: str) -> Optional[list]:
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
        key for key, (_, timestamp) in cache.items()
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

def load_sources():
    """Load the list of sources from sources.txt"""
    try:
        with open('sources.txt', 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def search_lyrics_translations(song_name, artist_name):
    """Search for lyrics translations using SerpAPI"""
    # Check cache first
    cached_results = get_cached_results(song_name, artist_name)
    if cached_results is not None:
        return cached_results

    search_query = f"{song_name} {artist_name} lyrics translation"
    
    params = {
        "engine": "google",
        "q": search_query,
        "api_key": SERPAPI_KEY,
        "num": 10,
        "gl": "in",
        "hl": "en"
    }
    
    try:
        time.sleep(2)
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "error" in results or "organic_results" not in results:
            print("No results found")
            return []
            
        matches = []
        for result in results['organic_results'][:10]:  # Limit to first 10 results
            url = result.get('link', '')
            title = result.get('title', '') or url.split('/')[-1].replace('-', ' ').title()
            
            matches.append({
                'url': url,
                'title': title
            })
        
        print(f"Found {len(matches)} results")
        # Cache the results
        cache_results(song_name, artist_name, matches)
        return matches
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return []

def duckduckgo_search_lyrics(song_name, artist_name, num_results=10):
    """Search for lyrics using DuckDuckGo"""
    # Check cache first
    cached_results, bookmarks = get_cached_results(song_name, artist_name)
    if cached_results is not None:
        return cached_results, bookmarks

    search_query = f"{song_name} {artist_name} translation lyrics"
    url = f"https://html.duckduckgo.com/html/?q={search_query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        matches = []
        
        for result in soup.find_all('a', class_='result__url', limit=num_results):
            redirect_url = result['href']
            if redirect_url.startswith('//duckduckgo.com/l/'):
                # Extract the actual URL from the redirect
                query_params = urlparse(redirect_url).query
                for param in query_params.split('&'):
                    if param.startswith('uddg='):
                        actual_url = unquote(param[5:])
                        matches.append({
                            'url': actual_url,
                            'bookmarked': False
                        })
                        break
            else:
                matches.append({
                    'url': redirect_url,
                    'bookmarked': False
                })
        
        print(f"Found {len(matches)} results")
        # Cache the results with empty bookmarks dict
        cache_results(song_name, artist_name, matches, {})
        return matches, {}
        
    except Exception as e:
        print(f"DuckDuckGo search error: {str(e)}")
        return [], {}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def login():
    """Redirect to Spotify authorization page"""
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(url=auth_url)

@app.get("/callback")
async def callback(code: str):
    """Handle Spotify authorization callback"""
    try:
        token_info = sp_oauth.get_access_token(code)
        if not token_info:
            raise HTTPException(status_code=400, detail="Failed to get access token")
            
        # Calculate token expiration time
        expires_at = datetime.now() + timedelta(seconds=token_info['expires_in'])
        token_info['expires_at'] = expires_at.timestamp()
        
        # Store token info in localStorage
        return HTMLResponse(f"""
            <html>
                <body>
                    <script>
                        localStorage.setItem('spotify_token', '{token_info["access_token"]}');
                        localStorage.setItem('spotify_token_expires_at', '{token_info["expires_at"]}');
                        window.location.href = '/';
                    </script>
                </body>
            </html>
        """)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def is_token_expired(expires_at):
    """Check if the token has expired"""
    if not expires_at:
        return True
    # Add a 60-second buffer to prevent edge cases
    return datetime.now().timestamp() > (float(expires_at) - 60)

@app.post("/toggle-bookmark")
async def toggle_bookmark(song_name: str, artist_name: str, url: str):
    """Handle toggling bookmark for a search result"""
    try:
        cache = load_cache()
        cache_key = get_cache_key(song_name, artist_name)
        
        if cache_key in cache:
            results, timestamp, bookmarks = cache[cache_key]
            # Toggle bookmark status
            bookmarks[url] = not bookmarks.get(url, False)
            # Update cache
            cache[cache_key] = (results, timestamp, bookmarks)
            save_cache(cache)
            return {"success": True, "bookmarked": bookmarks[url]}
        return {"success": False, "error": "Cache entry not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/current-song")
async def current_song(token: str, expires_at: str = None):
    """Get current playing song and lyrics translations"""
    try:
        # Check if token is expired
        if is_token_expired(expires_at):
            print("Token expired, redirecting to login")
            return {
                "error": "Token expired",
                "message": "Please log in again",
                "requires_login": True,
                "redirect_url": "/login"
            }
            
        sp = spotipy.Spotify(auth=token)
        
        try:
            current = sp.current_playback()
            if current and current["item"]:
                track = current["item"]
                song_name = track["name"]
                artist_name = track["artists"][0]["name"]
                
                # Try DuckDuckGo search first, fall back to SerpAPI if it fails
                results, bookmarks = duckduckgo_search_lyrics(song_name, artist_name)
                if not results:
                    print("DuckDuckGo search failed, trying SerpAPI...")
                    results = search_lyrics_translations(song_name, artist_name)
                    bookmarks = {}
                
                return {
                    "song": song_name,
                    "artist": artist_name,
                    "lyrics_sources": results,
                    "bookmarks": bookmarks
                }
            return {"error": "No song currently playing"}
            
        except spotipy.SpotifyException as e:
            if e.http_status == 401:
                print("Token invalid, redirecting to login")
                return {
                    "error": "Invalid token",
                    "message": "Please log in again",
                    "requires_login": True,
                    "redirect_url": "/login"
                }
            else:
                print(f"Spotify API error: {str(e)}")
                return {
                    "error": "Spotify API error",
                    "message": str(e)
                }
                
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            "error": "Unexpected error",
            "message": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 