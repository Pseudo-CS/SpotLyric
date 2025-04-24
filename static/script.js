let accessToken = localStorage.getItem('spotify_token');
let tokenExpiresAt = localStorage.getItem('spotify_token_expires_at');

document.getElementById('loginButton').addEventListener('click', async () => {
    try {
        window.location.href = '/login';
    } catch (error) {
        console.error('Login error:', error);
    }
});

// Check if we have a valid token in localStorage
if (accessToken && tokenExpiresAt) {
    const now = new Date().getTime() / 1000;
    if (now < parseFloat(tokenExpiresAt)) {
        // Token is valid, show player section
        document.getElementById('loginSection').style.display = 'none';
        document.getElementById('playerSection').style.display = 'block';
        // Initial update
        updateCurrentSong();
    } else {
        // Token expired, clear it and show login
        localStorage.removeItem('spotify_token');
        localStorage.removeItem('spotify_token_expires_at');
        document.getElementById('loginSection').style.display = 'block';
        document.getElementById('playerSection').style.display = 'none';
    }
}

function updateSourcesList(sources) {
    const sourcesList = document.getElementById('sourcesList');
    sourcesList.innerHTML = '';
    
    if (sources.length === 0) {
        sourcesList.innerHTML = '<p class="no-sources">No lyrics sources found</p>';
        return;
    }
    
    sources.forEach(source => {
        const sourceItem = document.createElement('div');
        sourceItem.className = 'source-item';
        sourceItem.innerHTML = `
            <a href="${source.url}" target="_blank">
                <div class="title">${source.title}</div>
            </a>
        `;
        sourcesList.appendChild(sourceItem);
    });
}

async function updateCurrentSong() {
    const token = localStorage.getItem('spotify_token');
    const expiresAt = localStorage.getItem('spotify_token_expires_at');
    
    if (!token || !expiresAt) {
        window.location.href = '/login';
        return;
    }

    try {
        const response = await fetch(`/current-song?token=${token}&expires_at=${expiresAt}`);
        const data = await response.json();

        if (data.requires_login) {
            // Clear tokens and redirect to login
            localStorage.removeItem('spotify_token');
            localStorage.removeItem('spotify_token_expires_at');
            window.location.href = '/login';
            return;
        }

        if (data.error) {
            document.getElementById('songTitle').textContent = 'No song playing';
            document.getElementById('artistName').textContent = '';
            updateSourcesList([]);
            return;
        }

        // Update song info
        document.getElementById('songTitle').textContent = data.song;
        document.getElementById('artistName').textContent = data.artist;
        
        // Update sources list
        updateSourcesList(data.lyrics_sources);
    } catch (error) {
        console.error('Update error:', error);
        // On error, clear tokens and redirect to login
        localStorage.removeItem('spotify_token');
        localStorage.removeItem('spotify_token_expires_at');
        window.location.href = '/login';
    }
} 