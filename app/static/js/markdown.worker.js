// static/js/markdown.worker.js

// Import the 'marked' library using the path Flask will serve it from.
// Flask serves the 'static' folder at the root URL path '/static'.
try {
    // IMPORTANT: Use the correct path relative to your Flask server's root!
    importScripts('/static/js/marked.min.js');
} catch (e) {
    console.error("Worker: Failed to load marked library from /static/js/marked.min.js.", e);
    self.postMessage({ error: "Failed to load Markdown library." });
    // Optional: Try a CDN as a fallback?
    // try {
    //    importScripts('https://cdn.jsdelivr.net/npm/marked/marked.min.js');
    // } catch (cdnError) {
    //    console.error("Worker: Failed to load marked library from CDN fallback.", cdnError);
    //    self.postMessage({ error: "Failed to load Markdown library from fallback." });
    // }
}


self.onmessage = (event) => {
    // Check if 'marked' was loaded successfully
    if (typeof marked === 'undefined') {
        console.error("Worker: 'marked' library is not available.");
        self.postMessage({ html: "<p>Error: Markdown library unavailable in worker.</p>", originalMarkdown: event.data });
        return;
    }

    const markdown = event.data;

    try {
        // Configure marked (optional, but recommended)
        marked.setOptions({
            gfm: true,       // Enable GitHub Flavored Markdown
            breaks: true,    // Convert single line breaks to <br>
            // Consider safety: Sanitize HTML on the MAIN thread after receiving it if needed.
            // sanitize: false, // Disable marked's built-in basic sanitizer
        });

        const html = marked.parse(markdown);

        // Send the parsed HTML back to the main thread.
        self.postMessage({ html: html, originalMarkdown: markdown });

    } catch (e) {
        console.error("Worker: Markdown parsing error:", e);
        self.postMessage({ html: `<p>Error parsing Markdown content.</p><pre><code>${escapeHtml(markdown)}</code></pre>`, originalMarkdown: markdown });
    }
};

function escapeHtml(unsafe) {
   // ... (keep the escapeHtml function from the previous example) ...
    if (!unsafe) return '';
    return unsafe
         .replace(/&/g, "&")
         .replace(/</g, "<")
         .replace(/>/g, ">")
         .replace(/"/g, "\"")
         .replace(/'/g, "'");
}


console.log("Markdown Worker initialized.");