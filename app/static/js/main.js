document.addEventListener('DOMContentLoaded', () => {
    // Health check API verification
    const apiStatusEl = document.getElementById('api-status');

    fetch('/health')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (apiStatusEl && data.status === 'ok') {
                apiStatusEl.textContent = '200 OK (Healthy)';
                apiStatusEl.style.color = 'var(--accent-emerald)';
            }
        })
        .catch(error => {
            console.error('Health check failed:', error);
            if (apiStatusEl) {
                apiStatusEl.textContent = 'Error connecting to API';
                apiStatusEl.style.color = '#ef4444';
            }
        });
});
