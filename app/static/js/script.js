// Function to get access token from localStorage
function getAccessToken() {
    return localStorage.getItem('access_token');
}

// Helper function to get authentication token
function getAuthToken() {
    return localStorage.getItem('access_token');
}

// Global variable to track the current conversation
let currentConversationId = null;

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

            modelSelect.innerHTML = '';

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

// Function to check if user is authenticated, and redirect to login if not
async function checkAuth() {
    const token = getAccessToken();
    if (!token) {
        window.location.href = '/login';
        return false;
    }
    
    try {
        const response = await fetch('/api/me', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            // Token is invalid or expired
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login';
            return false;
        }
        
        return true;
    } catch (error) {
        console.error('Auth check failed:', error);
        return false;
    }
}

// Function to create a new conversation or load existing ones
async function loadOrCreateConversation() {
    if (currentConversationId) {
        return currentConversationId;
    }
    
    // Check authentication first
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) {
        return null;
    }
    
    try {
        // First try to get existing conversations
        const response = await fetch('/api/chat/conversations', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${getAccessToken()}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.conversations && data.conversations.length > 0) {
                // Use the most recent conversation
                currentConversationId = data.conversations[0].id;
                console.log(`Loaded existing conversation ID: ${currentConversationId}`);
                return currentConversationId;
            }
        }
        
        // If no conversations exist, create a new one
        const createResponse = await fetch('/api/chat/conversations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAccessToken()}`
            },
            body: JSON.stringify({
                title: 'New Conversation'
            })
        });
        
        if (createResponse.ok) {
            const createData = await createResponse.json();
            currentConversationId = createData.conversation.id;
            console.log(`Created new conversation ID: ${currentConversationId}`);
            return currentConversationId;
        } else {
            const errorData = await createResponse.json();
            console.error('Failed to create new conversation:', errorData);
            
            if (createResponse.status === 401) {
                // Authentication issue
                window.location.href = '/login';
            }
            
            return null;
        }
    } catch (error) {
        console.error('Error managing conversations:', error);
        return null;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const chatbox = document.getElementById('chatbox');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const newChatButton = document.querySelector('.new-chat-button');

    // Check authentication first
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) {
        return; // Stop execution if not authenticated
    }
    
    // Initial setup
    const conversationId = await loadOrCreateConversation();
    if (!conversationId) {
        appendMessage('bot', 'Could not load or create a conversation. Please try again or log in again.');
    }
    
    sendButton.addEventListener('click', sendMessage);

    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    userInput.addEventListener('input', () => {
        autoResizeTextarea(userInput);
        toggleSendButton();
    });

    if (newChatButton) {
        newChatButton.addEventListener('click', startNewChat);
    }

    toggleSendButton();
    autoResizeTextarea(userInput);
    scrollToBottom();

    // Load available models
    loadAvailableModels();

    function appendMessage(sender, messageContent) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${sender}-message`);

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');

        const p = document.createElement('p');
        p.textContent = messageContent;
        contentDiv.appendChild(p);

        messageDiv.appendChild(contentDiv);
        chatbox.appendChild(messageDiv);
        scrollToBottom();
    }

    function showTypingIndicator() {
        if (document.getElementById('typing-indicator')) return;

        const indicatorDiv = document.createElement('div');
        indicatorDiv.classList.add('message', 'bot-message');
        indicatorDiv.id = 'typing-indicator';

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content', 'typing-indicator');
        contentDiv.innerHTML = `<span></span><span></span><span></span>`;

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

        // Make sure we have a conversation ID
        if (!currentConversationId) {
            try {
                const newConvId = await loadOrCreateConversation();
                if (!newConvId) {
                    appendMessage('bot', 'Error: Could not load or create a conversation. Please try logging in again.');
                    return;
                }
            } catch (error) {
                console.error('Error creating conversation before sending message:', error);
                appendMessage('bot', 'Error: Could not load or create a conversation. Please try logging in again.');
                return;
            }
        }

        const modelSelect = document.getElementById('modelSelect');
        const selectedModel = modelSelect.value;

        appendMessage('user', messageText);
        userInput.value = '';
        autoResizeTextarea(userInput);
        toggleSendButton(true);
        showTypingIndicator();

        try {
            console.log(`Sending message to conversation ${currentConversationId} with model ${selectedModel}`);
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

            if (!response.ok) {
                if (response.status === 401) {
                    // Auth error - redirect to login
                    hideTypingIndicator();
                    appendMessage('bot', 'Your session has expired. Please log in again.');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                    return;
                }
                
                const errorData = await response.json();
                console.error('Error from server:', errorData);
                hideTypingIndicator();
                appendMessage('bot', `Error: ${errorData.error || 'Failed to get response from server'}`);
                return;
            }

            const data = await response.json();
            hideTypingIndicator();
            
            // Find the last assistant message in the conversation
            const conversation = data.conversation;
            if (conversation && conversation.messages && conversation.messages.length > 0) {
                const assistantMessages = conversation.messages.filter(msg => msg.role === 'assistant');
                if (assistantMessages.length > 0) {
                    const lastAssistantMessage = assistantMessages[assistantMessages.length - 1];
                    appendMessage('bot', lastAssistantMessage.content);
                } else {
                    appendMessage('bot', 'No response received from assistant.');
                }
            } else {
                appendMessage('bot', 'No response received from assistant.');
            }

        } catch (error) {
            console.error('Send message error:', error);
            hideTypingIndicator();
            appendMessage('bot', 'Sorry, there was an error processing your request.');
        } finally {
            toggleSendButton(false);
        }
    }

    async function streamMessage(conversationId, message) {
        const messageText = message || userInput.value.trim();
        if (!messageText) return;

        appendMessage('user', messageText);
        userInput.value = '';
        autoResizeTextarea(userInput);
        toggleSendButton(true);
        showTypingIndicator();

        let responseText = '';
        const responseDiv = document.createElement('div');
        responseDiv.classList.add('message', 'bot-message');

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');

        const responsePara = document.createElement('p');
        contentDiv.appendChild(responsePara);
        responseDiv.appendChild(contentDiv);

        hideTypingIndicator();
        chatbox.appendChild(responseDiv);

        try {
            const eventSource = new EventSource(`/api/chat/conversations/${conversationId}/stream`, {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getAuthToken()}`
                },
                body: JSON.stringify({ message: messageText })
            });

            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);

                if (data.error) {
                    responsePara.textContent = `Error: ${data.error}`;
                    eventSource.close();
                    return;
                }

                if (!data.complete) {
                    responseText += data.chunk;
                    responsePara.textContent = responseText;
                    scrollToBottom();
                } else {
                    if (data.full_response) {
                        responsePara.textContent = data.full_response;
                    }
                    eventSource.close();
                }
            };

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

    function scrollToBottom() {
        chatbox.scrollTop = chatbox.scrollHeight;
    }

    function autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = `${textarea.scrollHeight}px`;
    }

    function toggleSendButton(forceDisable = null) {
        if (forceDisable === true) {
            sendButton.disabled = true;
        } else {
            sendButton.disabled = userInput.value.trim() === '';
        }
    }

    async function startNewChat() {
        chatbox.innerHTML = '';
        appendMessage('bot', 'Hello! How can I help you today?');
        
        // Check authentication first
        const isAuthenticated = await checkAuth();
        if (!isAuthenticated) {
            return; // Stop execution if not authenticated
        }
        
        // Create a new conversation
        try {
            const createResponse = await fetch('/api/chat/conversations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getAccessToken()}`
                },
                body: JSON.stringify({
                    title: 'New Conversation'
                })
            });
            
            if (createResponse.ok) {
                const createData = await createResponse.json();
                currentConversationId = createData.conversation.id;
                console.log(`Created new conversation ID: ${currentConversationId}`);
            } else {
                const errorData = await createResponse.json();
                console.error('Failed to create new conversation:', errorData);
                appendMessage('bot', 'Error: Could not create a new conversation.');
                
                if (createResponse.status === 401) {
                    // Authentication issue
                    appendMessage('bot', 'Your session has expired. Please log in again.');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                }
            }
        } catch (error) {
            console.error('Error creating new conversation:', error);
            appendMessage('bot', 'Error: Could not create a new conversation.');
        }
        
        userInput.value = '';
        autoResizeTextarea(userInput);
        toggleSendButton();
        userInput.focus();
    }
});