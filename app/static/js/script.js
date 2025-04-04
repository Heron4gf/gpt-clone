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
        if (!messageText) return;
    
        // Get the selected model
        const modelSelect = document.getElementById('modelSelect');
        const selectedModel = modelSelect.value;
    
        // Display user's message...
        
        try {
            // Send message to backend API with model selection
            const response = await fetch(`/api/chat/conversations/${currentConversationId}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getAccessToken()}`
                },
                body: JSON.stringify({ 
                    content: messageText,
                    model: selectedModel
                }),
            });
            
            // Handle response...
        }
        catch (error) {
            // Error handling...
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

// app/static/js/script.js (update the model selection part)

// Add a function to load available models
async function loadAvailableModels() {
    try {
        const response = await fetch('/api/models', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${getAccessToken()}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            const modelSelect = document.getElementById('modelSelect');
            
            // Clear existing options
            modelSelect.innerHTML = '';
            
            // Add options for each model
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.display_name;
                modelSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading models:', error);
    }
}

// Add this to your initialization code
document.addEventListener('DOMContentLoaded', () => {
    // Existing initialization code...
    
    // Load available models
    loadAvailableModels();
    
    // Check if the user is logged in
    if (!getAccessToken()) {
        window.location.href = '/login';
    }
});
