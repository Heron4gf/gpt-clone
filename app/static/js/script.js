// Function to get access token from localStorage
function getAccessToken() {
    return localStorage.getItem('access_token');
}

// Helper function (redundant, but keeping for consistency with original code)
function getAuthToken() {
    return localStorage.getItem('access_token');
}

// Global variable to track the current conversation
let currentConversationId = null;
let eventSourceController = null; // To allow aborting fetch stream if needed

// --- loadAvailableModels function (keep as is) ---
async function loadAvailableModels() {
    try {
        const response = await fetch('/api/models', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${getAccessToken()}`,
                'Content-Type': 'application/json'
            }
        });
        if (response.ok) {
            const data = await response.json();
            const modelSelect = document.getElementById('modelSelect');
            modelSelect.innerHTML = ''; // Clear previous options
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.display_name;
                modelSelect.appendChild(option);
            });
        } else {
             console.error('Failed to load models:', response.status, await response.text());
        }
    } catch (error) {
        console.error('Error loading models:', error);
    }
}

// --- checkAuth function (keep as is) ---
async function checkAuth() {
    const token = getAccessToken();
    if (!token) {
        window.location.href = '/login';
        return false;
    }
    try {
        const response = await fetch('/api/me', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
        });
        if (!response.ok) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login';
            return false;
        }
        return true;
    } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login'; // Redirect on error too
        return false;
    }
}

// --- loadOrCreateConversation function (keep as is) ---
async function loadOrCreateConversation() {
    if (currentConversationId) return currentConversationId;
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) return null;

    try {
        // Try getting existing conversations
        const response = await fetch('/api/chat/conversations', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${getAccessToken()}`, 'Content-Type': 'application/json' }
        });
        if (response.ok) {
            const data = await response.json();
            if (data.conversations && data.conversations.length > 0) {
                currentConversationId = data.conversations[0].id; // Use most recent
                console.log(`Loaded existing conversation ID: ${currentConversationId}`);
                // TODO: Optionally load messages for this conversation here
                // await loadMessagesForConversation(currentConversationId);
                return currentConversationId;
            }
        } else if (response.status !== 404) { // Ignore 404, handle others
             console.error('Failed to get conversations:', response.status, await response.text());
        }

        // If no conversations, create one
        console.log('No existing conversations found, creating a new one...');
        const createResponse = await fetch('/api/chat/conversations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getAccessToken()}` },
            body: JSON.stringify({ title: 'New Conversation' })
        });
        if (createResponse.ok) {
            const createData = await createResponse.json();
            currentConversationId = createData.conversation.id;
            console.log(`Created new conversation ID: ${currentConversationId}`);
            return currentConversationId;
        } else {
            const errorData = await createResponse.json();
            console.error('Failed to create new conversation:', errorData);
            if (createResponse.status === 401) window.location.href = '/login';
            return null;
        }
    } catch (error) {
        console.error('Error managing conversations:', error);
        return null;
    }
}

// --- DOMContentLoaded Event Listener (Modified) ---
document.addEventListener('DOMContentLoaded', async () => {
    const chatbox = document.getElementById('chatbox');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const newChatButton = document.querySelector('.new-chat-button');

    // Check authentication first
    console.log("Checking authentication...");
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) {
        console.log("Authentication failed or pending redirect.");
        return; // Stop execution if not authenticated
    }
    console.log("Authentication successful.");

    // Initial setup
    console.log("Loading or creating conversation...");
    const conversationId = await loadOrCreateConversation();
    if (!conversationId) {
        console.error("Failed to establish a conversation ID.");
        appendMessage('bot', 'Could not load or create a conversation. Please try refreshing or logging in again.');
        return; // Stop if no conversation ID
    }
    console.log(`Using conversation ID: ${conversationId}`);

    // --- MODIFIED Event Listeners ---
    // Replace sendMessage with handleSendMessage which will call the streaming function
    sendButton.addEventListener('click', handleSendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    // --- End Modification ---

    userInput.addEventListener('input', () => {
        autoResizeTextarea(userInput);
        toggleSendButton();
    });

    if (newChatButton) {
        newChatButton.addEventListener('click', startNewChat);
    }

    toggleSendButton();
    autoResizeTextarea(userInput);
    // Initial scroll might be needed if loading messages
    // scrollToBottom();

    console.log("Loading available models...");
    await loadAvailableModels();
    console.log("Setup complete.");
});


// --- Utility functions (appendMessage, show/hideTyping, scrollToBottom, autoResize, toggleSend) ---
// Keep these mostly as they are, but modify appendMessage slightly for streaming

function appendMessage(sender, messageContent, messageId = null) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${sender}-message`);
    if (messageId) {
        messageDiv.id = messageId; // Assign ID if provided (for streaming updates)
    }

    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');

    const p = document.createElement('p');
    // Basic Markdown rendering could be added here if desired
    p.textContent = messageContent;
    contentDiv.appendChild(p);

    messageDiv.appendChild(contentDiv);
    chatbox.appendChild(messageDiv);
    scrollToBottom();
    return messageDiv; // Return the created div
}

function updateStreamingMessage(messageId, chunk) {
     const messageDiv = document.getElementById(messageId);
     if (messageDiv) {
         const p = messageDiv.querySelector('.message-content p');
         if (p) {
             p.textContent += chunk; // Append the chunk
             scrollToBottom();
         }
     } else {
         console.warn(`Message div with ID ${messageId} not found for streaming update.`);
         // Optionally create it if missing, though it should be created first
         // appendMessage('bot', chunk, messageId);
     }
}


function showTypingIndicator() {
    // Keep as is
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
    // Keep as is
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

function scrollToBottom() {
    // Keep as is
    chatbox.scrollTop = chatbox.scrollHeight;
}

function autoResizeTextarea(textarea) {
    // Keep as is
    textarea.style.height = 'auto';
    textarea.style.height = `${textarea.scrollHeight}px`;
}

function toggleSendButton(forceDisable = null) {
    const sendButton = document.getElementById('sendButton');
    const userInput = document.getElementById('userInput');
    if (!sendButton || !userInput) return; // Add guards

    if (forceDisable === true) {
        sendButton.disabled = true;
    } else if (forceDisable === false) {
        sendButton.disabled = false; // Allow forcing enable
    }
     else {
        sendButton.disabled = userInput.value.trim() === '';
    }
}

// --- NEW function called by event listeners ---
async function handleSendMessage() {
    const userInput = document.getElementById('userInput');
    const messageText = userInput.value.trim();
    if (!messageText) return;

    // Ensure conversation ID is available
    if (!currentConversationId) {
        console.log("Attempting to get conversation ID before sending...");
        const newConvId = await loadOrCreateConversation();
        if (!newConvId) {
            appendMessage('bot', 'Error: Could not load or create a conversation. Please try logging in again.');
            return;
        }
        console.log(`Using newly established conversation ID: ${currentConversationId}`);
    }

    const modelSelect = document.getElementById('modelSelect');
    const selectedModel = modelSelect.value;

    // Append user message UI
    appendMessage('user', messageText);
    userInput.value = ''; // Clear input AFTER getting value
    autoResizeTextarea(userInput);
    toggleSendButton(true); // Disable button while processing

    // Call the fetch-based streaming function
    await streamMessageWithFetch(currentConversationId, messageText, selectedModel);
}


// --- REWRITTEN Streaming function using Fetch ---
async function streamMessageWithFetch(conversationId, messageText, model) {
    console.log(`[STREAM] Starting fetch stream for conv ${conversationId}, model ${model}`);
    showTypingIndicator(); // Show indicator initially

    // Generate a unique ID for the bot's response message element
    const botMessageId = `bot-msg-${Date.now()}-${Math.random().toString(16).substring(2, 8)}`;
    let botMessageDiv = null; // Initialize placeholder div
    let responseText = ''; // Accumulate text

    // Abort controller to allow stopping the fetch request if needed (e.g., user navigates away)
    eventSourceController = new AbortController();
    const signal = eventSourceController.signal;

    try {
        const response = await fetch(`/api/chat/conversations/${conversationId}/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}` // Use existing function
            },
            body: JSON.stringify({
                content: messageText, // Ensure backend expects 'content'
                model: model
            }),
            signal: signal // Pass the abort signal
        });

        hideTypingIndicator(); // Hide indicator once response headers are received

        if (!response.ok) {
            // Handle HTTP errors (like 401, 404, 500 before streaming starts)
            if (response.status === 401) {
                appendMessage('bot', 'Session expired. Redirecting to login...');
                setTimeout(() => window.location.href = '/login', 2000);
            } else {
                const errorData = await response.json().catch(() => ({ error: `Server error: ${response.status}` }));
                console.error('[STREAM] Fetch error:', response.status, errorData);
                appendMessage('bot', `Error: ${errorData.error || `Failed to start stream (${response.status})`}`);
            }
            toggleSendButton(false); // Re-enable button on error
            return; // Stop processing
        }

        // Check content type
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('text/event-stream')) {
            console.error('[STREAM] Expected text/event-stream, but received:', contentType);
            appendMessage('bot', 'Error: Received unexpected response format from server.');
            toggleSendButton(false);
            return;
        }

        // Process the stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = ''; // Buffer for incomplete SSE messages

        console.log("[STREAM] Starting to read stream...");

        // Create the initial empty bot message div *before* reading the stream
        botMessageDiv = appendMessage('bot', '', botMessageId);

        while (true) {
            const { value, done } = await reader.read();

            if (done) {
                console.log("[STREAM] Stream finished.");
                if (buffer) {
                    console.warn("[STREAM] Stream finished with incomplete data in buffer:", buffer);
                }
                break; // Exit loop when stream is done
            }

            // Decode chunk and add to buffer
            buffer += decoder.decode(value, { stream: true }); // stream: true handles multi-byte chars potentially split across chunks
            // console.debug("[STREAM] Buffer:", buffer); // Very verbose

            // Process buffer line by line for SSE messages
            let eolIndex;
            while ((eolIndex = buffer.indexOf('\n\n')) >= 0) {
                const message = buffer.substring(0, eolIndex);
                buffer = buffer.substring(eolIndex + 2); // Consume message + \n\n

                if (message.startsWith('data:')) {
                    const jsonData = message.substring(5).trim(); // Get data part
                    // console.debug("[STREAM] Received SSE data:", jsonData); // Verbose
                    try {
                        const data = JSON.parse(jsonData);

                        if (data.error) {
                            console.error('[STREAM] Received error event:', data.error);
                            updateStreamingMessage(botMessageId, `\n\n--- Error: ${data.error} ---`);
                            // Optionally close the reader early on error?
                            // await reader.cancel(); // or eventSourceController.abort();
                            break; // Stop processing further events in this scenario
                        } else if (data.complete) {
                            console.log('[STREAM] Received completion event.');
                            // The finally block below handles final UI state
                            break; // Exit inner loop, outer loop will exit as 'done' should be true soon
                        } else if (data.chunk) {
                            responseText += data.chunk;
                             // Update the content of the existing message div
                            updateStreamingMessage(botMessageId, data.chunk);
                        } else {
                             console.warn("[STREAM] Received data event with no chunk/error/complete:", data);
                        }

                    } catch (e) {
                        console.error('[STREAM] Failed to parse JSON data:', jsonData, e);
                        // Maybe display a parsing error in the UI?
                        updateStreamingMessage(botMessageId, `\n\n--- Error parsing server message ---`);
                    }
                } else if (message.trim() !== '') {
                     console.warn("[STREAM] Received non-data SSE line:", message);
                }
            } // end while ((eolIndex = buffer.indexOf('\n\n')) >= 0)
             if (done) break; // Ensure exit if done flag was set during buffer processing
        } // end while (true)

    } catch (error) {
        hideTypingIndicator();
        // Handle errors like network issues or fetch abort
        if (error.name === 'AbortError') {
             console.log('[STREAM] Fetch aborted.');
        } else {
            console.error('[STREAM] Fetch/Streaming Error:', error);
            // Try to update the bot message div if it exists, otherwise append new error
            if (botMessageDiv) {
                updateStreamingMessage(botMessageId, '\n\n--- Connection error ---');
            } else {
                appendMessage('bot', 'Sorry, there was a connection error.');
            }
        }
    } finally {
        console.log("[STREAM] Fetch stream processing finished or aborted.");
        hideTypingIndicator();
        toggleSendButton(false); // Re-enable send button
        userInput.focus(); // Refocus input
        eventSourceController = null; // Clear controller
    }
}


// --- startNewChat function (keep as is, ensures currentConversationId is reset) ---
async function startNewChat() {
    // Abort any ongoing stream before starting new chat
     if (eventSourceController) {
         console.log("[NEW CHAT] Aborting previous stream...");
         eventSourceController.abort();
         eventSourceController = null;
     }

    chatbox.innerHTML = ''; // Clear UI
    appendMessage('bot', 'Hello! How can I help you today?');
    currentConversationId = null; // Reset current conversation ID

    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) return;

    // Create a new conversation on the backend immediately
    try {
        console.log("[NEW CHAT] Creating new conversation on backend...");
        const createResponse = await fetch('/api/chat/conversations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getAccessToken()}` },
            body: JSON.stringify({ title: 'New Conversation' }) // Maybe use a timestamp?
        });
        if (createResponse.ok) {
            const createData = await createResponse.json();
            currentConversationId = createData.conversation.id; // Set the new ID
            console.log(`[NEW CHAT] Created and set new conversation ID: ${currentConversationId}`);
        } else {
            const errorData = await createResponse.json();
            console.error('[NEW CHAT] Failed to create new conversation:', errorData);
            appendMessage('bot', 'Error: Could not start a new conversation session.');
            if (createResponse.status === 401) {
                 appendMessage('bot', 'Session expired. Redirecting to login...');
                 setTimeout(() => window.location.href = '/login', 2000);
            }
        }
    } catch (error) {
        console.error('[NEW CHAT] Error creating new conversation:', error);
        appendMessage('bot', 'Error: Could not start a new conversation session.');
    }

    // Reset UI elements
    const userInput = document.getElementById('userInput');
    userInput.value = '';
    autoResizeTextarea(userInput);
    toggleSendButton();
    userInput.focus();
}