// static/js/script.js

// --- Utility Functions ---
function getAccessToken() {
    return localStorage.getItem('access_token');
}

function getAuthToken() { // Kept for consistency if used elsewhere
    return localStorage.getItem('access_token');
}

// Simple throttle function
function throttle(func, limit) {
    let inThrottle;
    let lastFunc;
    let lastRan;
    return function() {
        const context = this;
        const args = arguments;
        if (!inThrottle) {
            func.apply(context, args);
            lastRan = Date.now();
            inThrottle = true;
            setTimeout(function() {
                inThrottle = false;
                if (lastFunc) {
                    // Execute the last scheduled call after throttle period ends
                    lastFunc.apply(context, args);
                    lastFunc = null; // Reset last function queued
                }
            }, limit);
        } else {
             // Queue the last function call to run after throttle
            lastFunc = func;
        }
    }
}

// --- Global Variables ---
let currentConversationId = null;
let eventSourceController = null;
let markdownWorker = null; // Initialize worker state
let currentBotMessageIdForStreaming = null;
let currentBotMarkdownContent = '';
const THROTTLE_DELAY_MS = 150; // Adjust as needed (milliseconds)

// --- Core Functions (Authentication, Model Loading, Conversation Management) ---

async function checkAuth() {
    console.log("Checking authentication...");
    const token = getAccessToken();
    if (!token) {
        console.log("No access token found, redirecting to login.");
        window.location.href = '/login';
        return false;
    }
    try {
        const response = await fetch('/api/me', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
        });
        if (!response.ok) {
            console.error(`Auth check failed with status ${response.status}. Clearing tokens and redirecting.`);
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login';
            return false;
        }
        const userData = await response.json(); // Optional: Use user data if needed
        console.log(`User authenticated: ${userData?.username || 'Unknown'}`);
        return true;
    } catch (error) {
        console.error('Auth check fetch failed:', error);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login'; // Redirect on error too
        return false;
    }
}

async function loadAvailableModels() {
    console.log("Loading available models...");
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
            if (!modelSelect) {
                console.error("Model select dropdown not found!");
                return;
            }
            modelSelect.innerHTML = ''; // Clear previous options
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.display_name;
                modelSelect.appendChild(option);
            });
            console.log("Models loaded successfully.");
        } else {
             console.error('Failed to load models:', response.status, await response.text());
        }
    } catch (error) {
        console.error('Error loading models:', error);
    }
}

async function loadOrCreateConversation() {
    console.log("Loading or creating conversation...");
    if (currentConversationId) {
         console.log(`Using existing currentConversationId: ${currentConversationId}`);
         return currentConversationId;
    }
    // No need to call checkAuth here again, DOMContentLoaded does it first

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
            } else {
                 console.log('No existing conversations found on server.');
            }
        } else if (response.status !== 404) { // Ignore 404 (no conversations), handle others
             console.error('Failed to get conversations:', response.status, await response.text());
        }

        // If no conversations, create one
        console.log('Creating a new conversation...');
        const createResponse = await fetch('/api/chat/conversations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getAccessToken()}` },
            body: JSON.stringify({ title: 'New Conversation' }) // Backend might auto-title
        });
        if (createResponse.ok) {
            const createData = await createResponse.json();
            currentConversationId = createData.conversation.id;
            console.log(`Created new conversation ID: ${currentConversationId}`);
            return currentConversationId;
        } else {
            const errorText = await createResponse.text();
            console.error('Failed to create new conversation:', createResponse.status, errorText);
            if (createResponse.status === 401) window.location.href = '/login';
            return null;
        }
    } catch (error) {
        console.error('Error managing conversations:', error);
        return null;
    }
}

// --- Markdown Worker Integration ---

function initializeMarkdownWorker() {
    if (markdownWorker !== null) { // Check if already initialized or failed
        console.log("Markdown Worker already initialized or initialization failed previously.");
        return;
    }

    console.log("Attempting to initialize Markdown Worker...");
    try {
        // *** Ensure this path is correct based on your Flask static setup ***
        markdownWorker = new Worker('/static/js/markdown.worker.js');
        console.log("Markdown Worker created successfully.");

        markdownWorker.onmessage = (event) => {
            // console.log("Received message from worker:", event.data); // Log the raw event data (can be verbose)
            const { html, originalMarkdown, error } = event.data || {}; // Safely destructure

            if (error) {
                console.error("Error message received from Markdown Worker:", error);
                 if (currentBotMessageIdForStreaming) {
                    const targetElement = document.getElementById(currentBotMessageIdForStreaming);
                    if (targetElement) {
                        const contentP = targetElement.querySelector('.message-content p');
                        if (contentP) {
                            contentP.innerHTML += `<br><small style="color:red;">[Markdown Error: ${error}]</small>`;
                        }
                    }
                 }
                return;
            }

            // Check if the message ID we expect to update is still the active one
            if (!currentBotMessageIdForStreaming) {
                console.warn("Worker returned HTML, but no active streaming message ID. Ignoring. (This might be ok if chat was cleared or stream aborted)");
                return;
            }

            const targetElement = document.getElementById(currentBotMessageIdForStreaming);
            if (targetElement) {
                const contentP = targetElement.querySelector('.message-content p');
                if (contentP) {
                    // console.debug(`Updating innerHTML for ${currentBotMessageIdForStreaming}`);
                    contentP.innerHTML = html || ''; // Update content with parsed HTML
                    // TODO: Add syntax highlighting call here if needed (e.g., hljs.highlightAll() or specific element)
                    scrollToBottom(); // Scroll after updating content
                } else {
                    console.error("Critical: Could not find 'p' tag within message element:", currentBotMessageIdForStreaming, targetElement);
                }
            } else {
                // This might happen if the chat was cleared or message removed before worker finished
                // console.warn("Target message element not found for worker update (might be normal):", currentBotMessageIdForStreaming);
            }
        };

        markdownWorker.onerror = (errorEvent) => {
            console.error("CRITICAL: Error initializing or running Markdown Worker. Event Object:", errorEvent);
            console.error(` - Error Type: ${errorEvent.type}`);
            console.error(` - Error Message: ${errorEvent.message}`);
            console.error(` - Filename: ${errorEvent.filename}`);
            console.error(` - Line Number: ${errorEvent.lineno}`);
            console.error(` - Column Number: ${errorEvent.colno}`);

            appendMessage('bot', 'A critical error occurred with the Markdown processor. Formatting disabled.');
            markdownWorker = null; // Mark worker as failed
        };

    } catch (error) {
        console.error("CRITICAL: Failed to construct Markdown Worker:", error);
        appendMessage('bot', 'Error: Could not initialize Markdown processor. Formatting disabled.');
        markdownWorker = null; // Mark worker as failed
    }
}

const throttledParseAndRenderMarkdown = throttle(() => {
    if (markdownWorker && currentBotMessageIdForStreaming && currentBotMarkdownContent != null) { // Check content isn't null
        // console.debug("Throttled: Sending markdown to worker for ID:", currentBotMessageIdForStreaming, `Length: ${currentBotMarkdownContent.length}`);
        try {
            markdownWorker.postMessage(currentBotMarkdownContent);
        } catch(postError) {
            console.error("Error sending message to worker:", postError);
             markdownWorker = null; // Assume worker is dead
             appendMessage('bot', 'Error communicating with Markdown processor. Displaying raw text.');
              // Fallback to raw text if postMessage fails
              const targetElement = document.getElementById(currentBotMessageIdForStreaming);
              if (targetElement) {
                 const contentP = targetElement.querySelector('.message-content p');
                 if (contentP) contentP.textContent = currentBotMarkdownContent;
              }
        }
    } else if (!markdownWorker && currentBotMessageIdForStreaming) { // If worker failed previously
         // console.warn("Markdown Worker not available, rendering raw markdown."); // Can be verbose
          // Render raw text as a fallback
          const targetElement = document.getElementById(currentBotMessageIdForStreaming);
           if (targetElement) {
               const contentP = targetElement.querySelector('.message-content p');
               if (contentP) {
                    // Throttle still applies, so this updates periodically
                    contentP.textContent = currentBotMarkdownContent;
                    scrollToBottom(); // Scroll as raw text is added
               }
           }
    }
}, THROTTLE_DELAY_MS);

// --- DOM Manipulation & UI Utilities ---

function appendMessage(sender, messageContent, messageId = null) {
    // console.log(`Appending message: sender=${sender}, id=${messageId}, content length=${messageContent?.length ?? 0}`);
    const chatbox = document.getElementById('chatbox');
    if (!chatbox) {
        console.error("CRITICAL: Cannot find chatbox element!");
        return null;
    }

    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${sender}-message`);
    if (messageId) {
        messageDiv.id = messageId;
    }

    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');

    const p = document.createElement('p');
    // Set initial content safely using textContent.
    // The worker's onmessage handler will update bot messages with innerHTML later if successful.
    p.textContent = messageContent || ''; // Ensure content isn't null/undefined
    contentDiv.appendChild(p);

    messageDiv.appendChild(contentDiv);

    try {
        chatbox.appendChild(messageDiv);
        // console.log(`Appended message div for ID: ${messageId || '(no ID)'}`);
         scrollToBottom();
    } catch (e) {
        console.error("Error appending message to chatbox:", e, messageDiv);
        return null;
    }

    return messageDiv;
}

function showTypingIndicator() {
    const chatbox = document.getElementById('chatbox'); if (!chatbox) return;
    if (document.getElementById('typing-indicator')) return; // Already showing

    const indicatorDiv = document.createElement('div');
    indicatorDiv.classList.add('message', 'bot-message');
    indicatorDiv.id = 'typing-indicator';

    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content', 'typing-indicator');
    contentDiv.innerHTML = `<span></span><span></span><span></span>`; // Simple CSS animation dots

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

function scrollToBottom() {
    const chatbox = document.getElementById('chatbox'); if (!chatbox) return;
    // Add small delay to allow DOM to render before scrolling, especially after innerHTML changes
    setTimeout(() => {
        chatbox.scrollTop = chatbox.scrollHeight;
    }, 50);
}


function autoResizeTextarea(textarea) {
    if (!textarea) return;
    textarea.style.height = 'auto'; // Temporarily shrink
    textarea.style.height = `${textarea.scrollHeight}px`; // Set to scroll height
}

function toggleSendButton(forceDisable = null) {
    const sendButton = document.getElementById('sendButton');
    const userInput = document.getElementById('userInput');
    if (!sendButton || !userInput) return;

    if (forceDisable === true) {
        sendButton.disabled = true;
    } else if (forceDisable === false) {
        sendButton.disabled = false;
    } else {
        sendButton.disabled = userInput.value.trim() === '';
    }
}

// --- Event Handlers ---

async function handleSendMessage() {
    console.log("handleSendMessage triggered.");
    const userInput = document.getElementById('userInput');
    const modelSelect = document.getElementById('modelSelect');
    if (!userInput || !modelSelect) {
         console.error("Cannot send message: Input or model select not found.");
         return;
    }

    const messageText = userInput.value.trim();
    if (!messageText) return; // Don't send empty messages

    if (!currentConversationId) {
        console.log("No active conversation ID, attempting to load/create...");
        const newConvId = await loadOrCreateConversation();
        if (!newConvId) {
            appendMessage('bot', 'Error: Could not establish a conversation session. Please try refreshing.');
            return;
        }
        console.log(`Using newly established conversation ID: ${currentConversationId}`);
    }

    const selectedModel = modelSelect.value;

    appendMessage('user', messageText); // Display user message immediately
    userInput.value = ''; // Clear input
    autoResizeTextarea(userInput); // Resize after clearing
    toggleSendButton(true); // Disable send button

    await streamMessageWithFetch(currentConversationId, messageText, selectedModel);
}

async function startNewChat() {
    console.log("Starting new chat...");
    // Abort any ongoing stream
    if (eventSourceController) {
        console.log("[NEW CHAT] Aborting previous stream...");
        eventSourceController.abort();
        eventSourceController = null;
    }
    // Reset streaming state
    currentBotMessageIdForStreaming = null;
    currentBotMarkdownContent = '';

    const chatbox = document.getElementById('chatbox'); if (!chatbox) return;
    chatbox.innerHTML = ''; // Clear chat UI
    appendMessage('bot', 'Hello! How can I assist you?'); // Initial message
    currentConversationId = null; // Reset conversation ID

    // No need for auth check here, already done on load. Assumes user is still authenticated.

    // Create a new conversation on the backend immediately
    try {
        console.log("[NEW CHAT] Creating new conversation on backend...");
        const createResponse = await fetch('/api/chat/conversations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getAccessToken()}` },
            body: JSON.stringify({ title: 'New Conversation' }) // Backend can assign better title
        });
        if (createResponse.ok) {
            const createData = await createResponse.json();
            currentConversationId = createData.conversation.id;
            console.log(`[NEW CHAT] Created and set new conversation ID: ${currentConversationId}`);
        } else {
            const errorText = await createResponse.text();
            console.error('[NEW CHAT] Failed to create new conversation:', createResponse.status, errorText);
            appendMessage('bot', 'Error: Could not start a new conversation session.');
            if (createResponse.status === 401) {
                 appendMessage('bot', 'Session expired. Please login again.');
                 setTimeout(() => window.location.href = '/login', 2000);
            }
        }
    } catch (error) {
        console.error('[NEW CHAT] Error creating new conversation:', error);
        appendMessage('bot', 'Error: Could not start a new conversation session due to a network issue.');
    }

    // Reset UI elements
    const userInput = document.getElementById('userInput');
    if (userInput) {
        userInput.value = '';
        autoResizeTextarea(userInput);
        toggleSendButton(); // Re-evaluate based on empty input
        userInput.focus();
    }
}


// --- Streaming Logic ---

async function streamMessageWithFetch(conversationId, messageText, model) {
    console.log(`[STREAM] Starting fetch stream for conv ${conversationId}, model ${model}`);
    showTypingIndicator();

    // Reset state for this specific message stream
    currentBotMessageIdForStreaming = `bot-msg-${Date.now()}-${Math.random().toString(16).substring(2, 8)}`;
    currentBotMarkdownContent = ''; // Start with empty markdown
    let botMessageDiv = null; // Placeholder for the message div

    eventSourceController = new AbortController();
    const signal = eventSourceController.signal;

    try {
        // Create the initial placeholder message div using the safe appendMessage
        console.log(`[STREAM] Creating initial bot message div with ID: ${currentBotMessageIdForStreaming}`);
        botMessageDiv = appendMessage('bot', '', currentBotMessageIdForStreaming); // Initial empty message

        if (!botMessageDiv) {
             console.error("[STREAM] Failed to create bot message div! Aborting stream.");
             hideTypingIndicator();
             toggleSendButton(false);
             return;
        }

        // Fetch the stream
        const response = await fetch(`/api/chat/conversations/${conversationId}/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                content: messageText,
                model: model
            }),
            signal: signal
        });

        hideTypingIndicator(); // Hide once headers are received or request fails fast

        if (!response.ok) {
            // Handle HTTP errors before streaming starts
            const errorText = await response.text(); // Get error details
            console.error('[STREAM] Fetch error:', response.status, errorText);
            if (response.status === 401) {
                appendMessage('bot', 'Session expired. Redirecting to login...');
                setTimeout(() => window.location.href = '/login', 2000);
            } else {
                 // Update the placeholder div with the error message
                const errorMsg = `Error: ${response.status} - ${errorText || 'Failed to start stream'}`;
                 if(botMessageDiv) {
                     const p = botMessageDiv.querySelector('.message-content p');
                     if(p) p.textContent = errorMsg;
                 } else {
                     appendMessage('bot', errorMsg); // Append new if div creation failed
                 }
            }
            currentBotMessageIdForStreaming = null; // Clear state
            toggleSendButton(false);
            return;
        }

        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('text/event-stream')) {
            console.error('[STREAM] Expected text/event-stream, but received:', contentType);
            const errorMsg = 'Error: Received unexpected response format from server.';
             if(botMessageDiv) {
                const p = botMessageDiv.querySelector('.message-content p');
                if(p) p.textContent = errorMsg;
             } else {
                 appendMessage('bot', errorMsg);
             }
            currentBotMessageIdForStreaming = null; // Clear state
            toggleSendButton(false);
            return;
        }

        // Process the stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        console.log("[STREAM] Starting to read stream...");

        while (true) {
            const { value, done } = await reader.read();

            if (done) {
                console.log("[STREAM] Stream finished.");
                 // Ensure final accumulated content is sent for parsing
                 if (currentBotMessageIdForStreaming && currentBotMarkdownContent != null) {
                     if (markdownWorker) {
                         console.log("[STREAM] Sending final accumulated markdown to worker.");
                         try {
                             markdownWorker.postMessage(currentBotMarkdownContent);
                         } catch(postError) {
                             console.error("Error sending final message to worker:", postError);
                             if(botMessageDiv) botMessageDiv.querySelector('p').textContent = currentBotMarkdownContent; // Fallback
                         }
                     } else {
                          // If worker failed, ensure final raw text is displayed
                          console.log("[STREAM] Worker unavailable. Displaying final raw text.");
                         if(botMessageDiv) botMessageDiv.querySelector('p').textContent = currentBotMarkdownContent;
                     }
                 }
                break; // Exit loop
            }

            buffer += decoder.decode(value, { stream: true });

            // Process Server-Sent Events (SSE)
            let eolIndex;
            while ((eolIndex = buffer.indexOf('\n\n')) >= 0) {
                const message = buffer.substring(0, eolIndex);
                buffer = buffer.substring(eolIndex + 2); // Consume the message + \n\n

                if (message.startsWith('data:')) {
                    const jsonData = message.substring(5).trim();
                    try {
                        const data = JSON.parse(jsonData);

                        if (data.error) {
                            console.error('[STREAM] Received error event:', data.error);
                            currentBotMarkdownContent += `\n\n**Error:** ${data.error}\n`;
                            throttledParseAndRenderMarkdown(); // Trigger UI update with error
                            // Decide if you want to break the loop on error
                        } else if (data.complete) {
                            console.log('[STREAM] Received explicit completion event.');
                            // The 'done' flag from reader.read() is the primary signal, but this can be useful
                            // Don't break here, let the 'done' flag handle loop exit naturally
                        } else if (data.chunk) {
                            currentBotMarkdownContent += data.chunk;
                            throttledParseAndRenderMarkdown(); // Trigger potential parse/render
                        } else {
                             // console.warn("[STREAM] Received data event with unknown format:", data);
                        }

                    } catch (e) {
                        console.error('[STREAM] Failed to parse JSON data:', jsonData, e);
                        currentBotMarkdownContent += `\n\n**Error parsing server message.**\n`;
                        throttledParseAndRenderMarkdown();
                    }
                } else if (message.trim() !== '') {
                     // console.warn("[STREAM] Received non-data SSE line (e.g., comment):", message);
                }
            } // end while buffer has EOL
             // No need to check done flag again here, the top of the loop handles it
        } // end while (true) reader loop

    } catch (error) {
        hideTypingIndicator();
        if (error.name === 'AbortError') {
             console.log('[STREAM] Fetch aborted by user or navigation.');
        } else {
            console.error('[STREAM] Fetch/Streaming Error:', error);
             const errorMsg = 'Sorry, a connection error occurred while receiving the response.';
             // Try to update the message div if it exists
             if(botMessageDiv) {
                 const p = botMessageDiv.querySelector('.message-content p');
                 // Append error notice to potentially existing partial content
                 if(p) p.innerHTML += `<br><small style="color:red;">[Stream Error: ${error.message}]</small>`;
             } else {
                 appendMessage('bot', errorMsg); // Fallback to new message
             }
        }
    } finally {
        console.log("[STREAM] Fetch stream processing finished or aborted.");
        hideTypingIndicator();
        toggleSendButton(false); // Re-enable send button
        // Don't refocus input automatically, might interrupt user
        eventSourceController = null; // Clear the controller

        // --- THIS LINE WAS REMOVED ---
        // The ID state variable (`currentBotMessageIdForStreaming`) is now cleared
        // only at the beginning of the *next* stream request or when 'New Chat' is clicked.
        // This ensures the final worker message for the *current* stream can still find its target div.

    } // End Finally
} // End streamMessageWithFetch


// --- Initialization ---

document.addEventListener('DOMContentLoaded', async () => {
    console.log("DOM Content Loaded. Starting initialization...");

    // Get essential UI elements
    const chatbox = document.getElementById('chatbox');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const newChatButton = document.querySelector('.new-chat-button'); // Use querySelector for class
    const modelSelect = document.getElementById('modelSelect');

    // Guard against missing elements
    if (!chatbox || !userInput || !sendButton || !newChatButton || !modelSelect) {
        console.error("CRITICAL: One or more essential UI elements are missing. Aborting setup.");
        // Maybe display an error message to the user in the body?
        document.body.innerHTML = "<p>Error: Chat interface failed to load correctly. Please contact support.</p>";
        return;
    }

    // 1. Initialize Markdown Worker (can run early)
    initializeMarkdownWorker();

    // 2. Check Authentication
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) {
        console.log("Authentication check failed or redirecting. Halting setup.");
        return; // Stop further setup if not authenticated
    }
    // Authentication successful message moved inside checkAuth() for clarity

    // 3. Load or Create Conversation
    const conversationId = await loadOrCreateConversation();
    if (!conversationId) {
        console.error("Failed to establish a conversation ID. Chat may not function.");
        appendMessage('bot', 'Could not load or create a conversation. Please try refreshing.');
        // Decide if you want to halt or allow limited functionality
        // return;
    } else {
         console.log(`Using conversation ID: ${conversationId}`);
    }


    // 4. Setup Event Listeners
    sendButton.addEventListener('click', handleSendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { // Send on Enter, allow Shift+Enter for newline
            e.preventDefault(); // Prevent default newline insertion
            handleSendMessage();
        }
    });
    userInput.addEventListener('input', () => { // Auto-resize and toggle button on input
        autoResizeTextarea(userInput);
        toggleSendButton();
    });
    newChatButton.addEventListener('click', startNewChat);

    // 5. Initial UI State
    toggleSendButton(); // Set initial button state based on input field
    autoResizeTextarea(userInput); // Set initial textarea size

    // 6. Load Models (can happen after conversation is ready)
    await loadAvailableModels();

    console.log("Chat initialization complete.");
    userInput.focus(); // Focus input field for user
});