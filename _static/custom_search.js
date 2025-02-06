window.addEventListener("DOMContentLoaded", () => {
    console.log("Custom search script loaded.");

    // Wait for the search index to be available
    const checkSearchIndex = setInterval(() => {
        if (window.search && window.search._index) {
            console.log("Search index found, enhancing functionality.");
            window.search._index.pipeline.remove(window.search.lunr.stemmer); // Example enhancement
            clearInterval(checkSearchIndex); // Stop checking once initialized
        }
    }, 100);
});