// static/js/markdown.worker.js
console.log("Worker: Script starting execution...");

let markedLoaded = false;

try {
    // *** This path must match where Flask serves the file ***
    // It's relative to the server root, NOT the worker file itself.
    const libraryPath = '/static/js/marked.min.js';
    console.log(`Worker: Attempting to importScripts from ${libraryPath}`);
    importScripts(libraryPath);

    // Verify that the 'marked' object is now available
    if (typeof marked === 'function' || typeof marked === 'object') {
        console.log("Worker: Successfully imported and verified 'marked' library.");
        markedLoaded = true;
        // Configure marked globally within the worker (optional)
        marked.setOptions({
            gfm: true,       // Enable GitHub Flavored Markdown (tables, strikethrough, etc.)
            breaks: true,    // Convert single line breaks in paragraphs to <br>
            // Consider security: If markdown comes from untrusted sources,
            // sanitize the HTML on the MAIN thread after receiving it using DOMPurify.
            // Do NOT rely solely on marked's basic/deprecated sanitize options.
            // sanitize: false, // Deprecated and potentially unsafe
            // sanitizer: null, // Ensure no custom sanitizer runs here unless intended
            async: false     // Ensure synchronous parsing if needed, usually default
        });
         console.log("Worker: Marked options set.");
    } else {
        console.error("Worker: CRITICAL - importScripts succeeded but 'marked' is not defined or not a function/object!");
        // Send error back - main thread needs to know the worker is broken
        self.postMessage({ error: "Markdown library loaded but not functional." });
    }
} catch (e) {
    console.error(`Worker: CRITICAL - Failed to importScripts from ${libraryPath}. Error:`, e);
    // Send error back to main thread
    self.postMessage({ error: `Failed to load Markdown library: ${e.message}` });
    // Note: The worker might terminate or be unusable after this point.
}

self.onmessage = (event) => {
    // console.log("Worker: Received message from main thread:", event.data ? typeof event.data : 'null/undefined');

    if (!markedLoaded) {
        console.error("Worker: Received message, but 'marked' library failed to load. Cannot parse.");
        // Send error back with the original markdown for potential fallback rendering
        self.postMessage({
            error: "Markdown library unavailable.",
            html: `<p style="color: red;">[Markdown formatting unavailable]</p><pre><code>${escapeHtml(event.data)}</code></pre>`,
            originalMarkdown: event.data
        });
        return;
    }

    const markdown = event.data;
    if (typeof markdown !== 'string') {
         console.warn("Worker: Received non-string data. Ignoring.", markdown);
         // Optionally send back an error or empty content
         self.postMessage({ html: '', originalMarkdown: markdown });
         return;
    }

    // console.log(`Worker: Parsing markdown (${markdown.length} chars)...`);

    try {
        // Parse the markdown using the globally configured 'marked' instance
        const html = marked.parse(markdown);
        // console.log(`Worker: Parsing complete. Sending HTML (${html.length} chars) back.`);

        // Send the parsed HTML (and original markdown for reference if needed)
        self.postMessage({ html: html, originalMarkdown: markdown });

    } catch (e) {
        console.error("Worker: Markdown parsing error:", e);
        // Send back an error message and the original markdown
        self.postMessage({
            error: `Parsing error: ${e.message}`,
            html: `<p style="color: red;">[Error parsing Markdown]</p><pre><code>${escapeHtml(markdown)}</code></pre>`,
            originalMarkdown: markdown
        });
    }
};

// Utility function to escape HTML for displaying in error messages safely
function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') return '';
    return unsafe
         .replace(/&/g, "&")
         .replace(/</g, "<")
         .replace(/>/g, ">")
         .replace(/"/g, "\"")
         .replace(/'/g, "'");
}

// Optional: Catch unhandled errors within the worker itself
self.onerror = function(event) {
    console.error("Worker: Uncaught internal error:", event.message, event);
    // Attempt to notify the main thread about the unexpected failure
    // This might not always work if the worker state is severely corrupted.
    try {
        self.postMessage({ error: `Worker internal error: ${event.message}` });
    } catch (e) {
        // *** FIX: Added closing parenthesis ')' ***
        console.error("Worker: Failed to post internal error message back to main thread.", e);
        // ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    }
};

console.log("Worker: Initial script execution finished. Waiting for messages.");