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
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        // Handle any error status as a need to re-login
        if (!response.ok) {
            console.log('Authentication check failed, redirecting to login');
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            window.location.href = '/login';
            return;
        }
        
        return response.json();
    })
    .then(data => {
        if (data && data.user) {
            console.log('User authenticated:', data.user.username);
        }
    })
    .catch(err => {
        console.error('Auth check error:', err);
        // Redirect to login on any error
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
    });
});