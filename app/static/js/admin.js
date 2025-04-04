// app/static/js/admin.js
document.addEventListener('DOMContentLoaded', function() {
    const generateKeyBtn = document.getElementById('generateKeyBtn');
    const loadKeysBtn = document.getElementById('loadKeysBtn');
    
    // Create a message element for notifications
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.style.display = 'none';
    document.querySelector('.admin-container').insertBefore(messageDiv, document.querySelector('.keys-table'));
    
    generateKeyBtn.addEventListener('click', function() {
        fetch('/api/admin/keys/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showMessage(data.error, 'error');
                return;
            }
            
            showMessage('Key generated successfully!', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        })
        .catch(err => {
            showMessage('An error occurred while generating the key.', 'error');
            console.error('Generate key error:', err);
        });
    });
    
    loadKeysBtn.addEventListener('click', function() {
        fetch('/api/admin/keys/load', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showMessage(data.error, 'error');
                return;
            }
            
            showMessage(data.message, 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        })
        .catch(err => {
            showMessage('An error occurred while loading keys.', 'error');
            console.error('Load keys error:', err);
        });
    });
    
    function showMessage(text, type) {
        messageDiv.textContent = text;
        messageDiv.className = `message ${type}`;
        messageDiv.style.display = 'block';
        
        // Hide after 5 seconds
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 5000);
    }
});
