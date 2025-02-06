window.addEventListener("DOMContentLoaded", () => {
    console.log("Custom search script loaded.");

    // Function to scroll to the first highlighted result
    const scrollToResult = () => {
        const firstResult = document.querySelector('.highlighted');
        if (firstResult) {
            firstResult.scrollIntoView({ behavior: 'smooth', block: 'center' });
            console.log("Scrolled to the first highlighted result.");
            return true; // Scrolling succeeded
        } else {
            console.warn("No highlighted result found.");
            return false; // No result to scroll to
        }
    };

    // Wait for the search functionality to initialize
    const checkSearchIndex = setInterval(() => {
        console.log("Checking for search index...");
        if (window.Search && window.Search.query) {
            console.log("Search functionality initialized.");

            // Stop the interval once the search functionality is found
            clearInterval(checkSearchIndex);

            // Observe the search results container for changes
            const searchResultsContainer = document.querySelector('.search-results');
            if (searchResultsContainer) {
                console.log("Search results container found, setting up observer.");

                const observer = new MutationObserver(() => {
                    console.log("Search results updated.");
                    const scrolled = scrollToResult();
                    if (scrolled) {
                        observer.disconnect(); // Stop observing after scrolling
                        console.log("Observer disconnected after scrolling.");
                    }
                });

                observer.observe(searchResultsContainer, { childList: true, subtree: true });
            } else {
                console.warn("Search results container not found.");
            }
        }
    }, 500); // Check every 500ms to avoid excessive checks
});
