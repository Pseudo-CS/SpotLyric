from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
from langdetect import detect
import requests
from bs4 import BeautifulSoup
import re

load_dotenv()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Spotify credentials
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = "https://spotlyric.onrender.com/callback"

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
    """Search Google for lyrics translations and check against sources"""
    search_query = f"{song_name} {artist_name} lyrics translation"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        # Get the list of sources to check for
        sources = load_sources()
        
        # Search Google
        search_url = f"https://www.google.com/search?q={search_query}"
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all search results
        results = []
        for result in soup.find_all('div', {'class': 'g'}):
            link = result.find('a')
            if link and link.get('href'):
                url = link['href']
                # Check if URL matches any of our sources
                for source in sources:
                    if source in url:
                        results.append({
                            'url': url,
                            'source': source,
                            'title': link.text
                        })
                        break
        
        return results
    except Exception as e:
        print(f"Search error: {str(e)}")
        return []

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
    return HTMLResponse(f"""
        <html>
            <body>
                <script>
                    localStorage.setItem('spotify_token', '{token_info["access_token"]}');
                    window.location.href = '/';
                </script>
            </body>
        </html>
    """)

@app.get("/current-song")
async def current_song(token: str):
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
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 