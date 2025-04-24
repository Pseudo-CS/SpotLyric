let accessToken = null;

document.getElementById('loginButton').addEventListener('click', async () => {
    try {
        const response = await fetch('/login');
        const data = await response.json();
        window.location.href = data.auth_url;
    } catch (error) {
        console.error('Login error:', error);
    }
});

// Check if we have a token in the URL (callback)
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');

if (code) {
    getAccessToken(code);
}

async function getAccessToken(code) {
    try {
        const response = await fetch(`/callback?code=${code}`);
        const data = await response.json();
        accessToken = data.token;
        
        // Hide login section and show player section
        document.getElementById('loginSection').style.display = 'none';
        document.getElementById('playerSection').style.display = 'block';
        
        // Start polling for current song
        startPolling();
    } catch (error) {
        console.error('Token error:', error);
    }
}

let currentSongId = null;

async function startPolling() {
    // Poll every 5 seconds
    setInterval(updateCurrentSong, 5000);
    // Initial update
    updateCurrentSong();
}

async function updateCurrentSong() {
    if (!accessToken) return;

    try {
        const response = await fetch(`/current-song?token=${accessToken}`);
        const data = await response.json();

        if (data.error) {
            document.getElementById('songTitle').textContent = 'No song playing';
            document.getElementById('artistName').textContent = '';
            document.getElementById('lyrics').textContent = '';
            document.getElementById('translationSection').style.display = 'none';
            return;
        }

        // Update song info
        document.getElementById('songTitle').textContent = data.song;
        document.getElementById('artistName').textContent = data.artist;
        document.getElementById('lyrics').textContent = data.lyrics;

        // Show/hide translation section
        const translationSection = document.getElementById('translationSection');
        if (data.translation) {
            translationSection.style.display = 'block';
            document.getElementById('translation').textContent = data.translation;
        } else {
            translationSection.style.display = 'none';
        }
    } catch (error) {
        console.error('Update error:', error);
    }
} 