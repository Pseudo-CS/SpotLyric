let accessToken = localStorage.getItem('spotify_token');

document.getElementById('loginButton').addEventListener('click', async () => {
    try {
        const response = await fetch('/login');
        const data = await response.json();
        window.location.href = data.auth_url;
    } catch (error) {
        console.error('Login error:', error);
    }
});

// Check if we have a token in localStorage
if (accessToken) {
    // Hide login section and show player section
    document.getElementById('loginSection').style.display = 'none';
    document.getElementById('playerSection').style.display = 'block';
    
    // Start polling for current song
    startPolling();
}

async function startPolling() {
    // Poll every 5 seconds
    setInterval(updateCurrentSong, 5000);
    // Initial update
    updateCurrentSong();
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
                <div class="source">${source.source}</div>
            </a>
        `;
        sourcesList.appendChild(sourceItem);
    });
}

async function updateCurrentSong() {
    if (!accessToken) return;

    try {
        const response = await fetch(`/current-song?token=${accessToken}`);
        const data = await response.json();

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
    }
} 