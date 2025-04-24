from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from langdetect import detect
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

# Initialize Spotify client
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="user-read-currently-playing user-read-playback-state"
)

def get_lyrics(song_name, artist_name):
    # Search for lyrics
    search_url = f"https://www.google.com/search?q={song_name}+{artist_name}+lyrics"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find lyrics
        lyrics_div = soup.find('div', {'class': 'BNeawe tAd8D AP7Wnd'})
        if lyrics_div:
            return lyrics_div.text
        return "Lyrics not found"
    except Exception as e:
        return f"Error fetching lyrics: {str(e)}"

def get_translation(text, target_lang="en"):
    # Simple translation using Google Translate
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={text}"
    try:
        response = requests.get(url)
        data = response.json()
        return data[0][0][0]
    except Exception as e:
        return f"Error translating: {str(e)}"

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
    return {"token": token_info["access_token"]}

@app.get("/current-song")
async def current_song(token: str):
    sp = spotipy.Spotify(auth=token)
    
    try:
        current = sp.current_playback()
        if current and current["item"]:
            track = current["item"]
            song_name = track["name"]
            artist_name = track["artists"][0]["name"]
            
            # Get lyrics
            lyrics = get_lyrics(song_name, artist_name)
            
            # Detect language
            try:
                language = detect(lyrics)
            except:
                language = "unknown"
            
            # If not English, get translation
            if language != "en" and language != "unknown":
                translation = get_translation(lyrics)
            else:
                translation = None
            
            return {
                "song": song_name,
                "artist": artist_name,
                "lyrics": lyrics,
                "language": language,
                "translation": translation
            }
        return {"error": "No song currently playing"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 