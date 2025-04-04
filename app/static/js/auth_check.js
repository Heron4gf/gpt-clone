// app/static/js/auth_check.js
document.addEventListener('DOMContentLoaded', function() {
    // Skip check for login and register pages
    const path = window.location.pathname;
    if (path === '/login' || path === '/register') {
        return;
    }
    
    // Check for access token
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }
    
    // Verify token is valid (optional - can be added for extra security)
    fetch('/api/me', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (response.status === 401) {
            // Token invalid, redirect to login
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            window.location.href = '/login';
        }
    })
    .catch(err => {
        console.error('Auth check error:', err);
    });
});
