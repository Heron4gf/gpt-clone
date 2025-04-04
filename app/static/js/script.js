// app/static/js/script.js
document.addEventListener('DOMContentLoaded', () => {
    const chatbox = document.getElementById('chatbox');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const newChatButton = document.querySelector('.new-chat-button'); // Optional

    // --- Event Listeners ---
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        // Send message on Enter key press (Shift+Enter for new line)
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault(); // Prevent default Enter behavior (new line)
            sendMessage();
        }
    });

     // Auto-resize textarea
    userInput.addEventListener('input', () => {
        autoResizeTextarea(userInput);
        toggleSendButton(); // Enable/disable button based on content
    });

    // Optional: New Chat functionality
    if (newChatButton) {
        newChatButton.addEventListener('click', startNewChat);
    }

    // Initial setup
    toggleSendButton();


    // --- Functions ---

    function appendMessage(sender, messageContent) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${sender}-message`); // e.g., 'user-message' or 'bot-message'

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');

        // Simple paragraph for now. Could parse markdown later.
        const p = document.createElement('p');
        p.textContent = messageContent;
        contentDiv.appendChild(p);

        messageDiv.appendChild(contentDiv);
        chatbox.appendChild(messageDiv);
        scrollToBottom();
    }

    function showTypingIndicator() {
        // Check if indicator already exists
        if (document.getElementById('typing-indicator')) return;

        const indicatorDiv = document.createElement('div');
        indicatorDiv.classList.add('message', 'bot-message'); // Style like a bot message
        indicatorDiv.id = 'typing-indicator';

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content', 'typing-indicator');
        contentDiv.innerHTML = `<span></span><span></span><span></span>` // Simple dots

        indicatorDiv.appendChild(contentDiv);
        chatbox.appendChild(indicatorDiv);
        scrollToBottom();
    }

    function hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    async function sendMessage() {
        const messageText = userInput.value.trim();
        if (!messageText) return; // Don't send empty messages

        // 1. Display user's message immediately
        appendMessage('user', messageText);

        // 2. Clear input and disable send button
        userInput.value = '';
        autoResizeTextarea(userInput); // Reset height
        toggleSendButton(true); // Disable button

        // 3. Show typing indicator
        showTypingIndicator();

        try {
            // 4. Send message to backend API
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: messageText }),
            });

            // 5. Hide typing indicator
            hideTypingIndicator();

            if (!response.ok) {
                // Handle HTTP errors (e.g., 400, 500)
                const errorData = await response.json().catch(() => ({ error: 'Unknown server error' }));
                console.error('API Error:', response.status, errorData);
                appendMessage('bot', `Sorry, something went wrong. ${errorData.error || 'Please try again.'}`);
            } else {
                // 6. Get response and display bot message
                const data = await response.json();
                appendMessage('bot', data.response);
            }

        } catch (error) {
            // Handle network errors or fetch API failures
            hideTypingIndicator();
            console.error('Network or fetch error:', error);
            appendMessage('bot', 'Sorry, I couldn\'t connect to the server. Please check your connection.');
        } finally {
            // 7. Re-enable input/button
             toggleSendButton(false); // Enable button (or keep disabled if input is empty)
             userInput.focus(); // Keep focus on input
        }
    }

    function scrollToBottom() {
        chatbox.scrollTop = chatbox.scrollHeight;
    }

    // Adjust textarea height based on content
    function autoResizeTextarea(textarea) {
        textarea.style.height = 'auto'; // Reset height
        textarea.style.height = `${textarea.scrollHeight}px`; // Set to scroll height
    }

     // Enable/disable send button based on input content
    function toggleSendButton(forceDisable = null) {
        if (forceDisable === true) {
             sendButton.disabled = true;
        } else if (forceDisable === false) {
            sendButton.disabled = userInput.value.trim() === '';
        }
         else {
            sendButton.disabled = userInput.value.trim() === '';
        }
    }

    function startNewChat() {
        // Clear chatbox content
        chatbox.innerHTML = '';
        // Add initial bot message if desired
        appendMessage('bot', 'Hello! How can I help you today?');
        // Clear input
        userInput.value = '';
        autoResizeTextarea(userInput);
        toggleSendButton();
        userInput.focus();
        console.log("New chat started");
        // Potentially clear server-side history if implemented
    }


    // Initial resize and scroll
    autoResizeTextarea(userInput);
    scrollToBottom();
});

// Add this function to app/static/js/script.js

async function streamMessage(conversationId, message) {
    const messageText = message || userInput.value.trim();
    if (!messageText) return;
    
    // Display user message and prepare UI
    appendMessage('user', messageText);
    userInput.value = '';
    autoResizeTextarea(userInput);
    toggleSendButton(true); // Disable button
    
    // Show typing indicator
    showTypingIndicator();
    
    // Initialize response container
    let responseText = '';
    const responseDiv = document.createElement('div');
    responseDiv.classList.add('message', 'bot-message');
    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');
    const responsePara = document.createElement('p');
    contentDiv.appendChild(responsePara);
    responseDiv.appendChild(contentDiv);
    
    // Add the empty response container to the chatbox
    hideTypingIndicator();
    chatbox.appendChild(responseDiv);
    
    try {
        // Start SSE connection
        const eventSource = new EventSource(`/api/chat/conversations/${conversationId}/stream`, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`  // You'll need to implement getAuthToken()
            },
            body: JSON.stringify({ message: messageText })
        });
        
        // Handle incoming message chunks
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.error) {
                responsePara.textContent = `Error: ${data.error}`;
                eventSource.close();
                return;
            }
            
            if (!data.complete) {
                // Append each chunk to the response text
                responseText += data.chunk;
                responsePara.textContent = responseText;
                scrollToBottom();
            } else {
                // Message is complete
                if (data.full_response) {
                    responsePara.textContent = data.full_response;
                }
                eventSource.close();
            }
        };
        
        // Handle errors
        eventSource.onerror = function(error) {
            console.error('SSE Error:', error);
            responsePara.textContent = 'Sorry, there was an error connecting to the server.';
            eventSource.close();
        };
        
    } catch (error) {
        console.error('Error setting up streaming:', error);
        responsePara.textContent = 'Sorry, I couldn\'t connect to the server. Please check your connection.';
    } finally {
        toggleSendButton(false);
        userInput.focus();
        scrollToBottom();
    }
}

// Helper function to get authentication token
function getAuthToken() {
    // Implement based on your auth mechanism
    // For example:
    return localStorage.getItem('access_token');
}
