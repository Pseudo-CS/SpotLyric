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

def load_cache() -> Dict[str, Tuple[list, str]]:
    """Load cache from file"""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                # Convert string timestamps back to datetime objects
                return {
                    key: (results, datetime.fromisoformat(timestamp))
                    for key, (results, timestamp) in cache_data.items()
                }
    except Exception as e:
        print(f"Error loading cache: {e}")
    return {}

def save_cache(cache: Dict[str, Tuple[list, datetime]]):
    """Save cache to file"""
    try:
        # Convert datetime objects to ISO format strings for JSON serialization
        cache_data = {
            key: (results, timestamp.isoformat())
            for key, (results, timestamp) in cache.items()
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
        results, timestamp = cache[cache_key]
        if datetime.now() - timestamp < CACHE_EXPIRATION:
            print(f"Using cached results for {song_name} - {artist_name}")
            return results
        else:
            # Remove expired entry
            del cache[cache_key]
            save_cache(cache)
    return None

def cache_results(song_name: str, artist_name: str, results: list):
    """Cache search results with current timestamp"""
    cache = load_cache()
    cache_key = get_cache_key(song_name, artist_name)
    cache[cache_key] = (results, datetime.now())
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
    """Search for lyrics translations using SerpAPI and check against sources"""
    # Check cache first
    cached_results = get_cached_results(song_name, artist_name)
    if cached_results is not None:
        return cached_results

    search_query = f"{song_name} {artist_name} lyrics translation"
    sources = load_sources()
    print(f"Loaded sources: {sources}")
    
    params = {
        "engine": "google",
        "q": search_query,
        "api_key": SERPAPI_KEY,
        "num": 10,  # Number of results to return
        "gl": "in",  # Country to search from
        "hl": "en"   # Language of results
    }
    
    try:
        # Add a small delay to avoid rate limiting
        time.sleep(2)
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "error" in results:
            print(f"Error from SerpAPI: {results['error']}")
            return []
            
        if "organic_results" not in results:
            print("No organic results found")
            return []
            
        print(f"Found {len(results['organic_results'])} search results")
        matches = []
        
        for result in results['organic_results']:
            url = result.get('link', '')
            print(f"Checking URL: {url}")
            
            # Check if URL matches any of our sources
            for source in sources:
                if source in url:
                    print(f"Match found for source: {source}")
                    title = result.get('title', '')
                    if not title:
                        title = url.split('/')[-1].replace('-', ' ').title()
                    
                    matches.append({
                        'url': url,
                        'source': source,
                        'title': title
                    })
                    break
        
        print(f"Total matches found: {len(matches)}")
        # Cache the results
        cache_results(song_name, artist_name, matches)
        return matches
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return []

def google_search_lyrics(song_name, artist_name, num_results=10):
    """Search for lyrics using Google search API"""
    # Check cache first
    cached_results = get_cached_results(song_name, artist_name)
    if cached_results is not None:
        return cached_results

    search_query = f"{song_name} {artist_name} translation lyrics"
    sources = load_sources()
    print(f"Loaded sources: {sources}")
    
    try:
        results = search(search_query, num_results=num_results)
        matches = []
        
        for url in results:
            print(f"Checking URL: {url}")
            
            # Check if URL matches any of our sources
            for source in sources:
                if source in url:
                    print(f"Match found for source: {source}")
                    title = url.split('/')[-1].replace('-', ' ').title()
                    
                    matches.append({
                        'url': url,
                        'source': source,
                        'title': title
                    })
                    break
        
        print(f"Total matches found: {len(matches)}")
        # Cache the results
        cache_results(song_name, artist_name, matches)
        return matches
        
    except Exception as e:
        print(f"Google search error: {str(e)}")
        return []

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
    return datetime.now().timestamp() > float(expires_at)

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
                "requires_login": True
            }
            
        sp = spotipy.Spotify(auth=token)
        
        try:
            current = sp.current_playback()
            if current and current["item"]:
                track = current["item"]
                song_name = track["name"]
                artist_name = track["artists"][0]["name"]
                
                # Try Google search first, fall back to SerpAPI if it fails
                results = google_search_lyrics(song_name, artist_name)
                if not results:
                    print("Google search failed, trying SerpAPI...")
                    results = search_lyrics_translations(song_name, artist_name)
                
                return {
                    "song": song_name,
                    "artist": artist_name,
                    "lyrics_sources": results
                }
            return {"error": "No song currently playing"}
            
        except spotipy.SpotifyException as e:
            if e.http_status == 401:
                print("Token invalid, redirecting to login")
                return {
                    "error": "Invalid token",
                    "message": "Please log in again",
                    "requires_login": True
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