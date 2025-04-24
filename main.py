from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
from langdetect import detect
from serpapi import GoogleSearch
import time
import json

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
    """Search for lyrics translations using SerpAPI and check against sources"""
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
        return matches
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return []

def refresh_spotify_token(refresh_token):
    """Refresh the Spotify access token using the refresh token"""
    try:
        token_info = sp_oauth.refresh_access_token(refresh_token)
        return token_info
    except Exception as e:
        print(f"Error refreshing token: {str(e)}")
        return None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def login():
    auth_url = sp_oauth.get_authorize_url()
    return {"auth_url": auth_url}

@app.get("/callback")
async def callback(code: str):
    token_info = sp_oauth.get_access_token(code)
    # Store both access token and refresh token
    return HTMLResponse(f"""
        <html>
            <body>
                <script>
                    localStorage.setItem('spotify_token', '{token_info["access_token"]}');
                    localStorage.setItem('spotify_refresh_token', '{token_info["refresh_token"]}');
                    window.location.href = '/';
                </script>
            </body>
        </html>
    """)

@app.get("/current-song")
async def current_song(token: str, refresh_token: str = None):
    try:
        # Try to use the current token first
        sp = spotipy.Spotify(auth=token)
        
        try:
            current = sp.current_playback()
            if current and current["item"]:
                track = current["item"]
                song_name = track["name"]
                artist_name = track["artists"][0]["name"]
                
                # Search for lyrics translations
                results = search_lyrics_translations(song_name, artist_name)
                
                return {
                    "song": song_name,
                    "artist": artist_name,
                    "lyrics_sources": results
                }
            return {"error": "No song currently playing"}
            
        except spotipy.SpotifyException as e:
            # If token is expired and we have a refresh token, try to refresh it
            if e.http_status == 401 and refresh_token:
                print("Token expired, attempting to refresh...")
                try:
                    new_token_info = refresh_spotify_token(refresh_token)
                    
                    if new_token_info and "access_token" in new_token_info:
                        print("Token refresh successful")
                        # Retry with new token
                        sp = spotipy.Spotify(auth=new_token_info["access_token"])
                        current = sp.current_playback()
                        
                        if current and current["item"]:
                            track = current["item"]
                            song_name = track["name"]
                            artist_name = track["artists"][0]["name"]
                            
                            # Search for lyrics translations
                            results = search_lyrics_translations(song_name, artist_name)
                            
                            return {
                                "song": song_name,
                                "artist": artist_name,
                                "lyrics_sources": results,
                                "new_token": new_token_info["access_token"],  # Send new token to client
                                "token_expires_in": new_token_info.get("expires_in", 3600)  # Send token expiration time
                            }
                        return {"error": "No song currently playing"}
                    else:
                        print("Token refresh failed - no new token received")
                        return {
                            "error": "Failed to refresh token",
                            "message": "Please log in again",
                            "requires_login": True
                        }
                except Exception as refresh_error:
                    print(f"Error during token refresh: {str(refresh_error)}")
                    return {
                        "error": "Token refresh failed",
                        "message": "Please log in again",
                        "requires_login": True
                    }
            else:
                print(f"Spotify API error: {str(e)}")
                return {
                    "error": "Spotify API error",
                    "message": str(e),
                    "requires_login": e.http_status == 401
                }
                
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            "error": "Unexpected error",
            "message": str(e),
            "requires_login": True
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 