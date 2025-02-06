window.addEventListener("DOMContentLoaded", () => {
    console.log("Custom search script loaded.");

    const checkSearchIndex = setInterval(() => {
        console.log("Checking for search index...");
        if (window.Search && window.Search.query) {
            console.log("Search functionality initialized.");

            // Scroll to the first highlighted result
            const scrollToResult = () => {
                const firstResult = document.querySelector('.search-results .highlighted');
                if (firstResult) {
                    firstResult.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    console.log("Scrolled to first search result.");
                } else {
                    console.warn("No highlighted result found.");
                }
            };

            // Hook into search result rendering
            const searchResults = document.querySelector('.search-results');
            if (searchResults) {
                // Wait for results to be rendered before scrolling
                const observer = new MutationObserver(() => {
                    scrollToResult();
                    observer.disconnect(); // Stop observing once done
                });
                observer.observe(searchResults, { childList: true, subtree: true });
            }

            clearInterval(checkSearchIndex); // Stop checking once initialized
        }
    }, 100); // Check every 100ms
});
