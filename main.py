from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
from serpapi import GoogleSearch
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from cache_utils import (
    load_cache, save_cache, get_cache_key, get_cached_results, cache_results, cleanup_expired_cache
)

load_dotenv()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Spotify credentials
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
#SPOTIFY_REDIRECT_URI = "http://127.0.0.1:3000/callback"
SPOTIFY_REDIRECT_URI = "https://spotlyric.onrender.com/callback"

# SerpAPI credentials
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "6b1c5ada495ea534107a4ac5807851e770c104235fa4e198d8d7f5beeaebeb31")

# Initialize Spotify client
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="user-read-currently-playing user-read-playback-state"
)


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
    cached_results, bookmarks = get_cached_results(song_name, artist_name)
    if cached_results is not None:
        return cached_results, bookmarks, True  # True indicates cached results

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
            return [], {}, False
            
        matches = []
        for result in results['organic_results'][:10]:  # Limit to first 10 results
            url = result.get('link', '')
            title = result.get('title', '') or url.split('/')[-1].replace('-', ' ').title()
            
            matches.append({
                'url': url,
                'title': title
            })
        
        print(f"Found {len(matches)} results using SerpAPI")
        # Cache the results with empty bookmarks dict
        cache_results(song_name, artist_name, matches, {})
        return matches, {}, False  # False indicates fresh results
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return [], {}, False


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
async def toggle_bookmark(request: Request):
    """Handle toggling bookmark for a search result"""
    try:
        data = await request.json()
        song_name = data.get("song_name")
        artist_name = data.get("artist_name")
        url = data.get("url")
        
        if not all([song_name, artist_name, url]):
            return {"success": False, "error": "Missing required parameters"}
        
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
                
                # Use SerpAPI to search for lyrics
                results, bookmarks, is_cached = search_lyrics_translations(song_name, artist_name)
                
                return {
                    "song": song_name,
                    "artist": artist_name,
                    "lyrics_sources": results,
                    "bookmarks": bookmarks,
                    "is_cached": is_cached
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
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=3000
    ) 