// app/static/js/auth.js
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const errorMessage = document.getElementById('errorMessage');
    
    // Login form handler
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            if (!username || !password) {
                showError('Please fill in all fields');
                return;
            }
            
            // Clear previous errors
            errorMessage.textContent = '';
            
            fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                    return;
                }
                
                // Store tokens in localStorage
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);
                localStorage.setItem('user', JSON.stringify(data.user));
                
                // Redirect to chat page
                window.location.href = '/';
            })
            .catch(err => {
                showError('An error occurred. Please try again.');
                console.error('Login error:', err);
            });
        });
    }
    
    // Register form handler
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            const registrationKey = document.getElementById('registrationKey').value;
            
            if (!username || !password || !confirmPassword || !registrationKey) {
                showError('Please fill in all fields');
                return;
            }
            
            if (password !== confirmPassword) {
                showError('Passwords do not match');
                return;
            }
            
            // Clear previous errors
            errorMessage.textContent = '';
            
            fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    username, 
                    password, 
                    registration_key: registrationKey 
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                    return;
                }
                
                // Store tokens in localStorage
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);
                localStorage.setItem('user', JSON.stringify(data.user));
                
                // Redirect to chat page
                window.location.href = '/';
            })
            .catch(err => {
                showError('An error occurred. Please try again.');
                console.error('Registration error:', err);
            });
        });
    }
    
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    }
});
